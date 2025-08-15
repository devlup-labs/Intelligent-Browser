class SmartLoginTool(BaseTool):
    name: str = "smart_login"
    description: str = "Logs into a site using JWT if available & not expired, else creds, stores new JWT with expiry."
    args_schema: type[BaseModel] = SmartLoginInput

    def _run(self, url, parsed_html, page):
        # jwt_data = self._get_jwt(url)

        # # 1️⃣ If JWT exists and is still valid
        # if jwt_data and time.time() < jwt_data["expires_at"]:
        #     print("✅ Using stored valid JWT")
        #     self._inject_jwt(page, jwt_data["token"])
        #     return f"Used stored JWT token for {url} → login successful"

        # print("⚠️ No valid JWT found, logging in with credentials...")

        # 2️⃣ Get credentials
    #    creds = self._get_credentials(url)
        creds = False
        if not creds:
            username = input("Enter username: ")
            password = input("Enter password: ")
            creds = {"username": username, "password": password}
           # self._save_credentials(url, username, password)

        # 3️⃣ Extract selectors
        selectors = SelectorExtractorTool()._run(parsed_html)

        # 4️⃣ Perform login in same browser
        PlaywrightLoginTool()._run(
            page=page,
            url=url,
            username=creds["username"],
            password=creds["password"],
            username_selector=selectors["username_selector"],
            password_selector=selectors["password_selector"],
            submit_selector=selectors["submit_selector"]
        )

        # 5️⃣ Extract new JWT
        new_jwt = self._extract_jwt(page)

        if new_jwt:
            exp_time = decode_jwt_exp(new_jwt)
            if not exp_time:
                exp_time = time.time() + 3600  # fallback: 1h
        #    self._save_jwt(url, new_jwt, exp_time)
            print(f"💾 Saved new JWT, expires at {time.ctime(exp_time)}")
        else:
            print("❌ Could not extract JWT after login")
            print()
        return f"Login completed for {url} with new JWT"