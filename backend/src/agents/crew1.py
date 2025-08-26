# from crewai import Crew, Agent, Process, Task, LLM
# from pydantic import BaseModel , Field, RootModel
# import os
# import json

# import time
# import yaml
# import asyncio
# from src.utils.connection_manager import manager
# from crewai.project import CrewBase, agent, crew, task
# import logging
# from src.agents.tools.browser_tools import GoToPageTool,FetchAndCleanHTMLTool, GoBackTool, ReloadPageTool, GetCurrentURL, HoverElementTool, SelectDropdownTool, ScrollPageTool, DoubleClickTool, TextDeleteTool, TakeScreenshotTool, ClickElementTool, FillInputTool
# from src.agents.utils.browser_manager import BrowserManager
# from playwright.async_api import Page # pyright: ignore[reportMissingImports]
# from typing import List, Optional, Literal
# from enum import Enum
# from typing import Union
# import re
# logging.basicConfig(level=logging.INFO)

# logger = logging.getLogger(__name__)

# if not os.getenv("GEMINI_API_KEY"):
#     raise ValueError("GEMINI_API_KEY environment variable is not set")

# try:
#     llm = LLM(
#         model="gemini/gemini-2.5-flash-lite",
#         api_key=os.getenv("GEMINI_API_KEY"),
#         temperature=0.7,
#     )
#     logger.info("CrewAI LLM initialized successfully")
# except Exception as e:
#     logger.error(f"LLM initialization failed: {e}")
#     raise


# # Declares a full crewai project and collects and links @agent, @task, @crew
# # Without this manually sab crew ko batana padega
# # 📦 Under the hood, it probably collects all decorated methods and makes them accessible as .agents, .tasks, and .crew().

# class ExecutorOutputFormat(BaseModel):
#     status: Literal["SUCCESS", "FAILURE", "PARTIAL_FAILURE"]
#     step_description: str
#     result_summary: str
#     error_details: Optional[str] = None
#     suggestions_for_planner: Optional[str] = None
#     outputs_created: List[str] = Field(default_factory=list)
#     next_step_context: Optional[str] = None

# class StepStatus(str, Enum):
#     PENDING = "PENDING"
#     IN_PROGRESS = "IN_PROGRESS"
#     SUCCESS = "SUCCESS"
#     FAILURE = "FAILURE"
#     PARTIAL_FAILURE = "PARTIAL_FAILURE"


# class Step(BaseModel):
#     step_id: int
#     task_name: str
#     status: StepStatus = StepStatus.PENDING


# class InitialPlanning(BaseModel):
#     session_type: Literal["INITIAL_PLANNING"]
#     overall_task_name: str
#     master_thought: str
#     estimated_steps: str
#     steps: List[Step]
#     current_task: Step


# class IterativePlanning(BaseModel):
#     session_type: Literal["ITERATIVE_PLANNING"]
#     overall_task_name: str
#     progress_analysis: str
#     adaptation_reasoning: str
#     steps: List[Step]
#     current_task: Step
#     remaining_work: str
#     task_is_final: bool = False


# # Unified Planner Output Format
# class PlannerOutputFormat(RootModel[Union[InitialPlanning, IterativePlanning]]):
#     pass

# @CrewBase
# class ExecutorCrew:

#     def __init__(self, PAGE: Page):
#         self.page=PAGE
#         self.crew_instance=None
#         self._executor_task=None

#         try:
#             config_dir = os.path.join(os.path.dirname(__file__), "config")
#             with open(os.path.join(config_dir, "agents.yaml"), 'r') as file:
#                 self.agents_config = yaml.safe_load(file)
#             with open(os.path.join(config_dir, "tasks.yaml"), 'r') as file:
#                 self.tasks_config = yaml.safe_load(file)
#             with open(os.path.join(config_dir, "tools.yaml"), 'r') as file:
#                 self.tools_config = yaml.safe_load(file)

#             self.goto_page_tool = GoToPageTool(
#                 name=self.tools_config['goto_page_tool']['name'],
#                 description=self.tools_config['goto_page_tool']['description'],
#                 page=self.page
#             )

#             self.fetch_and_clean_html_tool = FetchAndCleanHTMLTool(
#                 name=self.tools_config['fetch_and_clean_html_tool']['name'],
#                 description=self.tools_config['fetch_and_clean_html_tool']['description'],
#                 page=self.page
#             )
#             self.take_screenshot_tool = TakeScreenshotTool(
#                 name=self.tools_config['take_screenshot_tool']['name'],
#                 description=self.tools_config['take_screenshot_tool']['description'],
#                 page=self.page
#             )

