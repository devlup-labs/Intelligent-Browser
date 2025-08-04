from crewai import Crew, Agent, Process, Task, LLM
from pydantic import BaseModel , Field, RootModel
import os
import json
import yaml
from crewai.project import CrewBase, agent, crew, task
import logging
from tools.browser_tools import GoToPageTool,FetchAndCleanHTMLTool, GoBackTool, ReloadPageTool, GetCurrentURL, HoverElementTool, SelectDropdownTool, ScrollPageTool, DoubleClickTool, TextDeleteTool, TextInputTool, TakeScreenshotTool
from utils.browser_manager import BrowserManager
from playwright.async_api import Page
from typing import List, Optional, Literal
from enum import Enum
from typing import Union
# from examples.planner_agent_example import examples

from utils.browser_manager import BrowserManager 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY environment variable is not set")

try:
    llm = LLM(
        model="gemini/gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.7
    )
    logger.info("CrewAI LLM initialized successfully")
except Exception as e:
    logger.error(f"LLM initialization failed: {e}")
    raise

# Declares a full crewai project and collects and links @agent, @task, @crew
# Without this manually sab crew ko batana padega
# 📦 Under the hood, it probably collects all decorated methods and makes them accessible as .agents, .tasks, and .crew().

class ExecutorOutputFormat(BaseModel):
    status: Literal["SUCCESS", "FAILURE", "PARTIAL_FAILURE"]
    step_description: str
    result_summary: str
    error_details: Optional[str] = None
    suggestions_for_planner: Optional[str] = None
    outputs_created: List[str] = Field(default_factory=list)
    next_step_context: Optional[str] = None

class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"


class Step(BaseModel):
    step_id: int
    task_name: str
    status: StepStatus = StepStatus.PENDING


class InitialPlanning(BaseModel):
    session_type: Literal["INITIAL_PLANNING"]
    overall_task_name: str
    master_thought: str
    estimated_steps: str
    steps: List[Step]
    current_task: Step


class IterativePlanning(BaseModel):
    session_type: Literal["ITERATIVE_PLANNING"]
    overall_task_name: str
    progress_analysis: str
    adaptation_reasoning: str
    steps: List[Step]
    current_task: Step
    remaining_work: str


# Unified Planner Output Format
class PlannerOutputFormat(RootModel[Union[InitialPlanning, IterativePlanning]]):
    pass

