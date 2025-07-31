planner_examples_list=[
        {
            "user_request": "hello.",
            "OutputResult": {
                "root": {
                    "name": "Chat",
                    "thought": "Alright, the user wrote \"hello\". That's pretty straightforward. I need to respond in a friendly and welcoming manner.",
                    "agents": [
                        {
                            "name": "Chat",
                            "id": 0,
                            "dependsOn": ""
                        }
                    ]
                }
            }
        },
        {
            "user_request": "Open Boss Zhipin, find 10 operation positions in Chengdu, and send a personal introduction to the recruiters based on the page information.",
            "OutputResult": {
                "root": {
                    "name": "Submit resume",
                    "thought": "OK, now the user requests me to create a workflow that involves opening the Boss Zhipin website, finding 10 operation positions in Chengdu, and sending personal resumes to the recruiters based on the job information.",
                    "agents": [
                        {
                            "name": "Browser",
                            "id": 0,
                            "dependsOn": "",
                            "task": "Open Boss Zhipin, find 10 operation positions in Chengdu, and send a personal introduction to the recruiters based on the page information.",
                            "nodes": [
                                "Open Boss Zhipin, enter the job search page",
                                "Set the regional filter to Chengdu and search for operational positions.",
                                "Brows the job list and filter out 10 suitable operation positions.",
                                {
                                    "forEach": "list",
                                    "steps": [
                                        "Analyze job requirements",
                                        "Send a self-introduction to the recruiter"
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        },
        {
            "user_request": "Help me collect the latest AI news, summarize it, and send it to the \"AI news information\" group chat on WeChat.",
            "OutputResult": {
                "root": {
                    "name": "Latest AI News",
                    "thought": "OK, users need to collect the latest AI news, summarize it, and send it to a WeChat group named \"AI news information\" This requires automation, including the steps of data collection, processing, and distribution.",
                    "agents": [
                        {
                            "name": "Browser",
                            "id": 0,
                            "dependsOn": "",
                            "task": "Search for the latest updates on AI",
                            "nodes": [
                                "Open Google",
                                "Search for the latest updates on AI",
                                {
                                    "forEach": "list",
                                    "steps": [
                                        "View Details"
                                    ]
                                },
                                {
                                    "output": "summaryInfo",
                                    "description": "Summarize search information"
                                }
                            ]
                        },
                        {
                            "name": "Computer",
                            "id": 1,
                            "dependsOn": "0",
                            "task": "Send a message to the WeChat group chat \"AI news information\"",
                            "nodes": [
                                "Open WeChat",
                                "Search for the \"AI news information\" chat group",
                                {
                                    "input": "summaryInfo",
                                    "description": "Send summary message"
                                }
                            ]
                        }
                    ]
                }
            }
        },
        {
            "user_request": "Access the Google team's organization page on GitHub, extract all developer accounts from the team, and compile statistics on the countries and regions where these developers are located.",
            "OutputResult": {
                "root": {
                    "name": "Statistics of Google Team Developers' Geographic Distribution",
                    "thought": "Okay, I need to first visit GitHub, then find Google's organization page on GitHub, extract the team member list, and individually visit each developer's homepage to obtain location information for each developer. This requires using a browser to complete all operations.",
                    "agents": [
                        {
                            "name": "Browser",
                            "id": 0,
                            "dependsOn": "",
                            "task": "Visit Google GitHub Organization Page and Analyze Developer Geographic Distribution",
                            "nodes": [
                                "Visit https://github.com/google",
                                "Click \"People\" tab to view team members",
                                "Scroll the page to load all developer information",
                                {
                                    "output": "developers",
                                    "description": "Extract all developer account information"
                                },
                                {
                                    "forEach": "developers",
                                    "steps": [
                                        "Visit developer's homepage",
                                        "Extract developer's location information"
                                    ]
                                },
                                "Compile and analyze the geographic distribution data of all developers"
                            ]
                        }
                    ]
                }
            }
        },
        {
            "user_request": "Search for information about \"fellou,\" compile the results into a summary profile, then share it across social media platforms including Twitter, Facebook, and Reddit. Finally, export the platform sharing operation results to an Excel file.",
            "OutputResult": {
                "root": {
                    "name": "Fellou Research and Social Media Campaign",
                    "thought": "The user wants me to research information about 'Fellou', create a summary profile, share it on multiple social media platforms (Twitter, Facebook, Reddit), and then compile the results into an Excel file. This requires multiple agents working together: Browser for research, Browser for social media posting (Twitter, Facebook, and Reddit in parallel), and File for creating the Excel export. I need to break this down into sequential steps with proper variable passing between agents.",
                    "agents": [
                        {
                            "name": "Browser",
                            "id": 0,
                            "dependsOn": "",
                            "task": "Research comprehensive information about 'Fellou'",
                            "nodes": [
                                "Search for the latest information about 'Fellou' - its identity, purpose, and core features",
                                "Search for Fellou's functionalities, capabilities, and technical specifications",
                                "Search for recent news, updates, announcements, and developments related to Fellou",
                                "Search for user reviews, feedback, and community discussions about Fellou",
                                "Search for Fellou's market position, competitors, and industry context",
                                {
                                    "output": "researchData",
                                    "description": "Compile all research findings into a comprehensive summary profile"
                                }
                            ]
                        },
                        {
                            "name": "Browser",
                            "id": 1,
                            "dependsOn": "0",
                            "task": "Share Fellou's summary and collected interaction data on Twitter/X",
                            "nodes": [
                                "Navigate to Twitter/X platform",
                                {
                                    "input": "researchData",
                                    "description": "Create and post Twitter-optimized content about Fellou (within character limits, using hashtags)"
                                },
                                {
                                    "output": "twitterResults",
                                    "description": "Capture Twitter post URL and initial engagement metrics"
                                }
                            ]
                        },
                        {
                            "name": "Browser",
                            "id": 2,
                            "dependsOn": "0",
                            "task": "Share Fellou's summary and collected interaction data on Facebook",
                            "nodes": [
                                "Navigate to Facebook platform",
                                {
                                    "input": "researchData",
                                    "description": "Create and post Facebook-optimized content about Fellou (longer format, engaging description)"
                                },
                                {
                                    "output": "facebookResults",
                                    "description": "Capture Facebook post URL and initial engagement metrics"
                                }
                            ]
                        },
                        {
                            "name": "Browser",
                            "id": 3,
                            "dependsOn": "0",
                            "task": "Share Fellou's summary and collected interaction data on Reddit",
                            "nodes": [
                                "Navigate to Reddit platform",
                                {
                                    "input": "researchData",
                                    "description": "Find appropriate subreddit and create Reddit-optimized post about Fellou (community-focused, informative)"
                                },
                                {
                                    "output": "redditResults",
                                    "description": "Capture Reddit post URL and initial engagement metrics"
                                }
                            ]
                        },
                        {
                            "name": "File",
                            "id": 4,
                            "dependsOn": "1,2,3",
                            "task": "Compile social media results into Excel file",
                            "nodes": [
                                {
                                    "input": "twitterResults,facebookResults,redditResults",
                                    "description": "Create Excel file with social media campaign results"
                                },
                                "Include columns for Platform, Post URL, Content Summary, Timestamp, Initial Likes/Shares/Comments",
                                "Format the Excel file with proper headers and styling",
                                "Save the file as 'Fellou_Social_Media_Campaign_Results.xlsx'"
                            ]
                        }
                    ]
                }
            }
        }
    ]

