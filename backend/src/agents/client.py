import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
import json
from typing import Dict, Any, List, Optional
from pydantic import AnyUrl, BaseModel
from openai import AsyncOpenAI

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.shared.context import RequestContext
import logging
import sys
import signal
from src.utils.connection_manager import manager
from contextlib import asynccontextmanager
from pydantic import BaseModel, RootModel
import os
import json
from enum import Enum
import logging
from typing import List, Optional, Literal
from typing import Union
from src.agents.event_listerner.basic_listerner import basic_listener
detailed_tools = []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for structured responses
class AgentOutput(BaseModel):
    task_completed: bool
    next_step: str
    result: str
    require_context: bool = False
    tool_to_call: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    additional_info: str = ""

# Simplified system prompt to avoid content policy issues
AGENT_SYSTEM_PROMPT = """You are an autonomous task execution agent that helps users by analyzing their requests and executing them step by step using available tools.

Your goal is to:
1. Understand the user's request
2. Determine the next logical step to take
3. Execute that step using appropriate tools
4. Continue until the task is completed

Always respond in valid JSON format with these exact fields:
{
  "task_completed": false,
  "next_step": "Description of what you plan to do next",
  "result": "What was accomplished in this step",
  "require_context": false,
  "tool_to_call": null,
  "tool_arguments": null,
  "errors": [],
  "additional_info": ""
}

Rules:
- Set task_completed to true only when the entire request is fulfilled
- Set require_context to true if you need to understand the current page state
- When setting require_context as true DO NOT GIVE ANY TOOL TO BE CALLED use the given context to then decide which tool to call with what parameters
- NEVER decide next step without having proper context of the current page
- Set tool_to_call to the name of the tool you want to use (or null)
- Set tool_arguments to a dictionary of arguments for the tool (or null)
- Always provide a clear next_step description
- Handle errors gracefully and report them in the errors array
- Respond only with valid JSON, no other text"""

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="E:\\test2\\Intelligent-Browser\\backend\\.venv\\Scripts\\uv.exe",
    args=[
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "playwright",
        "--with",
        "typing",
        "--with",
        "bs4",
        "mcp",
        "run",
        "E:\\test2\\Intelligent-Browser\\backend\\src\\agents\\server.py"
    ],
    # env={"DISPLAY": ":1", **os.environ}  # Use :1 instead of :0
)

