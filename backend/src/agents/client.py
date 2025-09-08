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
from contextlib import asynccontextmanager

detailed_tools = []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for structured responses
class PlannerOutput(BaseModel):
    status: str  # "IN_PROGRESS" or "SUCCESS" or "FAILED"
    current_task: str
    use_tool: Optional[str] = None
    reasoning: str
    next_steps: List[str] = []

class ExecutorOutput(BaseModel):
    task_completed: bool
    result: str
    errors: List[str] = []
    additional_info: str = ""

# System prompts - merged with task instructions
PLANNER_SYSTEM_PROMPT = """
planner:
  role: >
    Planner Agent
  goal: >
    Analyze user requests and generate structured, executable workflows 
    based on available agents/tools. 
    You do not perform tasks directly — instead, you design a logical plan 
    and coordinate step-by-step execution through an executor agent.

  backstory: >
    You are a workflow planning expert AI. Your job is to deeply understand 
    the user's request, break it down into sequential or branching tasks, 
    and express it in a structured JSON format. 
    You ensure each task is tied to a specific tool/agent (from the provided list), 
    while also tracking progress and handling errors gracefully. 
    You strictly adhere to the required format and never invoke unavailable tools.

  output_format: |
    Always respond in JSON with the following fields:
    {
      "status": "IN_PROGRESS" | "SUCCESS" | "FAILED",
      "current_task": "Clear description of the next task to execute",
      "use_tool": "Which tool/agent should be used for this task",
      "reasoning": "Why this task is needed and how it fits the overall workflow",
      "next_steps": ["list", "of", "remaining", "planned", "tasks"]
    }

  rules: |
    - "SUCCESS" only when the full user request has been completed.
    - "FAILED" if the workflow cannot be completed due to errors.
    - Keep "IN_PROGRESS" while there are still tasks left.
    - Always ground tasks in the provided tool/agent list.
    - Ensure workflows are logically ordered and modular.
    - You may design branching dependencies if required, but always 
      provide the *next actionable step* for execution.
    - Adjust the plan dynamically if intermediate steps fail or 
      produce unexpected results.

Instructions for Planning:

1. INITIAL CALL (when no execution history exists):
   - Analyze the overall user request and provide the master plan overview.
   - Generate a list of sequential steps needed to complete the request.
   - Mark the first step as the `current_task`.

2. SUBSEQUENT CALLS (when execution history exists):
   - Use the execution results to update the status of completed steps.
   - Generate ONE specific next task at a time, always choosing the first `PENDING` step.
   - Adapt the plan if executor results suggest adjustments.
   - Only mention the HTML_PARSER_TOOL when interacting with webpage elements
     (clicking, filling, dropdowns, navigation links), but NOT for system-level
     tasks like scrolling, hovering, or screenshots.

3. TASK COMPLETION DETECTION:
   - Set `task_is_final` to true ONLY when:
     • The executor has successfully completed the final step
     • No further meaningful actions are required to fulfill the request
     • The task has reached a natural completion state (form submitted, data extracted, etc.)

4. STEP MANAGEMENT:
   - Always maintain a `steps` list where each step has:
     • step_id
     • task_name
     • status (PENDING, SUCCESS, or FAILED)
   - The `current_task` must always point to the first `PENDING` step.
   - Update statuses in the steps list as execution progresses.

5. PLANNING MODES:
   - INITIAL_PLANNING: Set up the master plan and mark step 1 as current_task.
   - ITERATIVE_PLANNING: Update step statuses, assign the next PENDING task as current_task,
     and clearly explain remaining work or declare completion if task_is_final is true.

Please provide the next task to execute with the tool to be used or mark as complete if done.
"""

