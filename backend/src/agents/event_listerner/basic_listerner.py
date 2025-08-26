
# import time
# import logging
# import asyncio
# import json
# import re
# from crewai.utilities.events import (
#     CrewKickoffStartedEvent,
#     CrewKickoffCompletedEvent,
#     AgentExecutionStartedEvent,
#     AgentExecutionCompletedEvent,
#     TaskStartedEvent,
#     TaskCompletedEvent,
#     ToolUsageStartedEvent,
#     ToolUsageFinishedEvent,
#     LLMCallCompletedEvent,
#     LLMCallStartedEvent
# )

# from src.utils.connection_manager import manager
# from crewai.utilities.events.base_event_listener import BaseEventListener

# logger = logging.getLogger("crew.listeners.basic")
# logger.setLevel(logging.INFO)
# def parse_json_output(output):
#    if isinstance(output, str):
#        # Find JSON block between ```json and ```
#        json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
#        if json_match:
#            json_str = json_match.group(1).strip()
#        else:
#            # Fallback: look for any JSON-like content starting with {
#            brace_start = output.find('{')
#            if brace_start != -1:
#                json_str = output[brace_start:].strip()
#            else:
#                json_str = output.strip()
       
#        return json.loads(json_str)
#    return output
# class BasicListener(BaseEventListener):
#     def __init__(self):
#         super().__init__()

#     def setup_listeners(self, crewai_event_bus):
#         # Crew kickoff
#         @crewai_event_bus.on(CrewKickoffStartedEvent)
#         def on_crew_started(source, event):
#             print("Inside Agent")
#             # asyncio.create_task(manager.broadcast(f"👥 Crew started: {event.crew_name}"))

#         # Agent finished something (planner or executor)
#         @crewai_event_bus.on(AgentExecutionCompletedEvent)
#         def on_agent_completed(source, event):
            
#             output = event.output
#             # Parse JSON if output is a string
#             output=parse_json_output(output)
#             print("Inside Agent:", output)

#             if isinstance(output, str):
#                 try:
#                     output = json.loads(output)
#                     print("Inside Agent1:", output)
#                 except Exception as e:
#                     logger.error(f"Failed to parse event.output JSON: {e}")
#                     print("Inside Agent1 planner:", output)
#                     output = {}

#             session_type = output.get("session_type")
#             print("session_type:",session_type)
            
#             # 1. INITIAL PLANNING
#             if session_type == "INITIAL_PLANNING":
#                 # Send structured JSON data for workflow visualization
#                 workflow_data = {
#                     "session_type": "INITIAL_PLANNING",
#                     "overall_task_name": output.get('overall_task_name', ''),
#                     "master_thought": output.get('master_thought', ''),
#                     "estimated_steps": output.get('estimated_steps', 0),
#                     "steps": output.get("steps", []),
#                     "current_task": output.get("current_task", {}),
#                     "timestamp": time.time()
#                 }
                
#                 asyncio.create_task(manager.broadcast(json.dumps(workflow_data)))
                
#                 # Also send individual text messages for logging
#                 # asyncio.create_task(manager.broadcast(f"📋 Initial Planning for: {output.get('overall_task_name')}"))
#                 # asyncio.create_task(manager.broadcast(f"💭 Thought: {output.get('master_thought')}"))
#                 # asyncio.create_task(manager.broadcast(f"📊 Estimated steps: {output.get('estimated_steps')}"))

#                 current_task = output.get("current_task", {})
#                 # asyncio.create_task(manager.broadcast(f"▶️ First Task: {current_task.get('task_name')}"))

#             # 2. ITERATIVE PLANNING
#             elif session_type == "ITERATIVE_PLANNING":
#                 # Send structured JSON data for workflow updates
#                 workflow_data = {
#                     "session_type": "ITERATIVE_PLANNING",
#                     "overall_task_name": output.get('overall_task_name', ''),
#                     "progress_analysis": output.get('progress_analysis', ''),
#                     "adaptation_reasoning": output.get('adaptation_reasoning', ''),
#                     "steps": output.get("steps", []),
#                     "current_task": output.get("current_task", {}),
#                     "task_is_final": output.get("task_is_final", False),
#                     "timestamp": time.time()
#                 }
                
#                 asyncio.create_task(manager.broadcast(json.dumps(workflow_data)))
                
