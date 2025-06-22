from flask import Flask, request, jsonify
from atlassian import Jira
import json
import os
from datetime import datetime
from config import JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, validate_config

app = Flask(__name__)

# Build info - Updated for clean deployment
BUILD_VERSION = "v1.3.0-mcp-fix"
BUILD_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    <h1>Jira MCP Server {BUILD_VERSION}</h1>
    <p><strong>Status:</strong> ✅ Connected to {JIRA_URL}</p>
    <p><strong>User:</strong> {JIRA_USERNAME}</p>
    <p><strong>Build:</strong> {BUILD_TIME}</p>
    
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

# MCP Protocol Implementation with enhanced debugging
@app.route("/api/mcp", methods=["GET", "POST", "OPTIONS"])
def mcp_endpoint():
    """
    MCP (Model Context Protocol) compliant endpoint with debug logging
    """
    # Log all requests for debugging
    print(f"[MCP DEBUG] Method: {request.method}")
    print(f"[MCP DEBUG] Headers: {dict(request.headers)}")
    print(f"[MCP DEBUG] Args: {dict(request.args)}")
    if request.method == "POST":
        print(f"[MCP DEBUG] Body: {request.get_data(as_text=True)}")
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        return response
    
    # Add CORS headers to all responses
    def add_cors_headers(response):
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        return response
    
    if request.method == "GET":
        # Check for different tool discovery patterns
        if request.args.get("action") == "list_tools" or request.args.get("method") == "tools/list":
            # Alternative tool discovery format
            tool_response = {
                "tools": [
                    {
                        "name": "jira_list_projects",
                        "description": "List all available Jira projects",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    {
                        "name": "jira_search_issues", 
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
                        "name": "jira_get_issue",
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
                        "name": "jira_create_issue",
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
                                }
                            },
                            "required": ["project_key", "summary"]
                        }
                    }
                ]
            }
        else:
            # Standard tool discovery format
            tool_response = {
                "jsonrpc": "2.0",
                "id": request.args.get("id", "1"),
                "result": {
                    "tools": [
                        {
                            "name": "jira_list_projects",
                            "description": "List all available Jira projects",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "jira_search_issues", 
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
                            "name": "jira_get_issue",
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
                            "name": "jira_create_issue",
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
                                    }
                                },
                                "required": ["project_key", "summary"]
                            }
                        }
                    ]
                }
            }
            
        print(f"[MCP DEBUG] Returning tool discovery response: {json.dumps(tool_response, indent=2)}")
        return add_cors_headers(jsonify(tool_response))
    
    # Handle POST requests (tool calls)
    try:
        data = request.json or {}
        print(f"[MCP DEBUG] Parsed JSON: {json.dumps(data, indent=2)}")
        
        # Handle different MCP formats
        tool_name = (data.get("method") or 
                    data.get("name") or 
                    data.get("tool") or 
                    data.get("action"))
        
        arguments = (data.get("params") or 
                    data.get("arguments") or 
                    data.get("input") or 
                    {})
        
        request_id = data.get("id", "1")
        
        print(f"[MCP DEBUG] Tool: {tool_name}, Args: {arguments}")
        
        jira = get_jira_client()
        
        # Handle different tool name formats
        if tool_name in ["jira_list_projects", "list_jira_projects"]:
            result = jira.projects()
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(result)} Jira projects:\n\n" + 
                                   "\n".join([f"• {p['name']} ({p['key']})" for p in result])
                        }
                    ]
                }
            }
            
        elif tool_name == "initialize":
            # MCP initialization handshake - CRITICAL for Jace.ai
            print(f"[MCP DEBUG] Handling initialize request")
            protocol_version = arguments.get("protocolVersion", "2024-11-05")
            client_info = arguments.get("clientInfo", {})
            
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "jira-mcp-server",
                        "version": BUILD_VERSION
                    }
                }
            }
            print(f"[MCP DEBUG] Initialize response: {json.dumps(response_data, indent=2)}")
            
        elif tool_name in ["tools/list", "listTools"] or request.args.get("method") == "tools/list":
            # Tools discovery for MCP - return available tools
            print(f"[MCP DEBUG] Handling tools/list request")
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "jira_list_projects",
                            "description": "List all available Jira projects from Talkable's Atlassian instance",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "jira_search_issues", 
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
                            "name": "jira_get_issue",
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
                            "name": "jira_create_issue",
                            "description": "Create a new Jira issue in Talkable's projects",
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
                                    }
                                },
                                "required": ["project_key", "summary"]
                            }
                        }
                    ]
                }
            }
            
        elif tool_name in ["jira_search_issues", "search_jira_issues"]:
            jql = arguments.get("jql", "project IS NOT EMPTY ORDER BY created DESC")
            max_results = arguments.get("max_results", 50)
            
            results = jira.jql(jql, limit=max_results)
            issues = results.get("issues", [])
            
            if not issues:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text", 
                                "text": f"No issues found for JQL query: {jql}"
                            }
                        ]
                    }
                }
            else:
                issue_list = []
                for issue in issues:
                    fields = issue.get("fields", {})
                    issue_list.append(
                        f"• {issue['key']}: {fields.get('summary', 'No summary')}\n"
                        f"  Status: {fields.get('status', {}).get('name', 'Unknown')}\n"
                        f"  Assignee: {fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'}\n"
                        f"  Priority: {fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None'}"
                    )
                
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Found {len(issues)} issues (JQL: {jql}):\n\n" + "\n\n".join(issue_list)
                            }
                        ]
                    }
                }
            
        elif tool_name in ["jira_get_issue", "get_jira_issue"]:
            issue_key = arguments.get("issue_key")
            if not issue_key:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: issue_key is required"
                    }
                }
            else:
                issue = jira.issue(issue_key)
                fields = issue.get("fields", {})
                
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
                
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": details
                            }
                        ]
                    }
                }
                
        elif tool_name in ["jira_create_issue", "create_jira_issue"]:
            project_key = arguments.get("project_key")
            summary = arguments.get("summary")
            
            if not project_key or not summary:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: project_key and summary are required"
                    }
                }
            else:
                issue_data = {
                    "summary": summary,
                    "description": arguments.get("description", ""),
                    "issuetype": {"name": arguments.get("issue_type", "Task")},
                    "project": {"key": project_key}
                }
                
                new_issue = jira.issue_create(fields=issue_data)
                
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Successfully created issue: {new_issue['key']}\nSummary: {summary}\nProject: {project_key}"
                            }
                        ]
                    }
                }
                
        else:
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {tool_name}. Available: jira_list_projects, jira_search_issues, jira_get_issue, jira_create_issue"
                }
            }
            
        print(f"[MCP DEBUG] Response: {json.dumps(response_data, indent=2)}")
        return add_cors_headers(jsonify(response_data))
            
    except Exception as e:
        print(f"[MCP DEBUG] Error: {str(e)}")
        error_response = {
            "jsonrpc": "2.0",
            "id": request.json.get("id", "1") if request.json else "1",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return add_cors_headers(jsonify(error_response)), 500

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

# Additional MCP endpoints that Jace.ai might expect
@app.route("/tools/list", methods=["GET", "POST"])
def tools_list():
    """Alternative tools list endpoint"""
    print(f"[MCP DEBUG] /tools/list called with method: {request.method}")
    tools = [
        {
            "name": "jira_list_projects",
            "description": "List all available Jira projects"
        },
        {
            "name": "jira_search_issues", 
            "description": "Search Jira issues using JQL"
        },
        {
            "name": "jira_get_issue",
            "description": "Get detailed information about a specific Jira issue"
        },
        {
            "name": "jira_create_issue",
            "description": "Create a new Jira issue"
        }
    ]
    
    response = jsonify({"tools": tools})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route("/initialize", methods=["POST"])
def initialize():
    """MCP initialization endpoint"""
    print(f"[MCP DEBUG] /initialize called")
    data = request.json or {}
    print(f"[MCP DEBUG] Initialize data: {json.dumps(data, indent=2)}")
    
    response_data = {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {
                "listChanged": True
            }
        },
        "serverInfo": {
            "name": "jira-mcp-server",
            "version": BUILD_VERSION
        }
    }
    
    response = jsonify(response_data)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route("/tools", methods=["GET", "POST"])