#             self.go_back_tool = GoBackTool(
#                 name=self.tools_config['go_back_tool']['name'],
#                 description=self.tools_config['go_back_tool']['description'],
#                 page=self.page
#             )
#             self.reload_page_tool = ReloadPageTool(
#                 name=self.tools_config['reload_page_tool']['name'],
#                 description=self.tools_config['reload_page_tool']['description'],
#                 page=self.page
#             )
#             self.get_current_url = GetCurrentURL(
#                 name=self.tools_config['get_current_url']['name'],
#                 description=self.tools_config['get_current_url']['description'],
#                 page=self.page
#             )
#             self.hover_element_tool = HoverElementTool(
#                 name=self.tools_config['hover_element_tool']['name'],
#                 description=self.tools_config['hover_element_tool']['description'],
#                 page=self.page
#             )
#             self.select_dropdown_tool = SelectDropdownTool(
#                 name=self.tools_config['select_dropdown_tool']['name'],
#                 description=self.tools_config['select_dropdown_tool']['description'],
#                 page=self.page
#             )

#             self.scroll_page_tool = ScrollPageTool(
#                 name=self.tools_config['scroll_page_tool']['name'],
#                 description=self.tools_config['scroll_page_tool']['description'],
#                 page=self.page
#             )
#             self.double_click_tool = DoubleClickTool(
#                 name=self.tools_config['double_click_tool']['name'],
#                 description=self.tools_config['double_click_tool']['description'],
#                 page=self.page
#             )
#             self.text_delete_tool = TextDeleteTool(
#                 name=self.tools_config['text_delete_tool']['name'],
#                 description=self.tools_config['text_delete_tool']['description'],
#                 page=self.page
#             )

#             self.click_element_tool = ClickElementTool(
#                 name=self.tools_config['click_element_tool']['name'],
#                 description=self.tools_config['click_element_tool']['description'],
#                 page=self.page
#             )

#             self.fill_input_tool = FillInputTool(
#                 name=self.tools_config['fill_input_tool']['name'],
#                 description=self.tools_config['fill_input_tool']['description'],
#                 page=self.page
#             )

#         except (FileNotFoundError, yaml.YAMLError) as e:
#             logger.error(f"Failed to load or parse configuration: {e}")
#             raise


#     @agent
#     def executor_agent(self) -> Agent:
#         return Agent(
#             config=self.agents_config["executor"],
#             tools=[self.goto_page_tool,
#                    self.take_screenshot_tool,
#                    self.fetch_and_clean_html_tool,
#                    self.hover_element_tool,
#                    self.get_current_url,
#                    self.go_back_tool,
#                    self.reload_page_tool,self.select_dropdown_tool,
#                    self.scroll_page_tool,
#                    self.double_click_tool,
#                    self.text_delete_tool,
#                    self.click_element_tool,
#                    self.fill_input_tool],
#             output_json=ExecutorOutputFormat,
#             llm=llm,
#             verbose=True,
#         )

   
#     @task
#     def execution_task(self) -> Task:
#         if(self._executor_task is None):
#             self._executor_task=Task(
#             config=self.tasks_config["execution_task"],
#             agent=self.executor_agent(),
#             output_json=ExecutorOutputFormat,
#         )
#         return self._executor_task
    
#     @crew
#     def executor_crew(self) -> Crew:

#         if(self.crew_instance is None):
#             self.crew_instance= Crew(
         
#             agents=self.agents, 
#             tasks=self.tasks,
#             process=Process.sequential,
#             verbose=True,
#             memory=False,
#         )
#             return self.crew_instance
    


# @CrewBase
# class PlannerCrew:
    
#     def __init__(self):
#         logger.info("Inside Planner crew")
#         self.crew_instance=None
#         self._planner_task=None

#         try:
#             logger.info("Trying Inside Planner crew")
#             config_dir = os.path.join(os.path.dirname(__file__), "config")
#             with open(os.path.join(config_dir, "agents.yaml"), 'r') as file:
#                 self.agents_config = yaml.safe_load(file)
#             with open(os.path.join(config_dir, "tasks.yaml"), 'r') as file:
#                 self.tasks_config = yaml.safe_load(file)
#             with open(os.path.join(config_dir, "tools.yaml"), 'r') as file:
#                 self.tools_config = yaml.safe_load(file)

            

#         except (FileNotFoundError, yaml.YAMLError) as e:
#             logger.error(f"Failed to load or parse configuration: {e}")
#             raise

#     @agent
#     def planner_agent(self) -> Agent:
#         return Agent(
#             config=self.agents_config["planner"],
#             tools=[],
#             llm=llm,
#             verbose=True,
#             output_json=PlannerOutputFormat
#         )


