"""
Jira MCP Server - Model Context Protocol compliant Jira integration

This server provides MCP-compliant tools for interacting with Jira,
including creating, updating, searching, and managing issues.
"""

from flask import Flask, request, jsonify
from atlassian import Jira
import json
import os
from datetime import datetime
from config import JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, validate_config
from tools import (
    get_tools_list,
    get_mcp_tools_response,
    get_simple_tools_response,
    resolve_tool_name,
    get_tool_names,
)
from validators import (
    validate_issue_key,
    validate_project_key,
    validate_summary,
    validate_description,
    validate_comment,
    validate_jql,
    validate_max_results,
    validate_create_issue_args,
    validate_update_issue_args,
    validate_transition_id,
    validate_labels,
    sanitize_string,
)
from rate_limit import rate_limit, rate_limiter
import requests

app = Flask(__name__)

# Build info
BUILD_VERSION = "v2.0.0-improved"
BUILD_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Simple in-memory token storage (use database in production)
oauth_tokens = {}

# OAuth configuration
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "JqlDDc1zqyr62EPkAOwI3hPdQVWefTZ")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")


def get_jira_client(user_id=None):
    """Get Jira client with OAuth token if available, fallback to API token."""
    if user_id and user_id in oauth_tokens:
        token_data = oauth_tokens[user_id]
        return Jira(
            url=JIRA_URL,
            oauth2={
                "access_token": token_data["access_token"],
                "token_type": "Bearer"
            },
            cloud=True
        )
    else:
        validate_config()
        return Jira(
            url=JIRA_URL,
            username=JIRA_USERNAME,
            password=JIRA_API_TOKEN,
            cloud=True
        )


def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-User-ID")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response


def create_mcp_response(request_id, content=None, error=None):
    """Create a standardized MCP JSON-RPC response."""
    if error:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": error.get("code", -32603),
                "message": error.get("message", "Internal error")
            }
        }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": content}]
        }
    }


def create_mcp_error(request_id, code, message):
    """Create an MCP error response."""
    return create_mcp_response(request_id, error={"code": code, "message": message})


# =============================================================================
# Tool Handlers
# =============================================================================

def handle_list_projects(jira, args, request_id):
    """Handle jira_list_projects tool."""
    projects = jira.projects()
    project_list = "\n".join([f"• {p['name']} ({p['key']})" for p in projects])
    return create_mcp_response(request_id, f"Found {len(projects)} Jira projects:\n\n{project_list}")


def handle_search_issues(jira, args, request_id):
    """Handle jira_search_issues tool."""
    jql = args.get("jql", "project IS NOT EMPTY ORDER BY created DESC")

    is_valid, error = validate_jql(jql)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    is_valid, error, max_results = validate_max_results(args.get("max_results"))
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    results = jira.jql(jql, limit=max_results)
    issues = results.get("issues", [])

    if not issues:
        return create_mcp_response(request_id, f"No issues found for JQL query: {jql}")

    issue_list = []
    for issue in issues:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        priority = fields.get("priority")
        issue_list.append(
            f"• {issue['key']}: {fields.get('summary', 'No summary')}\n"
            f"  Status: {fields.get('status', {}).get('name', 'Unknown')}\n"
            f"  Assignee: {assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'}\n"
            f"  Priority: {priority.get('name', 'None') if priority else 'None'}"
        )

    return create_mcp_response(
        request_id,
        f"Found {len(issues)} issues (JQL: {jql}):\n\n" + "\n\n".join(issue_list)
    )


def handle_get_issue(jira, args, request_id):
    """Handle jira_get_issue tool."""
    issue_key = args.get("issue_key")

    is_valid, error = validate_issue_key(issue_key)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    issue = jira.issue(issue_key.upper())
    fields = issue.get("fields", {})

    assignee = fields.get("assignee")
    reporter = fields.get("reporter")
    priority = fields.get("priority")

    details = f"""**{issue_key}: {fields.get('summary', 'No summary')}**

**Description:** {fields.get('description', 'No description') or 'No description'}

**Status:** {fields.get('status', {}).get('name', 'Unknown')}
**Priority:** {priority.get('name', 'None') if priority else 'None'}
**Issue Type:** {fields.get('issuetype', {}).get('name', 'Unknown')}
**Assignee:** {assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'}
**Reporter:** {reporter.get('displayName', 'Unknown') if reporter else 'Unknown'}
**Created:** {fields.get('created', 'Unknown')}
**Updated:** {fields.get('updated', 'Unknown')}
**Project:** {fields.get('project', {}).get('name', 'Unknown')} ({fields.get('project', {}).get('key', 'Unknown')})
**Labels:** {', '.join(fields.get('labels', [])) or 'None'}"""

    return create_mcp_response(request_id, details)