class MCPOpenAIClient:
    def __init__(self, openai_api_key: str):
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.available_tools = []
        self.available_resources = []

    @asynccontextmanager
    async def get_mcp_session(self):
        """Create and manage MCP session using proper context manager pattern"""
        session = None
        stdio_ctx = None
        
        try:
            logger.info("Creating MCP session...")
            
            # Create stdio client context - this must stay in the same task
            stdio_ctx = stdio_client(server_params)
            read, write = await stdio_ctx.__aenter__()
            
            # Create session context - this must also stay in the same task
            session_ctx = ClientSession(read, write)
            session = await session_ctx.__aenter__()
            
            # Initialize the session
            await session.initialize()
            logger.info("MCP session initialized successfully")
            
            # Get available tools and resources
            try:
                tools_response = await session.list_tools()
                self.available_tools = []
                for t in tools_response.tools:
                    tool_info = {
                        "name": t.name, 
                        "description": t.description,
                        "parameters": t.inputSchema if hasattr(t, 'inputSchema') else {}
                    }
                    self.available_tools.append(tool_info)
                
                logger.info(f"Found {len(self.available_tools)} tools:")
                for tool in self.available_tools:
                    logger.info(f"  - {tool['name']}: {tool['description']}")
                    
            except Exception as e:
                logger.warning(f"Could not list tools: {e}")
                self.available_tools = []
            
            try:
                resources_response = await session.list_resources()
                self.available_resources = [{"uri": str(r.uri), "name": r.name} for r in resources_response.resources]
                logger.info(f"Found {len(self.available_resources)} resources")
            except Exception as e:
                logger.warning(f"Could not list resources: {e}")
                self.available_resources = []
            
            # Yield the session for use
            yield session
            
        except Exception as e:
            logger.error(f"Error in MCP session: {e}")
            raise
            
        finally:
            # Clean up in reverse order
            logger.info("Cleaning up MCP session...")
            
            if session:
                try:
                    await session_ctx.__aexit__(None, None, None)
                    logger.info("Session cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up session: {e}")
            
            if stdio_ctx:
                try:
                    await stdio_ctx.__aexit__(None, None, None)
                    logger.info("Stdio context cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up stdio context: {e}")
            
            logger.info("MCP session cleanup completed")
    
    async def call_openai_agent(self, user_request: str, session: ClientSession, messages: List[Dict] = None) -> AgentOutput:
        """Call OpenAI with single agent system prompt"""
        
        if messages is None:
            messages = []
        
        # Create tools info for the agent to reference
        available_tools_info = []
        for tool in self.available_tools:
            tool_info = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {})
            }
            available_tools_info.append(tool_info)
        
        # Create a cleaner user message
        user_message = f"""User Request: {user_request}

Available Tools:
{json.dumps(available_tools_info, indent=2)}

Please respond with a valid JSON object following the specified format."""
        
        # Prepare messages
        conversation_messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # Add any additional context messages
        conversation_messages.extend(messages)
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=conversation_messages,
                response_format={"type": "json_object"},
                temperature=0.1,  # Lower temperature for more consistent JSON
                max_tokens=1000   # Ensure we get a complete response
            )
            
            # Parse the JSON response
            response_content = response.choices[0].message.content
            logger.info(f"OpenAI agent response: {response_content}")
            
            if response_content is None or response_content.strip() == "":
                logger.error("OpenAI returned None or empty content")
                return AgentOutput(
                    task_completed=False,
                    next_step="Analyze the request and determine first step",
                    result="OpenAI response was empty, retrying",
                    require_context=True,
                    errors=["OpenAI returned empty response content"]
                )
            
            try:
                # Clean the response content in case there's extra whitespace or formatting
                cleaned_content = response_content.strip()
                agent_data = json.loads(cleaned_content)
                agent_output = AgentOutput(**agent_data)
                
                logger.info(f"Successfully parsed agent output: task_completed={agent_output.task_completed}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response content: {response_content}")
                return AgentOutput(
                    task_completed=False,
                    next_step="Parse JSON response correctly",
                    result="Failed to parse JSON response",
                    require_context=True,
                    errors=[f"JSON decode error: {str(e)}"]
                )
            except Exception as e:
                logger.error(f"Error creating AgentOutput: {e}")
                return AgentOutput(
                    task_completed=False,
                    next_step="Handle response parsing error",
                    result="Failed to create agent output object",
                    require_context=True,
                    errors=[f"AgentOutput creation error: {str(e)}"]
                )
            
            # Check if context is required
            if agent_output.require_context:
                try:
                    logger.info("Agent requested context, calling getcontexttool")
                    context_result = await session.call_tool("getcontexttool", arguments={})
                    
                    context_text = ""
                    for content in context_result.content:
                        if isinstance(content, types.TextContent):
                            context_text += content.text
                    
                    # Add context to messages for next iteration
                    messages.append({"role": "user", "content": f"Use the following page context to identify what is the step required to be performed on the page. For example, in a booking website first the page might want you to select the city then to select the movie and so on, identify what step to perform on the page using this page context. \nCurrent page context: {context_text}"})  # Limit context length
                    logger.info("Context added to conversation")
                    
                except Exception as e:
                    logger.error(f"Error getting context: {e}")
                    agent_output.errors.append(f"Error getting context: {str(e)}")
            
            # Check if tool needs to be called
            if agent_output.tool_to_call is not None:
                tool_name = agent_output.tool_to_call
                tool_arguments = agent_output.tool_arguments or {}
                
                logger.info(f"Agent requested tool: {tool_name} with args: {tool_arguments}")
                
                try:
                    # Validate tool exists
                    if not any(t['name'] == tool_name for t in self.available_tools):
                        raise ValueError(f"Tool '{tool_name}' not found in available tools")
                    
                    # Call the MCP tool
                    tool_result = await session.call_tool(tool_name, arguments=tool_arguments)
                    
                    result_text = ""
                    for content in tool_result.content:
                        if isinstance(content, types.TextContent):
                            result_text += content.text
                    
                    logger.info(f"Tool {tool_name} executed successfully")
                    
                    # Update the result with tool execution info
                    agent_output.result = f"Executed {tool_name}: {result_text[:200]}"  # Limit result length
                    agent_output.additional_info = f"Tool {tool_name} completed successfully"
                    
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    agent_output.errors.append(f"Error executing tool {tool_name}: {str(e)}")
                    agent_output.result = f"Failed to execute {tool_name}"
            
            return agent_output
                    
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {e}")
            return AgentOutput(
                task_completed=False,
                next_step="Retry the request",
                result="OpenAI API call failed",
                require_context=True,
                errors=[f"OpenAI API error: {str(e)}"]
            )
    
    async def process_user_request(self, user_request: str) -> Dict[str, Any]:
        """Main function that processes user request with single agent loop"""
        logger.info(f"🚀 Processing request: {user_request}")
        print("="*50)
        
        execution_history = []
        max_iterations = 10
        iteration = 0
        context_messages = []
        
        try:
            # Use the context manager for the entire processing session
            async with self.get_mcp_session() as session:
                while iteration < max_iterations:
                    iteration += 1
                    logger.info(f"🤖 Agent Iteration {iteration}")
                    
                    # Get response from agent
                    agent_output = await self.call_openai_agent(user_request, session, context_messages)
                    
                    # Send workflow data to frontend
                    workflow_data = {
                        "iteration": iteration,
                        "next_step": agent_output.next_step,
                        "result": agent_output.result,
                        "task_completed": agent_output.task_completed,
                        "errors": agent_output.errors,
                        "additional_info": agent_output.additional_info
                    }
                    
                    asyncio.create_task(manager.broadcast(json.dumps(workflow_data)))
                    
                    logger.info(f"Task Completed: {agent_output.task_completed}")
                    logger.info(f"Next Step: {agent_output.next_step}")
                    logger.info(f"Result: {agent_output.result}")
                    if agent_output.errors:
                        logger.warning(f"Errors: {agent_output.errors}")
                    
                    # Add to history
                    execution_history.append({
                        "iteration": iteration,
                        "next_step": agent_output.next_step,
                        "result": agent_output.result,
                        "task_completed": agent_output.task_completed,
                        "errors": agent_output.errors,
                        "additional_info": agent_output.additional_info
                    })
                    
                    # Add the agent's response to context for next iteration
                    context_messages.append({
                        "role": "assistant", 
                        "content": json.dumps({
                            "task_completed": agent_output.task_completed,
                            "next_step": agent_output.next_step,
                            "result": agent_output.result,
                            "errors": agent_output.errors
                        })
                    })
                    
                    # Check if we're done
                    if agent_output.task_completed:
                        logger.info("✅ Task completed successfully!")
                        return {
                            "status": "success",
                            "iterations": iteration,
                            "execution_history": execution_history
                        }
                    
                    # If there are critical errors, stop
                    if agent_output.errors and any("fatal" in error.lower() or "critical" in error.lower() for error in agent_output.errors):
                        logger.info("❌ Task failed due to critical errors!")
                        return {
                            "status": "failed",
                            "reason": "Critical errors encountered",
                            "iterations": iteration,
                            "execution_history": execution_history
                        }
                    
                    # If we keep getting the same error, break
                    if iteration > 3 and all("Error parsing response" in str(h.get("errors", [])) for h in execution_history[-3:]):
                        logger.error("❌ Repeated JSON parsing errors, stopping")
                        return {
                            "status": "failed",
                            "reason": "Repeated JSON parsing errors",
                            "iterations": iteration,
                            "execution_history": execution_history
                        }
                
                logger.warning(f"⚠️ Maximum iterations ({max_iterations}) reached!")
                return {
                    "status": "timeout",
                    "iterations": iteration,
                    "execution_history": execution_history
                }
            
        except Exception as e:
            logger.error(f"Error in process_user_request: {e}")
            return {
                "status": "error",
                "error": str(e),
                "iterations": iteration,
                "execution_history": execution_history
            }

# Simple wrapper function to avoid asyncio task mixing
async def run_client_session(request: str, api_key: str) -> Dict[str, Any]:
    """Run the entire client session in one async context"""
    client = MCPOpenAIClient(api_key)
    return await client.process_user_request(request)

async def runClient(user_request: str):
    """Entry point for the client script with proper asyncio handling."""
    
    print("Came to client") 
    # Setup signal handling for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return 1
            
        request = user_request
        
        # Run everything in a single asyncio.run call to avoid task mixing
        result = await run_client_session(request, api_key)
        
        print(f"\n📊 Final Result: {json.dumps(result, indent=2)}")
        return 0 if result.get("status") == "success" else 1
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1