#     @task
#     def planner_task(self) -> Task:
#         if(self._planner_task is None):
#             self._planner_task= Task(
#             config=self.tasks_config["planner_task"],
#             agent=self.planner_agent(),
#             output_json=PlannerOutputFormat,
#         )
#         return self._planner_task #if not new return ongoing one it will have earlier idea
    
    
#     @crew
#     def planner_crew(self) -> Crew:
#         logger.info("Inside planner crew")
#         if(self.crew_instance is None):
#             self.crew_instance= Crew(
         
#             agents=self.agent, 
#             tasks=self.task,
#             process=Process.sequential,
#             verbose=True,
#             memory=False,
#         )
#         logger.info("hello")
#         return self.crew_instance

# class MasterCrew:

#     def __init__(self, PAGE: Page):
#         self.page=PAGE
#         self.browser_manager = BrowserManager()
#         self.execution_history=[] #track iterations

#     def run_iterative_planner_executor(self, user_request, max_iterations=10):
        
#         logger.info(f"🚀 Starting automation task: '{user_request}'")
#         logger.info(f"📊 Max iterations: {max_iterations}")

#         for iteration in range(max_iterations):
#             logger.info(f"🔄 Starting iteration {iteration+1}/{max_iterations}")

#             kickoff_inputs_planner = {
#                 "user_request": user_request,
#                 "agents_list": ["executor_agent"],
#                 "execution_feedback": self.execution_history[-1] if self.execution_history else None,
#                 "progress_state": f"Iteration {iteration+1}, completed {len(self.execution_history)} tasks",
#                 "iteration": iteration+1,
#             }
#             kickoff_inputs_executor = {}
#             logger.info("📋 Planner_Running")
#             try: 
            
#                 Planner=PlannerCrew()
#                 planner_output=Planner.planner_crew().kickoff(inputs=kickoff_inputs_planner)
#                 logger.info("📋 Planner_Output:",planner_output)
#                 planner_output=parse_json_output(planner_output)
#                 logger.info("📋 Planner_Output_Refined:",planner_output)

#                 if isinstance(planner_output, str):
#                     try:
#                         planner_output = json.loads(planner_output)
#                         print("Inside Agent1:", planner_output)
#                     except Exception as e:
#                         logger.error(f"Failed to parse event.output JSON: {e}")
#                         planner_output = {}

#                 session_type = planner_output.get("session_type")
#                 print("session_type:",session_type)
               
#                 current_task = planner_output.get("current_task", {})
#                 kickoff_inputs_executor["current_task"]=current_task
#                 # 1. INITIAL PLANNING
#                 if session_type == "INITIAL_PLANNING":
#                     # Send structured JSON data for workflow visualization
#                     workflow_data = {
#                         "session_type": "INITIAL_PLANNING",
#                         "overall_task_name": planner_output.get('overall_task_name', ''),  # ✅ Fixed
#                         "master_thought": planner_output.get('master_thought', ''),        # ✅ Fixed
#                         "estimated_steps": planner_output.get('estimated_steps', 0),       # ✅ Fixed
#                         "steps": planner_output.get("steps", []),                          # ✅ Fixed
#                         "current_task": planner_output.get("current_task", {}),            # ✅ Fixed
#                         "timestamp": time.time()
#                     }
                    
#                     asyncio.create_task(manager.broadcast(json.dumps(workflow_data)))

#                 # 2. ITERATIVE PLANNING
#                 elif session_type == "ITERATIVE_PLANNING":
#                     # Send structured JSON data for workflow updates
#                     workflow_data = {
#                         "session_type": "ITERATIVE_PLANNING",
#                         "overall_task_name": planner_output.get('overall_task_name', ''),  # ✅ Fixed
#                         "master_thought": planner_output.get('master_thought', ''),        # ✅ Fixed
#                         "estimated_steps": planner_output.get('estimated_steps', 0),       # ✅ Fixed
#                         "steps": planner_output.get("steps", []),                          # ✅ Fixed
#                         "current_task": planner_output.get("current_task", {}),            # ✅ Fixed
#                         "timestamp": time.time()
#                     }
                    
#                     asyncio.create_task(manager.broadcast(json.dumps(workflow_data)))
                    
#             except Exception as e:
#                 logger.error(f"❌ Error in iteration {iteration+1}: {e}")
#                 continue



#             try:


#                 Executor=ExecutorCrew(PAGE=self.page)
#                 executor_output=Executor.executor_crew().kickoff(inputs=kickoff_inputs_executor)
#                 logger.info("📋 Executor_Output:",executor_output)
#                 executor_output=parse_json_output(executor_output)
#                 logger.info("📋 Executor_Output_Refined:",executor_output)

