'''import time
import logging
import asyncio
import json

from crewai.utilities.events import (
    CrewKickoffStartedEvent,
    CrewKickoffCompletedEvent,
    AgentExecutionStartedEvent,
    AgentExecutionCompletedEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    ToolUsageStartedEvent,
    ToolUsageFinishedEvent,
    LLMCallCompletedEvent,
    LLMCallStartedEvent
)

from src.utils.connection_manager import manager
from crewai.utilities.events.base_event_listener import BaseEventListener

logger = logging.getLogger("crew.listeners.basic")
logger.setLevel(logging.INFO)

class BasicListener(BaseEventListener):
    def __init__(self):
        super().__init__()

    def setup_listeners(self, crewai_event_bus):
        # Crew kickoff
        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_crew_started(source, event):
            print("Inside Agent")
            asyncio.create_task(manager.broadcast(f"👥 Crew started: {event.crew_name}"))

        # Agent finished something (planner or executor)
        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def on_agent_completed(source, event):
            print("Inside Agent:", event.output)

            output = event.output
            # Parse JSON if output is a string
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except Exception as e:
                    logger.error(f"Failed to parse event.output JSON: {e}")
                    output = {}

            session_type = output.get("session_type")
            print("session_type:",session_type)
            # 1. INITIAL PLANNING
            if session_type == "INITIAL_PLANNING":
                asyncio.create_task(manager.broadcast(f"Initial Planning for: {output.get('overall_task_name')}"))
                asyncio.create_task(manager.broadcast(f"Thought: {output.get('master_thought')}"))
                asyncio.create_task(manager.broadcast(f"Estimated steps: {output.get('estimated_steps')}"))

                asyncio.create_task(manager.broadcast("📋 Planned Steps:"))
                for step in output.get("steps", []):
                    asyncio.create_task(manager.broadcast(f"   Step {step['step_id']}: {step['task_name']} → {step['status']}"))

                current_task = output.get("current_task", {})
                asyncio.create_task(manager.broadcast(f"First Task: {current_task.get('task_name')}"))

            # 2. ITERATIVE PLANNING
            elif session_type == "ITERATIVE_PLANNING":
                asyncio.create_task(manager.broadcast(f"Iterative Planning update for: {output.get('overall_task_name')}"))
                asyncio.create_task(manager.broadcast(f"Progress: {output.get('progress_analysis')}"))
                asyncio.create_task(manager.broadcast(f"Reasoning: {output.get('adaptation_reasoning')}"))

                asyncio.create_task(manager.broadcast("Updated Steps:"))
                for step in output.get("steps", []):
                    asyncio.create_task(manager.broadcast(f"   Step {step['step_id']}: {step['task_name']} → {step['status']}"))

                current_task = output.get("current_task", {})
                asyncio.create_task(manager.broadcast(f"Next Task: {current_task.get('task_name')}"))

                if output.get("task_is_final", False):
                    asyncio.create_task(manager.broadcast("All tasks completed successfully!"))

            # 3. EXECUTOR RESULTS
            elif "status" in output and "result_summary" in output:
                status_icon = "✅" if output.get("status") == "SUCCESS" else "❌"
                asyncio.create_task(manager.broadcast(f"{status_icon} Executor finished: {output.get('step_description')}"))
                asyncio.create_task(manager.broadcast(f"Result: {output.get('result_summary')}"))

                if output.get("error_details"):
                    asyncio.create_task(manager.broadcast(f"Error: {output.get('error_details')}"))

                if output.get("suggestions_for_planner"):
                    asyncio.create_task(manager.broadcast(f"Suggestions: {output.get('suggestions_for_planner')}"))

                if output.get("outputs_created"):
                    asyncio.create_task(manager.broadcast(f"Outputs: {output.get('outputs_created')}"))

                if output.get("next_step_context"):
                    asyncio.create_task(manager.broadcast(f"Context for next step: {output.get('next_step_context')}"))

        # Tool usage logs
        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_started(source, event):
            asyncio.create_task(manager.broadcast(f"Tool started: {event.tool_name} args={event.tool_args}"))

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool_completed(source, event):
            asyncio.create_task(manager.broadcast(f"Subtask done: {event.tool_name}"))

basic_listener = BasicListener()


import time
import logging
import asyncio
import json

from crewai.utilities.events import (
    CrewKickoffStartedEvent,
    CrewKickoffCompletedEvent,
    AgentExecutionStartedEvent,
    AgentExecutionCompletedEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    ToolUsageStartedEvent,
    ToolUsageFinishedEvent,
    LLMCallCompletedEvent,
    LLMCallStartedEvent
)

from src.utils.connection_manager import manager
from crewai.utilities.events.base_event_listener import BaseEventListener

logger = logging.getLogger("crew.listeners.basic")
logger.setLevel(logging.INFO)

class BasicListener(BaseEventListener):
    def __init__(self):
        super().__init__()
        self.current_steps = {}  # Track current steps status
        self.overall_task_name = ""
        self.last_task_update_source = None  # Track which event updated last

    def setup_listeners(self, crewai_event_bus):
        # Crew kickoff
        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_crew_started(source, event):
            asyncio.create_task(manager.broadcast(f"👥 Crew started: {event.crew_name}"))

        # Task completion events - backup for status updates
        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_completed(source, event):
            # This fires when executor completes a task
            # Only update if planner hasn't updated recently
            if self.last_task_update_source != 'planner':
                for step_id, step_info in self.current_steps.items():
                    if step_info['status'] == 'PENDING':
                        # Mark first pending task as completed
                        self.current_steps[step_id]['status'] = 'SUCCESS'
                        status_display = self._get_status_display('SUCCESS')
                        asyncio.create_task(manager.broadcast(f"   {step_info['name']} {status_display}"))
                        self.last_task_update_source = 'task_event'
                        break
            
            # Reset the flag after a short delay
            asyncio.create_task(self._reset_update_source())

        # Agent finished something (planner or executor)
        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def on_agent_completed(source, event):
            output = event.output
            # Parse JSON if output is a string
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except Exception as e:
                    logger.error(f"Failed to parse event.output JSON: {e}")
                    output = {}

            session_type = output.get("session_type")
            
            # 1. INITIAL PLANNING - Show all subtasks initially
            if session_type == "INITIAL_PLANNING":
                self.overall_task_name = output.get('overall_task_name', 'Task')
                asyncio.create_task(manager.broadcast(f"📋 {self.overall_task_name}"))
                asyncio.create_task(manager.broadcast(""))  # Empty line for separation
                
                # Store and display all steps
                steps = output.get("steps", [])
                for step in steps:
                    step_id = step.get('step_id')
                    task_name = step.get('task_name')
                    status = step.get('status', 'PENDING')
                    
                    # Store current status
                    self.current_steps[step_id] = {
                        'name': task_name,
                        'status': status
                    }
                    
                    # Display with status in brackets
                    status_display = self._get_status_display(status)
                    asyncio.create_task(manager.broadcast(f"   {task_name} {status_display}"))

            # 2. ITERATIVE_PLANNING - Update changed statuses only
            elif session_type == "ITERATIVE_PLANNING":
                status_updated = False
                steps = output.get("steps", [])
                
                for step in steps:
                    step_id = step.get('step_id')
                    task_name = step.get('task_name')
                    new_status = step.get('status', 'PENDING')
                    
                    # Check if status changed
                    if step_id in self.current_steps:
                        old_status = self.current_steps[step_id]['status']
                        if old_status != new_status:
                            # Status changed, update and broadcast
                            self.current_steps[step_id]['status'] = new_status
                            status_display = self._get_status_display(new_status)
                            asyncio.create_task(manager.broadcast(f"   {task_name} {status_display}"))
                            status_updated = True
                            self.last_task_update_source = 'planner'
                    else:
                        # New step added
                        self.current_steps[step_id] = {
                            'name': task_name,
                            'status': new_status
                        }
                        status_display = self._get_status_display(new_status)
                        asyncio.create_task(manager.broadcast(f"   {task_name} {status_display}"))
                        status_updated = True

                # Check if task is final
                if output.get("task_is_final", False):
                    asyncio.create_task(manager.broadcast(""))  # Empty line
                    asyncio.create_task(manager.broadcast("✅ All tasks completed successfully!"))

        # Tool usage logs (simplified)
        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_started(source, event):
            # Only show tool name, not args for cleaner output
            asyncio.create_task(manager.broadcast(f"🔧 {event.tool_name}"))

    async def _reset_update_source(self):
        """Reset the update source flag after a delay to allow both events to work"""
        await asyncio.sleep(1)
        self.last_task_update_source = None

    def _get_status_display(self, status):
        """Convert status to display format with brackets"""
        status_map = {
            'PENDING': '[PENDING]',
            'SUCCESS': '[COMPLETED]',
            'FAILURE': '[FAILED]'
        }
        return status_map.get(status, f'[{status}]')

basic_listener = BasicListener()'''
import time
import logging
import asyncio
import json
from crewai.utilities.events import (
    CrewKickoffStartedEvent,
    CrewKickoffCompletedEvent,
    AgentExecutionStartedEvent,
    AgentExecutionCompletedEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    ToolUsageStartedEvent,
    ToolUsageFinishedEvent,
    LLMCallCompletedEvent,
    LLMCallStartedEvent
)
from src.utils.connection_manager import manager
from crewai.utilities.events.base_event_listener import BaseEventListener

