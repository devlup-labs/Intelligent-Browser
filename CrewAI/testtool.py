from tools import SmartLoginTool
from playwright.sync_api import sync_playwright

parsed_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Cleaned for LLM</title>
</head>
<body>
<a x="85" y="8" w="78" h="40" href="#/">conduit</a>
<a x="1025" y="8" w="42" h="38" href="#/">Home</a>
<a x="1083" y="8" w="46" h="38" href="#/login">Sign in</a>
<a x="1145" y="8" w="50" h="38" href="#/register">Sign up</a>
<h1>Sign in</h1>
<a x="580" y="134" w="120" h="20" href="#/register">Need an account?</a>
<input x="370" y="172" w="540" h="51" type="email" placeholder="Email"/>
<input x="370" y="239" w="540" h="51" type="password" placeholder="Password"/>
<button x="805" y="306" w="105" h="51" type="submit">Sign in</button>
<a x="85" y="680" w="53" h="24" href="#/">conduit</a>
<p>© 2025.
      An interactive learning project from</p>
<a x="375" y="683" w="48" h="16" href="https://thinkster.io">Thinkster</a>
<p>.
      Code licensed under MIT.</p>
<a x="0" y="654" w="1280" h="66" href="https://github.com/gothinkster/angularjs-realworld-example-app">Fork on GitHub</a>
</body>
</html>
"""

url = "https://conduit-realworld-example-app.fly.dev/#/login"

tool = SmartLoginTool()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Set headless=True if you don’t want to see it
    page = browser.new_page()
    

    print(tool._run(url=url, parsed_html=parsed_html,page= page))
    
    # Keep browser open after run so you can inspect it
    input("Press Enter to close browser...")
   # browser.close()