def handle_create_issue(jira, args, request_id):
    """Handle jira_create_issue tool."""
    is_valid, error = validate_create_issue_args(args)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    project_key = args.get("project_key").upper()
    summary = sanitize_string(args.get("summary"), 255)
    description = sanitize_string(args.get("description", ""), 32000)
    issue_type = args.get("issue_type", "Task")

    issue_data = {
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
        "project": {"key": project_key}
    }

    if args.get("priority"):
        issue_data["priority"] = {"name": args["priority"]}

    if args.get("labels"):
        _, _, sanitized_labels = validate_labels(args["labels"])
        if sanitized_labels:
            issue_data["labels"] = sanitized_labels

    new_issue = jira.issue_create(fields=issue_data)

    return create_mcp_response(
        request_id,
        f"Successfully created issue: {new_issue['key']}\n"
        f"Summary: {summary}\n"
        f"Project: {project_key}\n"
        f"Type: {issue_type}"
    )


def handle_update_issue(jira, args, request_id):
    """Handle jira_update_issue tool."""
    is_valid, error = validate_update_issue_args(args)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    issue_key = args.get("issue_key").upper()

    update_fields = {}

    if args.get("summary"):
        update_fields["summary"] = sanitize_string(args["summary"], 255)

    if args.get("description") is not None:
        update_fields["description"] = sanitize_string(args["description"], 32000)

    if args.get("priority"):
        update_fields["priority"] = {"name": args["priority"]}

    if args.get("labels") is not None:
        _, _, sanitized_labels = validate_labels(args["labels"])
        update_fields["labels"] = sanitized_labels

    jira.issue_update(issue_key, fields=update_fields)

    updated_fields = ", ".join(update_fields.keys())
    return create_mcp_response(
        request_id,
        f"Successfully updated issue {issue_key}\nUpdated fields: {updated_fields}"
    )


def handle_add_comment(jira, args, request_id):
    """Handle jira_add_comment tool."""
    issue_key = args.get("issue_key")
    comment = args.get("comment")

    is_valid, error = validate_issue_key(issue_key)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    is_valid, error = validate_comment(comment)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    issue_key = issue_key.upper()
    comment = sanitize_string(comment, 32000)

    jira.issue_add_comment(issue_key, comment)

    return create_mcp_response(
        request_id,
        f"Successfully added comment to {issue_key}"
    )


def handle_get_transitions(jira, args, request_id):
    """Handle jira_get_transitions tool."""
    issue_key = args.get("issue_key")

    is_valid, error = validate_issue_key(issue_key)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    issue_key = issue_key.upper()
    transitions = jira.get_issue_transitions(issue_key)

    if not transitions:
        return create_mcp_response(
            request_id,
            f"No transitions available for {issue_key}"
        )

    transition_list = []
    for t in transitions:
        transition_list.append(f"• ID: {t['id']} - {t['name']}")

    return create_mcp_response(
        request_id,
        f"Available transitions for {issue_key}:\n\n" + "\n".join(transition_list) +
        "\n\nUse jira_transition_issue with the transition ID to change status."
    )


def handle_transition_issue(jira, args, request_id):
    """Handle jira_transition_issue tool."""
    issue_key = args.get("issue_key")
    transition_id = args.get("transition_id")
    comment = args.get("comment")

    is_valid, error = validate_issue_key(issue_key)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    is_valid, error = validate_transition_id(transition_id)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    issue_key = issue_key.upper()

    # Perform the transition
    jira.issue_transition(issue_key, transition_id)

    # Add comment if provided
    if comment:
        is_valid, error = validate_comment(comment)
        if is_valid:
            jira.issue_add_comment(issue_key, sanitize_string(comment, 32000))

    # Get the new status
    issue = jira.issue(issue_key)
    new_status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")

    return create_mcp_response(
        request_id,
        f"Successfully transitioned {issue_key}\nNew status: {new_status}"
    )


def handle_assign_issue(jira, args, request_id):
    """Handle jira_assign_issue tool."""
    issue_key = args.get("issue_key")
    assignee = args.get("assignee")

    is_valid, error = validate_issue_key(issue_key)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    issue_key = issue_key.upper()

    if assignee is None or assignee == "" or assignee.lower() == "null":
        # Unassign
        jira.issue_update(issue_key, fields={"assignee": None})
        return create_mcp_response(
            request_id,
            f"Successfully unassigned {issue_key}"
        )
    else:
        # Assign to user
        jira.assign_issue(issue_key, assignee)
        return create_mcp_response(
            request_id,
            f"Successfully assigned {issue_key} to {assignee}"
        )