@CrewBase
class MasterCrew:

    def __init__(self, PAGE: Page):
        self.page=PAGE
        self.browser_manager = BrowserManager()
        self.execution_history=[] #track iterations
        #Used for cacheing
        self.crew_instance=None
        self._planner_task=None
        self._executor_task=None

        try:
            config_dir = os.path.join(os.path.dirname(__file__), "config")
            with open(os.path.join(config_dir, "agents.yaml"), 'r') as file:
                self.agents_config = yaml.safe_load(file)
            with open(os.path.join(config_dir, "tasks.yaml"), 'r') as file:
                self.tasks_config = yaml.safe_load(file)
            with open(os.path.join(config_dir, "tools.yaml"), 'r') as file:
                self.tools_config = yaml.safe_load(file)

            self.goto_page_tool = GoToPageTool(
                name=self.tools_config['goto_page_tool']['name'],
                description=self.tools_config['goto_page_tool']['description'],
                page=self.page
            )

            self.fetch_and_clean_html_tool = FetchAndCleanHTMLTool(
                name=self.tools_config['fetch_and_clean_html_tool']['name'],
                description=self.tools_config['fetch_and_clean_html_tool']['description'],
                page=self.page
            )
            self.take_screenshot_tool = TakeScreenshotTool(
                name=self.tools_config['take_screenshot_tool']['name'],
                description=self.tools_config['take_screenshot_tool']['description'],
                page=self.page
            )

            self.go_back_tool = GoBackTool(
                name=self.tools_config['go_back_tool']['name'],
                description=self.tools_config['go_back_tool']['description'],
                page=self.page
            )
            self.reload_page_tool = ReloadPageTool(
                name=self.tools_config['reload_page_tool']['name'],
                description=self.tools_config['reload_page_tool']['description'],
                page=self.page
            )
            self.get_current_url = GetCurrentURL(
                name=self.tools_config['get_current_url']['name'],
                description=self.tools_config['get_current_url']['description'],
                page=self.page
            )
            self.hover_element_tool = HoverElementTool(
                name=self.tools_config['hover_element_tool']['name'],
                description=self.tools_config['hover_element_tool']['description'],
                page=self.page
            )
            self.select_dropdown_tool = SelectDropdownTool(
                name=self.tools_config['select_dropdown_tool']['name'],
                description=self.tools_config['select_dropdown_tool']['description'],
                page=self.page
            )

            self.scroll_page_tool = ScrollPageTool(
                name=self.tools_config['scroll_page_tool']['name'],
                description=self.tools_config['scroll_page_tool']['description'],
                page=self.page
            )
            self.double_click_tool = DoubleClickTool(
                name=self.tools_config['double_click_tool']['name'],
                description=self.tools_config['double_click_tool']['description'],
                page=self.page
            )
            self.text_delete_tool = TextDeleteTool(
                name=self.tools_config['text_delete_tool']['name'],
                description=self.tools_config['text_delete_tool']['description'],
                page=self.page
            )
            self.text_input_tool = TextInputTool(
                name=self.tools_config['text_input_tool']['name'],
                description=self.tools_config['text_input_tool']['description'],
                page=self.page
            )

            # self.check_uncheck_tool = PlaywrightCheckboxTool(
            #     name=self.tools_config['check_uncheck_tool']['name'],
            #     description=self.tools_config['check_uncheck_tool']['description'],
            #     page=self.page
            # )
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.error(f"Failed to load or parse configuration: {e}")
            raise

    @agent
    def planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            tools=[],
            llm=llm,
            verbose=True,
            output_json=PlannerOutputFormat
        )

    @agent
    def executor_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["executor"],
            tools=[self.goto_page_tool,
                   self.take_screenshot_tool,
                   self.fetch_and_clean_html_tool,
                   self.hover_element_tool,
                   self.get_current_url,
                   self.go_back_tool,
                   self.reload_page_tool,self.select_dropdown_tool],
            llm=llm,
            verbose=True,
        )

    @task
    def planner_task(self) -> Task:
        if(self._planner_task is None):
            self._planner_task= Task(
            config=self.tasks_config["planner_task"],
            agent=self.planner_agent(),
            output_json=PlannerOutputFormat,
        )
        return self._planner_task #if not new return ongoing one it will have earlier idea
    
    @task
    def execution_task(self) -> Task:
        if(self._executor_task is None):
            self._executor_task=Task(
            config=self.tasks_config["execution_task"],
            agent=self.executor_agent(),
            context=[self.planner_task()],
            output_json=ExecutorOutputFormat,
        )
        return self._executor_task
    
    @crew
    def crew(self) -> Crew:

        if(self.crew_instance is None):
            self.crew_instance= Crew(
         
            agents=self.agents, 
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=False #chromadb needs openai api key to work so not useful
        )
            return self.crew_instance
    
    # There is a issue over here in the fact that every time a its a new crew that is called memory remians only with one crew so this can create a problem
    #And the same issue exists with task as well if we cache just the same crew still the task creation is new very time
    #We want purana task only but with new context
    def run_iterative_planner_executor(self,user_request,max_iterations=2):
        """It will run Planner and Executor iteratively"""

        for iteration in range(max_iterations):
            logger.info(f"Starting iteration {iteration+1}")

 
            kickoff_inputs={
                "user_request":user_request,
                "agents_list":["executor_agent"],
                "execution_feedback":self.execution_history[-1] if self.execution_history else None,
                "progress_state":f"Iteration {iteration+1},completed {len(self.execution_history)} tasks",
                "iteration":iteration+1,
            }

            try:
                print("---------------------Execution History-------------------------")
                print(self.execution_history)
                result=self.crew().kickoff(inputs=kickoff_inputs)
                print(self.planner_task().output)
                print("------------------------------RESULT-----------------------------------------")
                print(result)
                print("------------------------------RESULT PRINED-----------------------------------------")
            except Exception as e:
                logger.error(f"Error in iteration {iteration+1}: {e}")
                continue
            try:
                json_result = result.model_dump_json()
                # print(type(json_result))
                if isinstance(json_result, str):
                    json_result = json.loads(json_result)
                final_result = json_result["json_dict"]
                self.execution_history.append(final_result)
                # print(type(final_result))
                print(final_result)
            except Exception as e:
                logger.error(f"Error converting result to JSON: {e}")
                continue

            # TODO : Need to think how it needs to end
            # if(self.is_task_complete(executor_output.json_dict,user_request)):
            #     logger.info(f"Task Completed SuccessFully after {iteration+1} iterations")
            #     break
                
    # def is_task_complete(self,execution_output,user_request):
    #     if execution_output.get("status") == 'SUCCESS':
    #         # Check if this is truly the final task completion
    #         result_summary = execution_output.get('result_summary', '').lower()
    #         next_step_context = execution_output.get('next_step_context', '').lower()
            
    #         # More robust completion detection
    #         completion_indicators = ['completed', 'finished', 'done', 'successful', 'final']
    #         no_next_steps = any(phrase in next_step_context for phrase in ['no further', 'complete', 'finished'])
            
    #         if (any(indicator in result_summary for indicator in completion_indicators) or no_next_steps):
    #             return True
    #         return False