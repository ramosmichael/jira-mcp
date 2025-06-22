import os

# Jira API Token Configuration
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME") 
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Validate required environment variables
def validate_config():
    if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]):
        missing = []
        if not JIRA_URL: missing.append("JIRA_URL")
        if not JIRA_USERNAME: missing.append("JIRA_USERNAME") 
        if not JIRA_API_TOKEN: missing.append("JIRA_API_TOKEN")
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return True