#                 # Also send individual text messages for logging
#                 # asyncio.create_task(manager.broadcast(f"🔄 Iterative Planning update for: {output.get('overall_task_name')}"))
#                 # asyncio.create_task(manager.broadcast(f"📈 Progress: {output.get('progress_analysis')}"))
#                 # asyncio.create_task(manager.broadcast(f"🧠 Reasoning: {output.get('adaptation_reasoning')}"))

#                 # current_task = output.get("current_task", {})
#                 # asyncio.create_task(manager.broadcast(f"➡️ Next Task: {current_task.get('task_name')}"))

#                 # if output.get("task_is_final", False):
#                 #     asyncio.create_task(manager.broadcast("🎉 All tasks completed successfully!"))

#             # 3. EXECUTOR RESULTS
#             elif "status" in output and "result_summary" in output:
#                 # Send structured JSON data for executor results
#                 executor_data = {
#                     "session_type": "EXECUTOR_RESULT",
#                     "status": output.get("status"),
#                     "step_description": output.get("step_description", ""),
#                     "result_summary": output.get("result_summary", ""),
#                     "error_details": output.get("error_details", ""),
#                     "suggestions_for_planner": output.get("suggestions_for_planner", ""),
#                     "outputs_created": output.get("outputs_created", ""),
#                     "next_step_context": output.get("next_step_context", ""),
#                     "timestamp": time.time()
#                 }
                
#                 asyncio.create_task(manager.broadcast(json.dumps(executor_data)))
                
#                 # Also send individual text messages for logging
#                 status_icon = "✅" if output.get("status") == "SUCCESS" else "❌"
#                 # asyncio.create_task(manager.broadcast(f"{status_icon} Executor finished: {output.get('step_description')}"))
#                 # asyncio.create_task(manager.broadcast(f"📋 Result: {output.get('result_summary')}"))

#                 # if output.get("error_details"):
#                 #     asyncio.create_task(manager.broadcast(f"⚠️ Error: {output.get('error_details')}"))

#                 # if output.get("suggestions_for_planner"):
#                 #     asyncio.create_task(manager.broadcast(f"💡 Suggestions: {output.get('suggestions_for_planner')}"))

#                 # if output.get("outputs_created"):
#                 #     asyncio.create_task(manager.broadcast(f"📁 Outputs: {output.get('outputs_created')}"))

#                 # if output.get("next_step_context"):
#                 #     asyncio.create_task(manager.broadcast(f"🔗 Context for next step: {output.get('next_step_context')}"))

#         # Tool usage logs
#         # @crewai_event_bus.on(ToolUsageStartedEvent)
#         # def on_tool_started(source, event):
#         #     # Send structured data for tool usage
#         #     tool_data = {
#         #         "session_type": "TOOL_STARTED",
#         #         "tool_name": event.tool_name,
#         #         "tool_args": event.tool_args,
#         #         "timestamp": time.time()
#         #     }
#             # asyncio.create_task(manager.broadcast(json.dumps(tool_data)))
#             # asyncio.create_task(manager.broadcast(f"🔧 Tool started: {event.tool_name}"))

#         # @crewai_event_bus.on(ToolUsageFinishedEvent)
#         # def on_tool_completed(source, event):
#         #     # Send structured data for tool completion
#         #     tool_data = {
#         #         "session_type": "TOOL_FINISHED",
#         #         "tool_name": event.tool_name,
#         #         "timestamp": time.time()
#         #     }
#             # asyncio.create_task(manager.broadcast(json.dumps(tool_data)))
#             # asyncio.create_task(manager.broadcast(f"✅ Tool finished: {event.tool_name}"))

# basic_listener = BasicListener()
# # import time
# # import logging
# # import asyncio
# # import json
# # from crewai.utilities.events import (
# #     CrewKickoffStartedEvent,
# #     CrewKickoffCompletedEvent,
# #     AgentExecutionStartedEvent,
# #     AgentExecutionCompletedEvent,
# #     TaskStartedEvent,
# #     TaskCompletedEvent,
# #     ToolUsageStartedEvent,
# #     ToolUsageFinishedEvent,
# #     LLMCallCompletedEvent,
# #     LLMCallStartedEvent
# # )

# # from src.utils.connection_manager import manager
# # from crewai.utilities.events.base_event_listener import BaseEventListener

# # logger = logging.getLogger("crew.listeners.basic")
# # logger.setLevel(logging.INFO)

