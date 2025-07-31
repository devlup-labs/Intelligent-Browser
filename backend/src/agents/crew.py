from crewai import Crew, Agent, Process, Task, LLM
import os
from crewai.project import CrewBase, agent, tool, crew, task
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(os.getenv("GEMINI_API_KEY"))
try:
    # Use CrewAI's native LLM class instead of LangChain
    llm = LLM(
        model="gemini/gemini-2.5-pro",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.7
    )
    print("CrewAI LLM initialized successfully")
except Exception as e:
    print(f"LLM initialization failed: {e}")
    raise

# Declares a full crewai project and collects and links @agent, @task, @crew
# Without this manually sab crew ko batana padega
# 📦 Under the hood, it probably collects all decorated methods and makes them accessible as .agents, .tasks, and .crew().
@CrewBase
class PlannerCrew:
    """Planner Crew"""

    def __init__(self):
        # Load YAML files into dictionaries
        with open("config/agents.yaml", 'r') as file:
            self.agents_config = yaml.safe_load(file)
        
        with open("config/tasks.yaml", 'r') as file:
            self.tasks_config = yaml.safe_load(file)
    print(self.agents_config)
    print(self.tasks_config)

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
            tools=[],
            llm=llm,
            verbose=True,
        )
    
    @task
    def planner_task(self) -> Task:
        return Task(
            config=self.tasks_config["planner_task"],
            agents=self.planner_agent()
        )
    
    @task
    def execution_task(self) -> Task:
        return Task(
            config=self.tasks_config["execution_task"],
            agents=self.executor_agent(),
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



    