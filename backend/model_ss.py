


async def ss_run(self, task: str, image_path: str) -> str:
    url = "http://10.36.16.15:8080/process-image/"   # FastAPI backend endpoint

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