EXECUTOR_SYSTEM_PROMPT = """
executor:
  role: Executor Agent
  goal: >
    Execute assigned automation tasks precisely and efficiently using the available MCP tools.
    Always focus on completing the task with the minimum required tool usage and zero unnecessary operations.

  backstory: >
    You are a precision task executor designed for reliability and efficiency. 
    You deeply understand tool usage trade-offs: when to parse HTML versus when to use direct browser actions.
    Your responsibility is to execute the given task, handle errors gracefully, 
    and report back structured results with absolute clarity — never hallucinating extra steps.

  CRITICAL EFFICIENCY RULES:
    - Always attempt direct tools (Screenshot, Navigation, Scroll) for simple operations.
    - Use HTML parsing only when selectors or DOM analysis is required (e.g., Click, Fill, Dropdown).
    - Never retry the same tool call multiple times without explicit reason.
    - If a tool returns None or empty output, consider it successful unless there is a clear error.
    - Do not invent tools or steps outside the provided list.

  execution_guidelines: |
    TOOL SELECTION MATRIX:

    Task Type → Tool Choice:
    • Take Screenshot → "Take Screenshot" (NO HTML parsing needed)
    • Navigate to URL → "Navigate To URL" (NO HTML parsing needed)  
    • Scroll Page → "Scroll Page" (NO HTML parsing needed)
    • Hover Element → "Hover Element" directly if selector known, else parse HTML first
    • Click Button → Parse HTML to find button selector, then use "Click Element"
    • Fill Form → Parse HTML to find input selectors, then use "Fill Input"
    • Select Dropdown → Parse HTML to find dropdown options, then use "Select Dropdown"
    • Smart Login → Use "Smart Login" tool, passing URL and parsed HTML

  error_handling: |
    - If a tool returns None → Treat as SUCCESS unless explicit error message is returned.
    - If tool output is empty but action is inherently passive (e.g., navigation, scroll, screenshot), consider SUCCESS.
    - Never repeat identical failed tool calls; instead, report the error in results.
    - Capture all errors in the JSON response for planner visibility.

  completion_indicators: |
    When a task is complete, report using structured JSON. 
    Include phrases like "task completed", "automation complete", or "user request fulfilled" in the result.

  output_format: |
    Always respond in JSON with the following fields:
    {
      "task_completed": true | false,
      "result": "Description of what was accomplished",
      "errors": ["list", "of", "any", "errors", "encountered"],
      "additional_info": "Any additional context or information discovered"
    }

Instructions for Execution:

1. EXECUTION FOCUS:
   - Only complete the current step provided by the planner.
   - Do not look ahead to future steps.
   - Use available tools efficiently and avoid redundant operations.
   - Call the specified tool as required.

2. STATE AWARENESS:
   - Remember what was just done. If HTML was fetched already for the current page, do not call the HTML parser again.
   - Analyze the existing HTML content to extract selectors for browser actions.
   - Avoid repeated HTML fetches for the same page.

3. HTML PARSER TOOL USAGE (STRICT):
   - Call fetch_and_clean_html_tool ONLY when interacting with webpage elements:
     ✅ Clicking buttons
     ✅ Filling forms
     ✅ Selecting dropdowns
     ✅ Finding links to navigate
   - DO NOT use HTML parser for:
     ❌ Taking screenshots
     ❌ Scrolling
     ❌ Hovering
     ❌ Navigating to known URLs
   - Call HTML parser only once per page unless navigating to a new page or after significant page changes.
   - Extract selectors from HTML for Playwright tools:
     • id="button1" → #button1
     • class="submit-btn" → .submit-btn
     • Position x="128" y="281" → (128, 281)
     • href="/login" → use for navigation
     • name="username" → [name="username"]

4. EFFICIENT TOOL USAGE FLOW:
   1. Analyze the task: Do I need to interact with specific webpage elements?
   2. If YES → Use fetch_and_clean_html_tool → Extract selectors → Use appropriate tools
   3. If NO → Use direct tools (Take Screenshot, Navigate To URL, Scroll Page, etc.)

5. TASK COMPLETION & ERROR HANDLING:
   - If a tool returns None or empty output, consider it successful unless an explicit error occurs.
   - Do not retry identical tool calls multiple times.
   - Provide clear feedback on whether this step represents completion of the overall user request.
   - Focus on efficiency and minimal tool usage.

Please execute this task using the appropriate MCP tool and provide structured feedback to help the planner adapt subsequent steps.
"""

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
    ]
    # env={"DISPLAY": ":1", **os.environ}  # Use :1 instead of :0
)

class MCPOpenAIClient:
    def __init__(self, openai_api_key: str):
        self.openai_planner_client = AsyncOpenAI(api_key=openai_api_key)
        self.openai_executor_client = AsyncOpenAI(api_key=openai_api_key)
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
            # Clean up in reverse order, but without using asyncio.wait_for
            # since that creates new tasks which cause the scope issues
            logger.info("Cleaning up MCP session...")
            
            if session:
                try:
                    # Clean up session in the same task context
                    await session_ctx.__aexit__(None, None, None)
                    logger.info("Session cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up session: {e}")
            
            if stdio_ctx:
                try:
                    # Clean up stdio context in the same task context  
                    await stdio_ctx.__aexit__(None, None, None)
                    logger.info("Stdio context cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up stdio context: {e}")
            
            logger.info("MCP session cleanup completed")
    
    async def call_openai_planner(self, user_request: str, iteration: int, execution_history: List[Dict] = None) -> PlannerOutput:
        """Call OpenAI with planner system prompt"""
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": f"""
User Request: {user_request}

Available Tools: {json.dumps(self.available_tools, indent=2)}
Available Resources: {json.dumps(self.available_resources, indent=2)}

