from flask import Flask, request, jsonify
from atlassian import Jira
import json
import os
from config import JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, validate_config

app = Flask(__name__)

# Initialize Jira client
def get_jira_client():
    validate_config()
    return Jira(
        url=JIRA_URL,
        username=JIRA_USERNAME,
        password=JIRA_API_TOKEN,
        cloud=True
    )

@app.route("/")
def home():
    return f"""
    <h1>Jira MCP Server</h1>
    <p><strong>Status:</strong> ✅ Connected to {JIRA_URL}</p>
    <p><strong>User:</strong> {JIRA_USERNAME}</p>
    
    <h2>Available Endpoints:</h2>
    <ul>
        <li><strong>GET</strong> <code>/projects</code> - List all projects</li>
        <li><strong>GET</strong> <code>/issues?jql=&lt;query&gt;</code> - Search issues</li>
        <li><strong>POST</strong> <code>/create-issue</code> - Create new issue</li>
        <li><strong>GET</strong> <code>/issue/&lt;key&gt;</code> - Get specific issue</li>
        <li><strong>POST</strong> <code>/api/mcp</code> - MCP endpoint</li>
    </ul>
    
    <h2>Test Connection:</h2>
    <a href="/projects">View Projects</a>
    """

@app.route("/projects")
def get_projects():
    try:
        jira = get_jira_client()
        projects = jira.projects()
        return jsonify({
            "success": True,
            "projects": projects
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/issues")
def search_issues():
    jql = request.args.get("jql", "project IS NOT EMPTY ORDER BY created DESC")
    max_results = int(request.args.get("max_results", 50))
    
    try:
        jira = get_jira_client()
        results = jira.jql(jql, limit=max_results)
        return jsonify({
            "success": True,
            "jql": jql,
            "total": results.get("total", 0),
            "issues": results.get("issues", [])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/issue/<issue_key>")
def get_issue(issue_key):
    try:
        jira = get_jira_client()
        issue = jira.issue(issue_key)
        return jsonify({
            "success": True,
            "issue": issue
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/create-issue", methods=["POST"])
def create_issue():
    try:
        jira = get_jira_client()
        data = request.json
        
        # Example issue data structure
        issue_data = {
            "summary": data.get("summary", "Issue created via API"),
            "description": data.get("description", ""),
            "issuetype": {"name": data.get("issue_type", "Task")},
            "project": {"key": data.get("project_key")}
        }
        
        if data.get("assignee"):
            issue_data["assignee"] = {"name": data["assignee"]}
            
        if data.get("priority"):
            issue_data["priority"] = {"name": data["priority"]}
        
        new_issue = jira.issue_create(fields=issue_data)
        return jsonify({
            "success": True,
            "issue": new_issue
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/mcp", methods=["POST"])
def mcp_entry():
    """
    MCP (Model Context Protocol) style endpoint for handling various Jira operations
    """
    try:
        data = request.json
        action = data.get("action")
        params = data.get("params", {})
        
        jira = get_jira_client()
        
        if action == "list_projects":
            result = jira.projects()
        elif action == "search_issues":
            jql = params.get("jql", "project IS NOT EMPTY")
            result = jira.jql(jql, limit=params.get("limit", 50))
        elif action == "get_issue":
            issue_key = params.get("key")
            result = jira.issue(issue_key)
        elif action == "create_issue":
            result = jira.issue_create(fields=params.get("fields"))
        elif action == "update_issue":
            issue_key = params.get("key")
            fields = params.get("fields")
            result = jira.issue_update(issue_key, fields=fields)
        else:
            return jsonify({
                "success": False,
                "error": f"Unknown action: {action}"
            }), 400
            
        return jsonify({
            "success": True,
            "action": action,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/health")
def health_check():
    try:
        jira = get_jira_client()
        # Simple test to verify connection
        jira.projects()
        return jsonify({
            "status": "healthy",
            "jira_url": JIRA_URL,
            "username": JIRA_USERNAME
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)