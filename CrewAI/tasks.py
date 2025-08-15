# tasks.py
from crewai import Task
from agent import super_login_agent
from CrewAI.sample.enhancedtools import SmartLoginTool, SelectorExtractorTool, PlaywrightLoginTool



# ============================================================
# TASK: Selector Extraction from Parsed HTML
# ============================================================
selector_extraction_task = Task(
    description=(
        "Analyze the provided cleaned/parsed HTML snippet of a website's login page "
        "to accurately determine the CSS selectors required for automating the login process. "
        "Focus on identifying the username (or email) input field, the password input field, "
        "and the login/submit button. Use regex-based pattern matching to detect these selectors "
        "reliably even in varied naming conventions, such as 'email', 'user', 'login', "
        "'password', 'pass', 'submit', or 'sign-in'. "
        "These selectors will be used directly in Playwright scripts to perform automated login."
    ),
    expected_output=(
        "A dictionary containing exactly three keys: "
        "`username_selector`, `password_selector`, and `submit_selector`. "
        "Each value should be a valid CSS selector string ready for Playwright usage. "
        "If any selector is not found, provide a reasonable default, such as 'text=Login' "
        "for the submit button."
    ),
    tools=[SelectorExtractorTool()],
    agent=super_login_agent
)

smart_login_task = Task(
    description=(
        "Execute the full intelligent login process for the given target website. "
        "Begin by checking if a stored JSON Web Token (JWT) exists for the site. "
        "If the token is found and is still valid (not expired), inject it into the "
        "browser's localStorage to instantly log in without any manual steps. "
        "If no valid JWT exists, fall back to stored username/password credentials "
        "and attempt an automated login. If credentials are available, use parsing tools "
        "to locate the correct login form selectors from the provided HTML, "
        "and then use Playwright to perform the login seamlessly in the same browser context. "
        "If no credentials are found in storage, prompt the user for them interactively. "
        "Once a successful login is achieved, extract a fresh JWT from the browser "
        "and store it along with its expiry time for future use. "
        "This ensures minimal user intervention in future sessions."
    ),
    expected_output=(
        "A detailed result message indicating the login outcome. "
        "This should specify whether the login succeeded using a stored JWT, "
        "stored credentials, or user-supplied credentials. "
        "If a new JWT is obtained, confirm that it was stored with its expiry time. "
        "In case of failure, provide an informative reason for troubleshooting."
    ),
    tools=[SmartLoginTool()],
    agent=super_login_agent
)
# ============================================================
# TASK: Automated Login with Playwright
# ============================================================

# playwright_login_task = Task(
#     description=(
#         "Perform a browser-based login using Playwright automation. "
#         "Navigate to the target website's login page in the same browser context "
#         "that may have been prepared earlier in the workflow. "
#         "Fill in the provided username and password fields using the provided CSS selectors, "
#         "then click the submit/login button. "
#         "Wait for the login process to complete and verify success by checking "
#         "that the expected post-login page or authentication state is reached. "
#         "This task assumes that correct credentials and selectors have already been supplied."
#     ),
#     expected_output=(
#         "A string message confirming whether the Playwright login attempt was successful or failed. "
#         "If successful, indicate that the session is now authenticated. "
#         "If failed, specify whether it was due to incorrect credentials, "
#         "invalid selectors, network issues, or other browser automation errors."
#     ),
#     tools=[PlaywrightLoginTool()],
#     agent=super_login_agent
# )