logger = logging.getLogger("crew.listeners.basic")
logger.setLevel(logging.INFO)

class BasicListener(BaseEventListener):
    def __init__(self):
        super().__init__()
        self.current_steps = {}
        self.displayed_steps = set()  # Track which steps we've already displayed

    def setup_listeners(self, crewai_event_bus):
        
        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def on_agent_completed(source, event):
            output = event.output
            
            # Parse JSON if output is a string
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except Exception as e:
                    logger.error(f"Failed to parse event.output JSON: {e}")
                    return

            session_type = output.get("session_type")
            
            if session_type == "INITIAL_PLANNING":
                self._handle_initial_planning(output)
            elif session_type == "ITERATIVE_PLANNING":
                self._handle_iterative_planning(output)

    def _handle_initial_planning(self, output):
        """Display all steps initially with PENDING status"""
        self.current_steps.clear()
        self.displayed_steps.clear()
        
        steps = output.get("steps", [])
        for step in steps:
            step_id = step.get('step_id')
            task_name = step.get('task_name')
            status = step.get('status', 'PENDING')
            
            self.current_steps[step_id] = {
                'name': task_name,
                'status': status
            }
            
            # Display: "Task name (PENDING)"
            display_text = f"{task_name} ({status})"
            asyncio.create_task(manager.broadcast(display_text))
            self.displayed_steps.add(step_id)

    def _handle_iterative_planning(self, output):
        """Update only the steps that changed status"""
        steps = output.get("steps", [])
        
        for step in steps:
            step_id = step.get('step_id')
            task_name = step.get('task_name')
            new_status = step.get('status', 'PENDING')
            
            # Check if this step exists and status changed
            if step_id in self.current_steps:
                old_status = self.current_steps[step_id]['status']
                if old_status != new_status:
                    # Status changed - update and broadcast
                    self.current_steps[step_id]['status'] = new_status
                    
                    # Display updated: "Task name (SUCCESS)"
                    display_text = f"{task_name} ({new_status})"
                    asyncio.create_task(manager.broadcast(display_text))
            
            # Handle new steps that weren't in initial planning
            elif step_id not in self.displayed_steps:
                self.current_steps[step_id] = {
                    'name': task_name,
                    'status': new_status
                }
                
                display_text = f"{task_name} ({new_status})"
                asyncio.create_task(manager.broadcast(display_text))
                self.displayed_steps.add(step_id)

basic_listener = BasicListener()
