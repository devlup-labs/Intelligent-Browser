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
class PlannerCrew:
    """Planner Crew"""

    def __init__(self, page: Page):
        # Load YAML files into dictionaries
        self.browser_manager = BrowserManager()
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "config")
            with open(os.path.join(config_dir, "agents.yaml"), 'r') as file:
                self.agents_config = yaml.safe_load(file)
            
            with open(os.path.join(config_dir, "tasks.yaml"), 'r') as file:
                self.tasks_config = yaml.safe_load(file)

            with open("config/tools.yaml", 'r') as file:
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

    #this is actual agent name not the one used in agents that is just for reference
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
            agent=self.planner_agent()
        )
    
    @task
    def execution_task(self) -> Task:
        return Task(
            config=self.tasks_config["execution_task"],
            agent=self.executor_agent(),
            # This makes the executor wait for the planner's output
            context=[self.planner_task()]  
        )
    
    @crew
    def crew(self) -> Crew:
        # print("helloL",self.agents)
        return Crew(
            # self.agents / self.tasks automatically created when decorators are used
            agents=self.agents, 
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
