"""
Centralized MCP Tool Definitions for Jira MCP Server

This module defines all available Jira tools in a single place,
eliminating duplication and making maintenance easier.
"""

from typing import Dict, List, Any

# Tool definitions - Single source of truth
JIRA_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "jira_list_projects",
        "description": "List all available Jira projects from your Atlassian instance",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "jira_search_issues",
        "description": "Search Jira issues using JQL (Jira Query Language). Examples: 'project = PROJ', 'status = Open', 'assignee = currentUser()'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "JQL query string (e.g., 'project = TEST AND status = Open')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 50, max: 100)",
                    "default": 50
                }
            },
            "required": ["jql"]
        }
    },
    {
        "name": "jira_get_issue",
        "description": "Get detailed information about a specific Jira issue including status, assignee, description, and comments",
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
        "description": "Create a new Jira issue with summary, description, and optional fields like priority and assignee",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "Project key where the issue will be created (e.g., 'PROJ')"
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary/title of the issue"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the issue"
                },
                "issue_type": {
                    "type": "string",
                    "description": "Type of issue (e.g., 'Task', 'Bug', 'Story', 'Epic')",
                    "default": "Task"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level (e.g., 'Highest', 'High', 'Medium', 'Low', 'Lowest')"
                },
                "assignee": {
                    "type": "string",
                    "description": "Account ID or email of the assignee"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels to add to the issue"
                }
            },
            "required": ["project_key", "summary"]
        }
    },
    {
        "name": "jira_update_issue",
        "description": "Update an existing Jira issue's fields like summary, description, priority, or labels",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key to update (e.g., 'PROJ-123')"
                },
                "summary": {
                    "type": "string",
                    "description": "New summary/title for the issue"
                },
                "description": {
                    "type": "string",
                    "description": "New description for the issue"
                },
                "priority": {
                    "type": "string",
                    "description": "New priority level"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New list of labels (replaces existing)"
                }
            },
            "required": ["issue_key"]
        }
    },
    {
        "name": "jira_add_comment",
        "description": "Add a comment to an existing Jira issue",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g., 'PROJ-123')"
                },
                "comment": {
                    "type": "string",
                    "description": "Comment text to add to the issue"
                }
            },
            "required": ["issue_key", "comment"]
        }
    },
    {
        "name": "jira_get_transitions",
        "description": "Get available status transitions for a Jira issue (e.g., 'To Do' -> 'In Progress' -> 'Done')",
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
        "name": "jira_transition_issue",
        "description": "Change the status of a Jira issue by performing a transition (e.g., move from 'To Do' to 'In Progress')",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g., 'PROJ-123')"
                },
                "transition_id": {
                    "type": "string",
                    "description": "ID of the transition to perform (use jira_get_transitions to find available transitions)"
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment to add when transitioning"
                }
            },
            "required": ["issue_key", "transition_id"]
        }
    },
    {
        "name": "jira_assign_issue",
        "description": "Assign or unassign a Jira issue to a user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g., 'PROJ-123')"
                },
                "assignee": {
                    "type": "string",
                    "description": "Account ID or email of the assignee. Use null or empty string to unassign."
                }
            },
            "required": ["issue_key"]
        }
    },
    {
        "name": "jira_get_comments",
        "description": "Get all comments on a Jira issue",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g., 'PROJ-123')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of comments to return (default: 50)",
                    "default": 50
                }
            },
            "required": ["issue_key"]
        }
    }
]


def get_tools_list() -> List[Dict[str, Any]]:
    """Get the complete list of available tools."""
    return JIRA_TOOLS


def get_tool_names() -> List[str]:
    """Get list of tool names only."""
    return [tool["name"] for tool in JIRA_TOOLS]


def get_tool_by_name(name: str) -> Dict[str, Any]:
    """Get a specific tool definition by name."""
    normalized_name = name.replace("-", "_").lower()
    for tool in JIRA_TOOLS:
        if tool["name"].lower() == normalized_name:
            return tool
    return None


def get_mcp_tools_response(request_id: str = "1") -> Dict[str, Any]:
    """Get tools in MCP JSON-RPC response format."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": JIRA_TOOLS
        }
    }


def get_simple_tools_response() -> Dict[str, Any]:
    """Get tools in simple format (without JSON-RPC wrapper)."""
    return {"tools": JIRA_TOOLS}


# Tool name aliases for backward compatibility
TOOL_ALIASES = {
    "list_jira_projects": "jira_list_projects",
    "search_jira_issues": "jira_search_issues",
    "get_jira_issue": "jira_get_issue",
    "create_jira_issue": "jira_create_issue",
    "update_jira_issue": "jira_update_issue",
    "add_jira_comment": "jira_add_comment",
    "get_jira_transitions": "jira_get_transitions",
    "transition_jira_issue": "jira_transition_issue",
    "assign_jira_issue": "jira_assign_issue",
    "get_jira_comments": "jira_get_comments",
}


def resolve_tool_name(name: str) -> str:
    """Resolve a tool name to its canonical form, handling aliases."""
    if not name:
        return None
    normalized = name.lower().replace("-", "_")
    if normalized in TOOL_ALIASES:
        return TOOL_ALIASES[normalized]
    for tool in JIRA_TOOLS:
        if tool["name"].lower() == normalized:
            return tool["name"]
    return name
