from crewai import Crew, Agent, Process, Task, LLM
import os
import yaml
import json
import logging
from tools.browser_tools import GoToPageTool,FetchAndCleanHTMLTool
from utils.browser_manager import BrowserManager
from playwright.async_api import Page
from crewai.project import CrewBase, agent, crew, task
from models.outputs import ExecutionOutput, PlannerOutput, CurrentTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY environment variable is not set")

try:
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

    def __init__(self, page: Page):
        self.page = page
        self.execution_history = []
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
            output_pydantic=PlannerOutput 
        )

    @task
    def execution_task(self) -> Task:
        return Task(
            config=self.tasks_config["execution_task"],
            agent=self.executor_agent(),
            context=[self.planner_task()],
            output_pydantic=ExecutionOutput
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=False
        )

    def run(self, inputs, max_iterations=5):

        progress_state = "Not started."
        execution_feedback = "No feedback yet. This is the first step."

        for i in range(max_iterations):
            logger.info(f"\n{'='*20} Starting Iteration {i+1} {'='*20}")

            iteration_inputs = inputs.copy()
            iteration_inputs['execution_feedback'] = json.dumps(execution_feedback, indent=2)
            iteration_inputs['progress_state'] = progress_state

            result = self.crew().kickoff(inputs=iteration_inputs)
            
            last_task_output = result.tasks_output[-1]
            raw_output = last_task_output.raw
            
            try:
                if '```json' in raw_output:
                    raw_output = raw_output.split('```json')[1].split('```')[0].strip()
                
                parsed_output = json.loads(raw_output)
                executor_output = ExecutionOutput(**parsed_output)

            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse executor's raw output. Error: {e}")
                print("Raw output was:", raw_output)
                break
            
            if not executor_output:
                logger.error("Executor did not return valid structured output. Stopping.")
                break

            self.execution_history.append(executor_output)
            logger.info(f"Iteration {i+1} Result: {executor_output.status} - {executor_output.result_summary}")

            execution_feedback = executor_output.model_dump()
            progress_state += f"\n- Step {i+1} ({executor_output.status}): {executor_output.result_summary}"

            if executor_output.status == 'SUCCESS':
                summary = executor_output.result_summary.lower()
                if "successfully navigated" in summary or "task complete" in summary:
                    logger.info("✅ Task seems complete based on executor's summary.")
                    print("\n\n✅ FINAL RESULT:", summary)
                    break
        else:
            logger.warning(f"⚠️ Max iterations ({max_iterations}) reached. Stopping.")