Execution History: {json.dumps(execution_history or [], indent=2)}
Give response in JSON format only.
"""}
        ]
        # if iteration ==1:
        #     messages = messages
        # else:
        #     messages.pop(0)
        
        try:
            # logger.info(iteration)
            # logger.info(type(iteration))
            # logger.info(messages)
            response = await self.openai_planner_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=1
            )
            logger.info(f"OpenAI planner response: {response.choices[0].message.content}")
            planner_data = json.loads(response.choices[0].message.content)
            logger.info(f"Planner response: {json.dumps(planner_data, indent=2)}")
            return PlannerOutput(**planner_data)
            
        except Exception as e:
            logger.error(f"Error in planner call: {e}")
            return PlannerOutput(
                status="FAILED",
                current_task="",
                use_tool = "",
                reasoning=f"Failed to get planner response: {e}"
            )
    
    async def call_openai_executor(self, task: str, session: ClientSession, use_tool: str, iteration: int, context: str = "") -> ExecutorOutput:
        """Call OpenAI with executor system prompt"""
        
        # Create tools in the new OpenAI tools format (not functions)
        detailed_tools = self.available_tools
        tools = []
        for tool in self.available_tools:
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool['name'],
                    "description": tool['description'],
                    "parameters": tool.get('parameters', {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            }
            tools.append(tool_def)
        
        messages = [
            {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Task to Execute: {task}
Use Tool: {use_tool}
Available Tools: {json.dumps([{'name': t['name'], 'description': t['description']} for t in detailed_tools], indent=2)}
Give Response in JSON format only.
"""}
        ]
        # if iteration==1:
        #     messages = messages
        # else:   
        #     messages.pop(0)
        
        try:
            response = await self.openai_executor_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=1
            )
            logger.info(f"OpenAI executor response: {response.choices[0].message.content}")
            
            # Handle tool calls (new format)
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]  # Take first tool call
                tool_name = tool_call.function.name
                
                logger.info(f"OpenAI selected tool: {tool_name}")
                
                try:
                    # Parse arguments
                    if tool_call.function.arguments:
                        arguments = json.loads(tool_call.function.arguments)
                    else:
                        arguments = {}
                    
                    logger.info(f"Calling MCP tool '{tool_name}' with arguments: {arguments}")
                    
                    # Call the MCP tool
                    tool_result = await session.call_tool(tool_name, arguments=arguments)
                    
                    result_text = ""
                    for content in tool_result.content:
                        if isinstance(content, types.TextContent):
                            result_text += content.text
                    
                    logger.info(f"Tool {tool_name} result: {result_text}")
                    
                    return ExecutorOutput(
                        task_completed=True,
                        result=f"Successfully executed {tool_name}: {result_text}",
                        additional_info=f"Tool {tool_name} executed successfully"
                    )
                    
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    return ExecutorOutput(
                        task_completed=False,
                        result="",
                        errors=[f"Error executing tool {tool_name}: {str(e)}"]
                    )
            else:
                # No tool call made
                logger.warning("OpenAI did not make a tool call")
                response_content = response.choices[0].message.content or "No response content"
                
                return ExecutorOutput(
                    task_completed=False,
                    result=response_content,
                    errors=["No tool was called by OpenAI"]
                )
                    
        except Exception as e:
            logger.error(f"Error in executor call: {e}")
            return ExecutorOutput(
                task_completed=False,
                result="",
                errors=[f"Error in executor call: {str(e)}"]
            )
    
    async def process_user_request(self, user_request: str) -> Dict[str, Any]:
        """Main function that processes user request with planner-executor loop"""
        logger.info(f"🚀 Processing request: {user_request}")
        print("="*50)
        
        execution_history = []
        max_iterations = 10
        iteration = 0
        
        try:
            # Use the context manager for the entire processing session
            async with self.get_mcp_session() as session:
                while iteration < max_iterations:
                    iteration += 1
                    logger.info(f"📋 Planning Iteration {iteration}")
                    # logger.info(type(iteration))
                    
                    # Get plan from planner
                    planner_output = await self.call_openai_planner(user_request, iteration, execution_history)
                    logger.info(f"Status: {planner_output.status}")
                    logger.info(f"Current Task: {planner_output.current_task}")
                    logger.info(f"Use_tool: {planner_output.use_tool}")
                    logger.info(f"Reasoning: {planner_output.reasoning}")
                    
                    # Check if we're done
                    if planner_output.status == "SUCCESS":
                        logger.info("✅ Task completed successfully!")
                        return {
                            "status": "success",
                            "iterations": iteration,
                            "execution_history": execution_history
                        }
                    elif planner_output.status == "FAILED":
                        logger.info("❌ Task failed!")
                        return {
                            "status": "failed",
                            "reason": planner_output.reasoning,
                            "iterations": iteration,
                            "execution_history": execution_history
                        }
                    
                    # Execute current task - pass session directly
                    logger.info(f"⚡ Executing: {planner_output.current_task}")
                    executor_output = await self.call_openai_executor(
                        planner_output.current_task,
                        session,  # Pass session directly
                        planner_output.use_tool,
                        iteration,
                        f"Overall goal: {user_request}",
                    )
                    
                    logger.info(f"Task Completed: {executor_output.task_completed}")
                    logger.info(f"Result: {executor_output.result}")
                    if executor_output.errors:
                        logger.warning(f"Errors: {executor_output.errors}")
                    
                    # Add to history
                    execution_history.append({
                        "iteration": iteration,
                        "planned_task": planner_output.current_task,
                        "execution_result": {
                            "completed": executor_output.task_completed,
                            "result": executor_output.result,
                            "errors": executor_output.errors,
                            "additional_info": executor_output.additional_info
                        }
                    })
                
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

# if __name__ == "__main__":
#     exit_code = main()
#     sys.exit(exit_code)