planner_examples_list = [
    {
        "user_request": "go to google.com",
        "OutputResult": {
            "session_type": "INITIAL_PLANNING",
            "overall_task_name": "Navigate to Google",
            "master_thought": "The user wants to navigate to a specific URL, 'google.com'. This is a direct, single-step action that can be performed by the executor agent using its browser navigation tool. I will create one task for the executor to go to the specified page.",
            "estimated_steps": "1",
            "current_task": {
                "task_name": "Go to Google Homepage",
                "task_id": 1,
                "agent_name": "executor_agent",
                "task_thought": "The first and only step is to use the navigation tool to open the requested URL. The executor has the 'Navigate To URL' tool for this purpose.",
                "task_description": "Use the 'Navigate To URL' tool to go to the page 'https://www.google.com'.",
                "subtasks": [
                    "Call the 'Navigate To URL' tool.",
                    "Provide 'https://www.google.com' as the url parameter."
                ],
                "expected_outputs": "Confirmation that the browser has successfully navigated to google.com."
            }
        }
    }
]