from crewai import Crew, Agent, Process, Task, LLM
import os
from crewai.project import CrewBase, agent, crew, task
import yaml
import logging
from tools.browser_tools import GoToPageTool
from utils.browser_manager import BrowserManager
from playwright.async_api import Page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate API key exists
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY environment variable is not set")


try:
    # Use CrewAI's native LLM class instead of LangChain
    llm = LLM(
        model="gemini/gemini-2.5-pro",
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
@CrewBase
class MasterCrew:
    """Planner Crew"""

    def __init__(self, page: Page):
      
        self.browser_manager = BrowserManager()
        self.execution_history=[] #track iterations

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
                page=page
            )

            logger.debug(self.agents_config)
            logger.debug(self.tasks_config)
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            self.browser_manager.close()
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise

    
    @agent
    def planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            tools=[],
            llm=llm,
            verbose=True,
        )
    
    @agent
    def executor_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["executor"],
            tools=[self.goto_page_tool],
            llm=llm,
            
            verbose=True,

        )
    
    @task
    def planner_task(self) -> Task:
        return Task(
            config=self.tasks_config["planner_task"],
            agent=self.planner_agent(),
            context={
                "execution_feedback": self.execution_history[-1] if self.execution_history else None,
                "iteration":len(self.execution_history)
            }   
        )
    
    @task
    def execution_task(self) -> Task:
        return Task(
            config=self.tasks_config["execution_task"],
            agent=self.executor_agent(),
            context=[self.planner_task()]  
        )
    
    @crew
    def crew(self) -> Crew:

        return Crew(
         
            agents=self.agents, 
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True #creates a shared memory space between agents so that they can communicate  
        )
    
    def run_iterative_planner_executor(self,user_request,max_iterations=10):
        """It will run Planner and Executor iteratively"""

        for iteration in range(max_iterations):
            logger.info(f"Starting iteration {iteration+1}")

            self.update_planner_description(user_request,iteration)

            result=self.crew().kickoff()

            executor_output=result.tasks_output[-1] #give you last task ka output which is executor one
            self.execution_history.append(executor_output.json_dict)

            # TODO : Need to think how it needs to end
            if(executor_output.json_dict.get("status")=='SUCCESS'):
                success_keywords=['completed', 'finished', 'done', 'successful']
                result_summary=executor_output.json_dict.get('result_summary','').lower()
                if any(indicator in result_summary for indicator in success_keywords):
                    logger.info(f"Task completed successfully after {iteration+1} iterations")
                    break


            

    def update_planner_description(self,user_request,iteration):
        """Update the planner description based on the no of iteration with executor feedback"""
        last_execution = self.execution_history[-1] if self.execution_history else None

        og_description=self.tasks_config["planner_task"]["description"]

        if(iteration==0):   #means first iteration
            self.tasks_config["planner_task"]["description"]=f"""
            {og_description}

            USER REQUEST: {user_request}
            This is the FIRST CALL
            """
        else:
            self.tasks_config["planner_task"]["description"]=f"""

            {og_description}
            
            USER REQUEST: {user_request}
            ITERATION: {iteration + 1}
            
            Previous execution details:
            - Status: {last_execution.get('status', 'Unknown')}
            - Result Summary: {last_execution.get('result_summary', 'No summary')}
            - Error Details: {last_execution.get('error_details', 'None')}
            - Suggestions: {last_execution.get('suggestions_for_planner', 'None')}
            - Next Step Context: {last_execution.get('next_step_context', 'None')}
            - Outputs Created: {last_execution.get('outputs_created', [])}

            """
        
