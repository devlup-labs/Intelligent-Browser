import asyncio
from crew import MasterCrew
import json
from examples.executor_agent_example import executor_examples_list
from utils.browser_manager import BrowserManager
import nest_asyncio

nest_asyncio.apply()

async def run():
    user_request = input("Ask me anything!! ---> ")
    agent_list = ["planner_agent", "executor_agent"]
    
    inputs = {
        "user_request": user_request,
        "agents_list": agent_list,
    }

    browser_manager = BrowserManager()
    
    try:
        page = await browser_manager.start()
        my_crew = MasterCrew(PAGE=page)
        
        my_crew.run_iterative_planner_executor(
            user_request=inputs["user_request"])
        
    finally:
        print("Closing browser...")
        await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(run())