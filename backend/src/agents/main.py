import asyncio 
from crew import PlannerCrew
import json
from examples.planner_agent_example import planner_examples_list
from utils.browser_manager import BrowserManager

async def run(): 
    user_request = input("Ask me anything!! ---> ")
    agent_list = ["Chat", "Browser", "Computer", "File"]
    example_list_json = json.dumps(planner_examples_list, indent=2)

    inputs = {
        "user_request": user_request,
        "agents_list": agent_list,
        "examples_list": example_list_json,
    }

    browser_manager = BrowserManager()
    
    try:
        page = await browser_manager.start()

        my_crew = PlannerCrew(page=page)
        
        result = my_crew.crew().kickoff(inputs=inputs)
        
        print("\n\n########################")
        print("## Here is the result")
        print("########################\n")
        print(result)
    finally:
        print("Closing browser...")
        await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(run())