# # class BasicListener(BaseEventListener):
# #     def __init__(self):
# #         super().__init__()

# #     def setup_listeners(self, crewai_event_bus):
# #         # Crew kickoff
# #         @crewai_event_bus.on(CrewKickoffStartedEvent)
# #         def on_crew_started(source, event):
# #             print("Inside Agent")
# #             asyncio.create_task(manager.broadcast(f"👥 Crew started: {event.crew_name}"))

# #         # Agent finished something (planner or executor)
# #         @crewai_event_bus.on(AgentExecutionCompletedEvent)
# #         def on_agent_completed(source, event):
# #             print("Inside Agent:", event.output)

# #             output = event.output
# #             # Parse JSON if output is a string
# #             if isinstance(output, str):
# #                 try:
# #                     output = json.loads(output)
# #                 except Exception as e:
# #                     logger.error(f"Failed to parse event.output JSON: {e}")
# #                     output = {}

# #             session_type = output.get("session_type")
# #             print("session_type:",session_type)
# #             # 1. INITIAL PLANNING
# #             if session_type == "INITIAL_PLANNING":
# #                 asyncio.create_task(manager.broadcast(f"Initial Planning for: {output.get('overall_task_name')}"))
# #                 asyncio.create_task(manager.broadcast(f"Thought: {output.get('master_thought')}"))
# #                 asyncio.create_task(manager.broadcast(f"Estimated steps: {output.get('estimated_steps')}"))

# #                 asyncio.create_task(manager.broadcast("📋 Planned Steps:"))
# #                 for step in output.get("steps", []):
# #                     asyncio.create_task(manager.broadcast(f"   Step {step['step_id']}: {step['task_name']} → {step['status']}"))

# #                 current_task = output.get("current_task", {})
# #                 asyncio.create_task(manager.broadcast(f"First Task: {current_task.get('task_name')}"))

# #             # 2. ITERATIVE PLANNING
# #             elif session_type == "ITERATIVE_PLANNING":
# #                 asyncio.create_task(manager.broadcast(f"Iterative Planning update for: {output.get('overall_task_name')}"))
# #                 asyncio.create_task(manager.broadcast(f"Progress: {output.get('progress_analysis')}"))
# #                 asyncio.create_task(manager.broadcast(f"Reasoning: {output.get('adaptation_reasoning')}"))

# #                 asyncio.create_task(manager.broadcast("Updated Steps:"))
# #                 for step in output.get("steps", []):
# #                     asyncio.create_task(manager.broadcast(f"   Step {step['step_id']}: {step['task_name']} → {step['status']}"))

# #                 current_task = output.get("current_task", {})
# #                 asyncio.create_task(manager.broadcast(f"Next Task: {current_task.get('task_name')}"))

# #                 if output.get("task_is_final", False):
# #                     asyncio.create_task(manager.broadcast("All tasks completed successfully!"))

# #             # 3. EXECUTOR RESULTS
# #             elif "status" in output and "result_summary" in output:
# #                 status_icon = "✅" if output.get("status") == "SUCCESS" else "❌"
# #                 asyncio.create_task(manager.broadcast(f"{status_icon} Executor finished: {output.get('step_description')}"))
# #                 asyncio.create_task(manager.broadcast(f"Result: {output.get('result_summary')}"))

# #                 if output.get("error_details"):
# #                     asyncio.create_task(manager.broadcast(f"Error: {output.get('error_details')}"))

# #                 if output.get("suggestions_for_planner"):
# #                     asyncio.create_task(manager.broadcast(f"Suggestions: {output.get('suggestions_for_planner')}"))

# #                 if output.get("outputs_created"):
# #                     asyncio.create_task(manager.broadcast(f"Outputs: {output.get('outputs_created')}"))

# #                 if output.get("next_step_context"):
# #                     asyncio.create_task(manager.broadcast(f"Context for next step: {output.get('next_step_context')}"))

# #         # Tool usage logs
# #         @crewai_event_bus.on(ToolUsageStartedEvent)
# #         def on_tool_started(source, event):
# #             asyncio.create_task(manager.broadcast(f"Tool started: {event.tool_name} args={event.tool_args}"))

# #         @crewai_event_bus.on(ToolUsageFinishedEvent)
# #         def on_tool_completed(source, event):
# #             asyncio.create_task(manager.broadcast(f"Tool finished: {event.tool_name}"))

# # basic_listener = BasicListener()