def handle_get_comments(jira, args, request_id):
    """Handle jira_get_comments tool."""
    issue_key = args.get("issue_key")

    is_valid, error = validate_issue_key(issue_key)
    if not is_valid:
        return create_mcp_error(request_id, -32602, error)

    is_valid, error, max_results = validate_max_results(args.get("max_results"))

    issue_key = issue_key.upper()

    # Get issue with comments
    issue = jira.issue(issue_key, expand="renderedFields")
    comments = issue.get("fields", {}).get("comment", {}).get("comments", [])

    if not comments:
        return create_mcp_response(
            request_id,
            f"No comments found on {issue_key}"
        )

    # Limit results
    comments = comments[:max_results]

    comment_list = []
    for c in comments:
        author = c.get("author", {}).get("displayName", "Unknown")
        created = c.get("created", "Unknown")
        body = c.get("body", "")
        # Truncate long comments
        if len(body) > 500:
            body = body[:500] + "..."
        comment_list.append(f"**{author}** ({created}):\n{body}")

    return create_mcp_response(
        request_id,
        f"Comments on {issue_key} ({len(comments)} shown):\n\n" + "\n\n---\n\n".join(comment_list)
    )


# Tool handler mapping
TOOL_HANDLERS = {
    "jira_list_projects": handle_list_projects,
    "jira_search_issues": handle_search_issues,
    "jira_get_issue": handle_get_issue,
    "jira_create_issue": handle_create_issue,
    "jira_update_issue": handle_update_issue,
    "jira_add_comment": handle_add_comment,
    "jira_get_transitions": handle_get_transitions,
    "jira_transition_issue": handle_transition_issue,
    "jira_assign_issue": handle_assign_issue,
    "jira_get_comments": handle_get_comments,
}


# =============================================================================
# Routes
# =============================================================================

@app.route("/")
def home():
    """Home page with server info."""
    tools_html = "\n".join([f"<li><code>{t['name']}</code> - {t['description']}</li>" for t in get_tools_list()])
    return f"""
    <h1>Jira MCP Server {BUILD_VERSION}</h1>
    <p><strong>Status:</strong> ✅ Connected to {JIRA_URL}</p>
    <p><strong>User:</strong> {JIRA_USERNAME}</p>
    <p><strong>Build:</strong> {BUILD_TIME}</p>

    <h2>MCP Tools Available ({len(get_tools_list())}):</h2>
    <ul>{tools_html}</ul>

    <h2>Endpoints:</h2>
    <ul>
        <li><strong>POST</strong> <code>/api/mcp</code> - MCP endpoint (JSON-RPC 2.0)</li>
        <li><strong>GET</strong> <code>/tools</code> - List available tools</li>
        <li><strong>GET</strong> <code>/health</code> - Health check</li>
    </ul>

    <h2>Test:</h2>
    <a href="/projects">View Projects</a> |
    <a href="/health">Health Check</a>
    """


@app.route("/api/mcp", methods=["GET", "POST", "OPTIONS"])
@rate_limit
def mcp_endpoint():
    """Main MCP endpoint - handles tool discovery and execution."""
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return add_cors_headers(jsonify({"status": "ok"}))

    # GET requests return tool list
    if request.method == "GET":
        if request.args.get("action") == "list_tools" or request.args.get("method") == "tools/list":
            return add_cors_headers(jsonify(get_simple_tools_response()))
        return add_cors_headers(jsonify(get_mcp_tools_response(request.args.get("id", "1"))))

    # POST requests handle tool calls
    try:
        data = request.json or {}
        request_id = data.get("id", "1")

        # Extract tool name from various formats
        tool_name = (
            data.get("method") or
            data.get("name") or
            data.get("tool") or
            data.get("action")
        )

        arguments = (
            data.get("params") or
            data.get("arguments") or
            data.get("input") or
            {}
        )

        # Handle MCP initialization
        if tool_name == "initialize":
            return add_cors_headers(jsonify({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "jira-mcp-server", "version": BUILD_VERSION}
                }
            }))

        # Handle tools/list
        if tool_name in ["tools/list", "listTools"]:
            return add_cors_headers(jsonify(get_mcp_tools_response(request_id)))

        # Resolve tool name (handle aliases)
        canonical_name = resolve_tool_name(tool_name)

        # Get handler for the tool
        handler = TOOL_HANDLERS.get(canonical_name)

        if not handler:
            available = ", ".join(get_tool_names())
            return add_cors_headers(jsonify(create_mcp_error(
                request_id, -32601,
                f"Method not found: {tool_name}. Available tools: {available}"
            )))

        # Get Jira client
        user_id = request.headers.get("X-User-ID") or arguments.get("user_id")
        jira = get_jira_client(user_id)

        # Execute the tool
        response_data = handler(jira, arguments, request_id)
        return add_cors_headers(jsonify(response_data))

    except Exception as e:
        return add_cors_headers(jsonify(create_mcp_error(
            request.json.get("id", "1") if request.json else "1",
            -32603,
            f"Internal error: {str(e)}"
        ))), 500


