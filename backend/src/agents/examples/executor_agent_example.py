import json

executor_examples_list = [
    {
        "task_description": "Use the 'Navigate To URL' tool to go to the page 'https://www.google.com'.",
        "tool_call_result": "Successfully navigated to https://www.google.com. The page content is now available.",
        "OutputResult": json.dumps({
            "status": "SUCCESS",
            "step_description": "Navigate to 'https://www.google.com'",
            "result_summary": "Successfully navigated to https://www.google.com.",
            "error_details": None,
            "suggestions_for_planner": None,
            "outputs_created": [],
            "next_step_context": "The current page is now google.com."
        }, indent=4)
    },
    {
        "task_description": "Use the 'Navigate To URL' tool to go to the page 'https://non-existent-url-123.com'.",
        "tool_call_result": "Navigation failed due to browser error: net::ERR_NAME_NOT_RESOLVED",
        "OutputResult": json.dumps({
            "status": "FAILURE",
            "step_description": "Navigate to 'https://non-existent-url-123.com'",
            "result_summary": "Failed to navigate to the URL because the domain name could not be found.",
            "error_details": "The browser returned the error 'net::ERR_NAME_NOT_RESOLVED', which means the URL does not exist or is unreachable.",
            "suggestions_for_planner": "Please verify the URL is correct and reachable. If it is, perhaps there is a network issue. Suggest trying a different, known-working URL as a test.",
            "outputs_created": [],
            "next_step_context": "Navigation failed, the browser remains on the previous page."
        }, indent=4)
    }
]