#                 executor_output = executor_output.model_dump_json()
#                 if isinstance(executor_output, str):
#                     try:
#                         executor_output = json.loads(executor_output)
#                         print("Inside Agent1:", executor_output)
#                     except Exception as e:
#                         logger.error(f"Failed to parse event.output JSON: {e}")
#                         output = {}
                    
#                 final_result = executor_output.get("json_dict", executor_output)
#                 self.execution_history.append(final_result)
                
#                 # efficiency_check = self.validate_execution_efficiency(final_result)
#                 # if not efficiency_check["efficient"]:
#                 #     logger.info("💡 Consider optimizing tool usage for better performance")
                
#                 # logger.info(f"💾 Stored execution result: {final_result}")
                
#             except Exception as e:
#                 logger.error(f"❌ Error converting result to JSON in iteration {iteration+1}: {e}")
#                 continue

#             if self.is_task_complete(planner_output):
#                 logger.info(f"🎉 Task completed successfully after {iteration+1} iterations")
#                 logger.info(f"📋 Final result: {final_result}")
#                 return {
#                     "status": "COMPLETED",
#                     "iterations": iteration + 1,
#                     "final_result": final_result,
#                     "execution_history": self.execution_history
#                 }
                
#             if iteration == max_iterations - 1:
#                 logger.warning(f"⚠️ Reached maximum iterations ({max_iterations}) without completion")
#                 return {    
#                     "status": "MAX_ITERATIONS_REACHED", 
#                     "iterations": iteration + 1,
#                     "final_result": final_result if 'final_result' in locals() else None,
#                     "execution_history": self.execution_history
#                 }
                
#             logger.info(f"🔄 Continuing to iteration {iteration+2}")
        
#         # This should never be reached due to the logic above, but included for completeness
#         return {
#             "status": "UNKNOWN_ERROR",
#             "iterations": max_iterations,
#             "execution_history": self.execution_history
#         }
    


#     def is_task_complete(self, planner_output):
#         try:
#             if (planner_output.get("session_type") == "ITERATIVE_PLANNING" and 
#                 planner_output.get("task_is_final", False)):
#                 logger.info("✅ Task marked as final by planner")
#                 return True
                
#             if self.execution_history:
#                 last_execution = self.execution_history[-1]
                
#                 if last_execution.get("status") == "SUCCESS":
                    
#                     suggestions = last_execution.get("suggestions_for_planner", "").lower()
#                     completion_phrases = [
#                         "user request is now complete",
#                         "task completed",
#                         "user request fulfilled",
#                         "automation complete",
#                         "process finished",
#                         "workflow completed",
#                         "request complete"
#                     ]
                    
#                     if any(phrase in suggestions for phrase in completion_phrases):
#                         logger.info("✅ Task completion detected from executor suggestions")
#                         return True
                    
#                     # Check next_step_context for completion indicators
#                     next_step_context = last_execution.get("next_step_context", "").lower()
#                     if any(phrase in next_step_context for phrase in completion_phrases):
#                         logger.info("✅ Task completion detected from executor context")
#                         return True
                
#             return False
            
#         except Exception as e:
#             logger.error(f"❌ Error checking task completion: {e}")
#             return False
    
#     def validate_execution_efficiency(self, execution_result):

#         warnings = []
        
#         try:
#             step_description = execution_result.get("step_description", "").lower()
            
#             if "screenshot" in step_description:
#                 result_summary = execution_result.get("result_summary", "").lower()
#                 if "html" in result_summary or "parsed" in result_summary:
#                     warnings.append("⚠️ HTML parsing may have been unnecessary for screenshot task")

#             if "navigate" in step_description:
#                 result_summary = execution_result.get("result_summary", "").lower()
#                 if "html" in result_summary or "parsed" in result_summary:
#                     warnings.append("⚠️ HTML parsing may have been unnecessary for navigation task")
                    
            
#             if warnings:
#                 for warning in warnings:
#                     logger.warning(warning)
                    
#             return {
#                 "efficient": len(warnings) == 0,
#                 "warnings": warnings
#             }
            
#         except Exception as e:
#             logger.error(f"❌ Error validating execution efficiency: {e}")
#             return {"efficient": True, "warnings": []}





# def parse_json_output(output):
#     if isinstance(output, str):
#         # Find JSON block between ```json and ```
#         json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
#         if json_match:
#             json_str = json_match.group(1).strip()
#         else:
#             # Fallback: look for any JSON-like content starting with {
#             brace_start = output.find('{')
#             if brace_start != -1:
#                 json_str = output[brace_start:].strip()
#             else:
#                 json_str = output.strip()
        
#         return json.loads(json_str)
#     return output


            
