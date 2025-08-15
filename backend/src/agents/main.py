import asyncio
from src.agents.crew import MasterCrew
from src.agents.utils.browser_manager import BrowserManager
from src.schema import schema
import nest_asyncio

nest_asyncio.apply()

async def run(chatRequest:schema.ChatInput):
    # user_request = input("Ask me anything!! ---> ")

    user_request=chatRequest.user_request
    agent_list = ["planner_agent", "executor_agent"]
    
    inputs = {
        "user_request": user_request,
        "agents_list": agent_list,
    }

    browser_manager = BrowserManager()
    
    try:
        page = await browser_manager.start()
        my_crew = MasterCrew(PAGE=page)
        
        result=my_crew.run_iterative_planner_executor(
            user_request=inputs["user_request"])
        return  result
        
    finally:
        print("Closing browser...")
        await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(run())