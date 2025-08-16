from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from playwright.async_api import Page, Error as PlaywrightError
from bs4 import BeautifulSoup, NavigableString, Comment
import requests
import re
from typing import Dict, List, Optional



class GetElementPositionSchema(BaseModel):
    task: str = Field(..., description="The task to perform, e.g., 'get position of element with selector #my-element'")
    image_path: str = Field(..., description="Path to the image file where the element is stored")


class GetElementPositionTool(BaseTool):
    name: str = "get_element_position"
    description: str = "Uploads an image and task to the backend FastAPI server to get element position."
    args_schema: type[BaseModel] = GetElementPositionSchema

    async def _run(self, task: str, image_path: str) -> str:
        url = "http://10.36.16.15:8000/process-image/"   # FastAPI backend endpoint

        try:
            # Open the image file safely
            with open(image_path, "rb") as image_file:
                files = {
                    "file": (image_path.split("/")[-1], image_file, "image/jpeg")
                }
                data = {
                    "task": task,
                    "history": ""   # Add actual history if needed
                }

                # Send POST request to backend
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()

                # Parse JSON response
                if response.headers.get("Content-Type", "").startswith("application/json"):
                    return response.json().get("action_code", "No action_code in response")
                else:
                    return response.text

        except FileNotFoundError:
            return f"Image file not found: {image_path}"
        except requests.exceptions.RequestException as e:
            return f"Request error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

if __name__ == "__main__":
    tool = GetElementPositionTool()

    result = tool._run(
        task="Go to search bar in Google Chrome then search for walmart.",
        image_path="/home/vichitrarora/intelli2/Intelligent-Browser/backend/image.png"
    )

    # since _run is async, you must run it properly
    import asyncio
    print(asyncio.run(result))
