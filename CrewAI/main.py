# main.py
from crewai import Crew
from tasks import smart_login_task, selector_extraction_task
from agent import smart_login_agent
import os
from dotenv import load_dotenv

load_dotenv()


gemini_key = os.getenv("GEMINI_API_KEY")

os.environ["LLM_PROVIDER"] = "gemini"
os.environ["GEMINI_API_KEY"] = gemini_key
   
crew = Crew(
    agents=[smart_login_agent],
    tasks=[smart_login_task, selector_extraction_task],
    verbose=True
)

if __name__ == "__main__":
    parsed_html = '<input id="username"><input id="password"><button id="login">'
    result = crew.kickoff(inputs={
        "url": "https://example.com",
        "parsed_html": parsed_html
    })
    print(result)
