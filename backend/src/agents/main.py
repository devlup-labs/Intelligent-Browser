import asyncio
from crew import MasterCrew
import json
from examples.executor_agent_example import executor_examples_list
from utils.browser_manager import BrowserManager
import nest_asyncio

nest_asyncio.apply()

async def run():
    user_request = input("Ask me anything!! ---> ")
    agent_list = ["executor_agent"]
    
    executor_examples_json = json.dumps(executor_examples_list, indent=2)

    inputs = {
        "user_request": user_request,
        "agents_list": agent_list,
        "executor_examples": executor_examples_json, 
    }

    browser_manager = BrowserManager()
    
    try:
        page = await browser_manager.start()
        my_crew = MasterCrew(page=page)
        
        my_crew.run(inputs=inputs)
        
    finally:
        print("Closing browser...")
        await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(run())