@app.route("/api/mcp/callback", methods=["GET", "POST"])
def oauth_callback():
    """Handle OAuth callback from Atlassian."""
    if request.method == "GET":
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")

        if error:
            return jsonify({"error": error}), 400

        if not code:
            return jsonify({"error": "No authorization code received"}), 400

        try:
            token_data = exchange_code_for_token(code)
            user_id = state or "default_user"
            oauth_tokens[user_id] = token_data
            return jsonify({
                "status": "success",
                "message": "OAuth authorization successful",
                "user_id": user_id
            })
        except Exception as e:
            return jsonify({"error": "token_exchange_failed", "message": str(e)}), 500

    elif request.method == "POST":
        data = request.json or {}
        if data.get("access_token"):
            user_id = data.get("user_id", "default_user")
            oauth_tokens[user_id] = {
                "access_token": data["access_token"],
                "token_type": data.get("token_type", "Bearer"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in")
            }
            return jsonify({"status": "success", "user_id": user_id})
        return jsonify({"error": "No access token provided"}), 400


def exchange_code_for_token(code):
    """Exchange authorization code for access token."""
    token_url = "https://auth.atlassian.com/oauth/token"
    redirect_uri = request.url_root.rstrip('/') + "/api/mcp/callback"

    response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if response.status_code == 200:
        return response.json()
    raise Exception(f"Token exchange failed: {response.status_code}")


# =============================================================================
# Convenience REST Endpoints (backward compatibility)
# =============================================================================

@app.route("/tools", methods=["GET", "POST"])
@app.route("/tools/list", methods=["GET", "POST"])
def tools_list():
    """List available tools."""
    response = jsonify(get_simple_tools_response())
    return add_cors_headers(response)


@app.route("/initialize", methods=["POST"])
def initialize():
    """MCP initialization endpoint."""
    return add_cors_headers(jsonify({
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {"listChanged": True}},
        "serverInfo": {"name": "jira-mcp-server", "version": BUILD_VERSION}
    }))


@app.route("/projects")
@rate_limit
def get_projects():
    """List all Jira projects."""
    try:
        jira = get_jira_client(request.headers.get("X-User-ID"))
        projects = jira.projects()
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/issues")
@rate_limit
def search_issues():
    """Search Jira issues."""
    jql = request.args.get("jql", "project IS NOT EMPTY ORDER BY created DESC")
    max_results = int(request.args.get("max_results", 50))

    try:
        jira = get_jira_client(request.headers.get("X-User-ID"))
        results = jira.jql(jql, limit=min(max_results, 100))
        return jsonify({
            "success": True,
            "jql": jql,
            "total": results.get("total", 0),
            "issues": results.get("issues", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/issue/<issue_key>")
@rate_limit
def get_issue(issue_key):
    """Get a specific Jira issue."""
    try:
        jira = get_jira_client(request.headers.get("X-User-ID"))
        issue = jira.issue(issue_key)
        return jsonify({"success": True, "issue": issue})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/create-issue", methods=["POST"])
@rate_limit
def create_issue():
    """Create a new Jira issue."""
    try:
        jira = get_jira_client(request.headers.get("X-User-ID"))
        data = request.json

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
        return jsonify({"success": True, "issue": new_issue})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health")
def health_check():
    """Health check endpoint."""
    try:
        jira = get_jira_client()
        jira.projects()
        return jsonify({
            "status": "healthy",
            "jira_url": JIRA_URL,
            "username": JIRA_USERNAME,
            "version": BUILD_VERSION,
            "build_time": BUILD_TIME,
            "tools_available": len(get_tools_list()),
            "rate_limit_stats": rate_limiter.get_stats()
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/call", methods=["POST"])
@rate_limit
def call_tool():
    """Direct tool call endpoint."""
    data = request.json or {}
    tool_name = data.get("name")
    arguments = data.get("arguments", {})

    try:
        jira = get_jira_client(request.headers.get("X-User-ID"))
        canonical_name = resolve_tool_name(tool_name)
        handler = TOOL_HANDLERS.get(canonical_name)

        if not handler:
            return add_cors_headers(jsonify({
                "content": [{"type": "text", "text": f"Tool {tool_name} not found"}]
            })), 404

        response = handler(jira, arguments, "1")
        # Extract just the content for this endpoint
        content = response.get("result", {}).get("content", [{"type": "text", "text": "No response"}])
        return add_cors_headers(jsonify({"content": content}))

    except Exception as e:
        return add_cors_headers(jsonify({
            "content": [{"type": "text", "text": f"Error: {str(e)}"}]
        })), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