def tools_endpoint():
    """Alternative tools endpoint"""
    print(f"[MCP DEBUG] /tools called with method: {request.method}")
    if request.method == "POST":
        data = request.json or {}
        print(f"[MCP DEBUG] Tools POST data: {json.dumps(data, indent=2)}")
    
    tools = {
        "tools": [
            {
                "name": "jira_list_projects",
                "description": "List all available Jira projects",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "jira_search_issues", 
                "description": "Search Jira issues using JQL (Jira Query Language)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "jql": {
                            "type": "string",
                            "description": "JQL query string"
                        }
                    },
                    "required": ["jql"]
                }
            },
            {
                "name": "jira_get_issue",
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
                "name": "jira_create_issue",
                "description": "Create a new Jira issue",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_key": {"type": "string"},
                        "summary": {"type": "string"}
                    },
                    "required": ["project_key", "summary"]
                }
            }
        ]
    }
    
    response = jsonify(tools)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route("/call", methods=["POST"])
def call_tool():
    """MCP tool call endpoint"""
    print(f"[MCP DEBUG] /call endpoint called")
    data = request.json or {}
    print(f"[MCP DEBUG] Call data: {json.dumps(data, indent=2)}")
    
    tool_name = data.get("name")
    arguments = data.get("arguments", {})
    
    try:
        jira = get_jira_client()
        
        if tool_name == "jira_list_projects":
            result = jira.projects()
            response_data = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Found {len(result)} Jira projects:\n\n" + 
                               "\n".join([f"• {p['name']} ({p['key']})" for p in result])
                    }
                ]
            }
        elif tool_name == "jira_search_issues":
            jql = arguments.get("jql", "project IS NOT EMPTY ORDER BY created DESC")
            results = jira.jql(jql, limit=50)
            issues = results.get("issues", [])
            
            if not issues:
                response_data = {
                    "content": [{"type": "text", "text": f"No issues found for JQL: {jql}"}]
                }
            else:
                issue_list = []
                for issue in issues:
                    fields = issue.get("fields", {})
                    issue_list.append(f"• {issue['key']}: {fields.get('summary', 'No summary')}")
                
                response_data = {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(issues)} issues:\n" + "\n".join(issue_list)
                        }
                    ]
                }
        else:
            response_data = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Tool {tool_name} not implemented in /call endpoint"
                    }
                ]
            }
            
        response = jsonify(response_data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
        
    except Exception as e:
        print(f"[MCP DEBUG] Error in /call: {str(e)}")
        error_response = {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}]
        }
        response = jsonify(error_response)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500

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
            "username": JIRA_USERNAME,
            "version": BUILD_VERSION,
            "build_time": BUILD_TIME
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)