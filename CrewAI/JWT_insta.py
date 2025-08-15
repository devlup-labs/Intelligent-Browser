from playwright.sync_api import sync_playwright

USERNAME = "wigg.213"
PASSWORD = "wiggly"

def login_and_get_sessionid():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Go to Instagram login page
        page.goto("https://www.instagram.com/accounts/login/")
        page.wait_for_selector("input[name='username']")

        # Fill login form
        page.fill("input[name='username']", USERNAME)
        page.fill("input[name='password']", PASSWORD)
        page.click("button[type='submit']")

        # Wait for login to complete
        try:
            page.wait_for_selector("svg[aria-label='Home']", timeout=15000)
            print("✅ Logged in successfully!")
        except:
            print("❌ Login failed or took too long.")
            browser.close()
            return

        # Get session cookies
        cookies = context.cookies()
        sessionid = None
        for cookie in cookies:
            if cookie["name"] == "sessionid":
                sessionid = cookie["value"]
                break

        if sessionid:
            print("✅ Your Instagram session token (sessionid):")
            print(sessionid)
        else:
            print("⚠ No sessionid cookie found.")

        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    login_and_get_sessionid()
