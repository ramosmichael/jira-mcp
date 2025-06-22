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
    
    <h2>MCP Tools Available:</h2>
    <ul>
        <li><code>list_jira_projects</code> - List all Jira projects</li>
        <li><code>search_jira_issues</code> - Search Jira issues with JQL</li>
        <li><code>get_jira_issue</code> - Get specific Jira issue details</li>
        <li><code>create_jira_issue</code> - Create new Jira issue</li>
    </ul>
    
    <h2>Test Connection:</h2>
    <a href="/projects">View Projects</a>
    """

# MCP Protocol Implementation
@app.route("/api/mcp", methods=["POST", "GET"])
def mcp_endpoint():
    """
    MCP (Model Context Protocol) compliant endpoint
    """
    if request.method == "GET":
        # Return tool definitions for MCP discovery
        return jsonify({
            "tools": [
                {
                    "name": "list_jira_projects",
                    "description": "List all available Jira projects",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "search_jira_issues", 
                    "description": "Search Jira issues using JQL (Jira Query Language)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "jql": {
                                "type": "string",
                                "description": "JQL query string (e.g., 'project = TEST AND status = Open')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 50)",
                                "default": 50
                            }
                        },
                        "required": ["jql"]
                    }
                },
                {
                    "name": "get_jira_issue",
                    "description": "Get detailed information about a specific Jira issue",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Jira issue key (e.g., 'PROJ-123')"
                            }
                        },
                        "required": ["issue_key"]
                    }
                },
                {
                    "name": "create_jira_issue",
                    "description": "Create a new Jira issue",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key where the issue will be created"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Brief summary of the issue"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the issue"
                            },
                            "issue_type": {
                                "type": "string",
                                "description": "Type of issue (e.g., 'Task', 'Bug', 'Story')",
                                "default": "Task"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Priority level (e.g., 'High', 'Medium', 'Low')"
                            },
                            "assignee": {
                                "type": "string",
                                "description": "Username of the assignee"
                            }
                        },
                        "required": ["project_key", "summary"]
                    }
                }
            ]
        })
    
    # Handle POST requests (tool calls)
    try:
        data = request.json
        tool_name = data.get("name") or data.get("tool") or data.get("action")
        arguments = data.get("arguments") or data.get("params") or data.get("input", {})
        
        jira = get_jira_client()
        
        if tool_name == "list_jira_projects":
            result = jira.projects()
            return jsonify({
                "content": [
                    {
                        "type": "text",
                        "text": f"Found {len(result)} Jira projects:\n\n" + 
                               "\n".join([f"• {p['name']} ({p['key']})" for p in result])
                    }
                ],
                "isError": False
            })
            
        elif tool_name == "search_jira_issues":
            jql = arguments.get("jql", "project IS NOT EMPTY ORDER BY created DESC")
            max_results = arguments.get("max_results", 50)
            
            results = jira.jql(jql, limit=max_results)
            issues = results.get("issues", [])
            
            if not issues:
                return jsonify({
                    "content": [
                        {
                            "type": "text", 
                            "text": f"No issues found for JQL query: {jql}"
                        }
                    ],
                    "isError": False
                })
            
            issue_list = []
            for issue in issues:
                fields = issue.get("fields", {})
                issue_list.append(
                    f"• {issue['key']}: {fields.get('summary', 'No summary')}\n"
                    f"  Status: {fields.get('status', {}).get('name', 'Unknown')}\n"
                    f"  Assignee: {fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'}\n"
                    f"  Priority: {fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None'}"
                )
            
            return jsonify({
                "content": [
                    {
                        "type": "text",
                        "text": f"Found {len(issues)} issues (JQL: {jql}):\n\n" + "\n\n".join(issue_list)
                    }
                ],
                "isError": False
            })
            
        elif tool_name == "get_jira_issue":
            issue_key = arguments.get("issue_key")
            if not issue_key:
                return jsonify({
                    "content": [{"type": "text", "text": "Error: issue_key is required"}],
                    "isError": True
                })
            
            issue = jira.issue(issue_key)
            fields = issue.get("fields", {})
            
            # Format issue details
            details = f"""
**{issue_key}: {fields.get('summary', 'No summary')}**

**Description:** {fields.get('description', 'No description')}

**Status:** {fields.get('status', {}).get('name', 'Unknown')}
**Priority:** {fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None'}
**Issue Type:** {fields.get('issuetype', {}).get('name', 'Unknown')}
**Assignee:** {fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'}
**Reporter:** {fields.get('reporter', {}).get('displayName', 'Unknown') if fields.get('reporter') else 'Unknown'}
**Created:** {fields.get('created', 'Unknown')}
**Updated:** {fields.get('updated', 'Unknown')}
**Project:** {fields.get('project', {}).get('name', 'Unknown')} ({fields.get('project', {}).get('key', 'Unknown')})
"""
            
            return jsonify({
                "content": [
                    {
                        "type": "text",
                        "text": details
                    }
                ],
                "isError": False
            })
            
        elif tool_name == "create_jira_issue":
            project_key = arguments.get("project_key")
            summary = arguments.get("summary")
            
            if not project_key or not summary:
                return jsonify({
                    "content": [{"type": "text", "text": "Error: project_key and summary are required"}],
                    "isError": True
                })
            
            issue_data = {
                "summary": summary,
                "description": arguments.get("description", ""),
                "issuetype": {"name": arguments.get("issue_type", "Task")},
                "project": {"key": project_key}
            }
            
            if arguments.get("assignee"):
                issue_data["assignee"] = {"name": arguments["assignee"]}
                
            if arguments.get("priority"):
                issue_data["priority"] = {"name": arguments["priority"]}
            
            new_issue = jira.issue_create(fields=issue_data)
            
            return jsonify({
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully created issue: {new_issue['key']}\nSummary: {summary}\nProject: {project_key}"
                    }
                ],
                "isError": False
            })
            
        else:
            return jsonify({
                "content": [
                    {
                        "type": "text",
                        "text": f"Unknown tool: {tool_name}. Available tools: list_jira_projects, search_jira_issues, get_jira_issue, create_jira_issue"
                    }
                ],
                "isError": True
            }), 400
            
    except Exception as e:
        return jsonify({
            "content": [
                {
                    "type": "text", 
                    "text": f"Error: {str(e)}"
                }
            ],
            "isError": True
        }), 500

# Keep existing REST endpoints for backward compatibility
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