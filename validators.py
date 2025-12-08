"""
Input Validation Utilities for Jira MCP Server

Provides validation functions to ensure safe and valid input
before making Jira API calls.
"""

import re
from typing import Dict, Any, Tuple, Optional, List


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


# Validation patterns
ISSUE_KEY_PATTERN = re.compile(r'^[A-Z][A-Z0-9]+-\d+$')
PROJECT_KEY_PATTERN = re.compile(r'^[A-Z][A-Z0-9]*$')
ACCOUNT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9:_-]+$')

# Max lengths to prevent abuse
MAX_SUMMARY_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 32000
MAX_COMMENT_LENGTH = 32000
MAX_JQL_LENGTH = 2000
MAX_LABEL_LENGTH = 255
MAX_RESULTS_LIMIT = 100


def validate_issue_key(issue_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a Jira issue key format (e.g., PROJ-123).

    Args:
        issue_key: The issue key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not issue_key:
        return False, "Issue key is required"

    if not isinstance(issue_key, str):
        return False, "Issue key must be a string"

    issue_key = issue_key.strip().upper()

    if not ISSUE_KEY_PATTERN.match(issue_key):
        return False, f"Invalid issue key format: '{issue_key}'. Expected format: PROJ-123"

    return True, None


def validate_project_key(project_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a Jira project key format (e.g., PROJ).

    Args:
        project_key: The project key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not project_key:
        return False, "Project key is required"

    if not isinstance(project_key, str):
        return False, "Project key must be a string"

    project_key = project_key.strip().upper()

    if len(project_key) < 2:
        return False, "Project key must be at least 2 characters"

    if len(project_key) > 10:
        return False, "Project key must be 10 characters or less"

    if not PROJECT_KEY_PATTERN.match(project_key):
        return False, f"Invalid project key format: '{project_key}'. Must start with a letter and contain only uppercase letters and numbers."

    return True, None


def validate_summary(summary: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an issue summary.

    Args:
        summary: The summary text to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not summary:
        return False, "Summary is required"

    if not isinstance(summary, str):
        return False, "Summary must be a string"

    summary = summary.strip()

    if len(summary) == 0:
        return False, "Summary cannot be empty"

    if len(summary) > MAX_SUMMARY_LENGTH:
        return False, f"Summary must be {MAX_SUMMARY_LENGTH} characters or less"

    return True, None


def validate_description(description: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an issue description.

    Args:
        description: The description text to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if description is None:
        return True, None  # Description is optional

    if not isinstance(description, str):
        return False, "Description must be a string"

    if len(description) > MAX_DESCRIPTION_LENGTH:
        return False, f"Description must be {MAX_DESCRIPTION_LENGTH} characters or less"

    return True, None


def validate_comment(comment: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a comment.

    Args:
        comment: The comment text to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not comment:
        return False, "Comment is required"

    if not isinstance(comment, str):
        return False, "Comment must be a string"

    comment = comment.strip()

    if len(comment) == 0:
        return False, "Comment cannot be empty"

    if len(comment) > MAX_COMMENT_LENGTH:
        return False, f"Comment must be {MAX_COMMENT_LENGTH} characters or less"

    return True, None


def validate_jql(jql: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a JQL query string.

    Args:
        jql: The JQL query to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not jql:
        return False, "JQL query is required"

    if not isinstance(jql, str):
        return False, "JQL must be a string"

    jql = jql.strip()

    if len(jql) == 0:
        return False, "JQL query cannot be empty"

    if len(jql) > MAX_JQL_LENGTH:
        return False, f"JQL query must be {MAX_JQL_LENGTH} characters or less"

    # Check for potentially dangerous patterns (basic SQL injection prevention)
    dangerous_patterns = [
        r';\s*(?:DROP|DELETE|TRUNCATE|UPDATE|INSERT)',
        r'--\s*$',
        r'/\*.*\*/',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, jql, re.IGNORECASE):
            return False, "JQL query contains invalid characters"

    return True, None


def validate_max_results(max_results: Any) -> Tuple[bool, Optional[str], int]:
    """
    Validate and sanitize max_results parameter.

    Args:
        max_results: The max results value to validate

    Returns:
        Tuple of (is_valid, error_message, sanitized_value)
    """
    if max_results is None:
        return True, None, 50  # Default value

    try:
        max_results = int(max_results)
    except (ValueError, TypeError):
        return False, "max_results must be a number", 50

    if max_results < 1:
        return False, "max_results must be at least 1", 50

    if max_results > MAX_RESULTS_LIMIT:
        return True, None, MAX_RESULTS_LIMIT  # Cap at max limit

    return True, None, max_results


def validate_issue_type(issue_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an issue type.

    Args:
        issue_type: The issue type to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if issue_type is None:
        return True, None  # Issue type is optional, defaults to Task

    if not isinstance(issue_type, str):
        return False, "Issue type must be a string"

    issue_type = issue_type.strip()

    # Common valid issue types
    valid_types = ['task', 'bug', 'story', 'epic', 'subtask', 'improvement', 'new feature']

    if issue_type.lower() not in valid_types:
        # Still allow it, but log a warning - the Jira API will validate
        pass

    return True, None


def validate_priority(priority: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a priority level.

    Args:
        priority: The priority to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if priority is None:
        return True, None  # Priority is optional

    if not isinstance(priority, str):
        return False, "Priority must be a string"

    return True, None


def validate_labels(labels: Any) -> Tuple[bool, Optional[str], List[str]]:
    """
    Validate and sanitize labels.

    Args:
        labels: The labels to validate

    Returns:
        Tuple of (is_valid, error_message, sanitized_labels)
    """
    if labels is None:
        return True, None, []

    if not isinstance(labels, list):
        return False, "Labels must be a list", []

    sanitized = []
    for label in labels:
        if not isinstance(label, str):
            return False, "Each label must be a string", []

        label = label.strip()

        if len(label) > MAX_LABEL_LENGTH:
            return False, f"Labels must be {MAX_LABEL_LENGTH} characters or less", []

        # Labels cannot contain spaces in Jira
        if ' ' in label:
            label = label.replace(' ', '_')

        if label:
            sanitized.append(label)

    return True, None, sanitized


def validate_transition_id(transition_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a transition ID.

    Args:
        transition_id: The transition ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not transition_id:
        return False, "Transition ID is required"

    if not isinstance(transition_id, str):
        return False, "Transition ID must be a string"

    # Transition IDs are typically numeric
    try:
        int(transition_id)
    except ValueError:
        return False, "Transition ID must be a numeric string"

    return True, None


def validate_create_issue_args(args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate all arguments for creating an issue.

    Args:
        args: Dictionary of arguments

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Required fields
    is_valid, error = validate_project_key(args.get('project_key'))
    if not is_valid:
        return False, error

    is_valid, error = validate_summary(args.get('summary'))
    if not is_valid:
        return False, error

    # Optional fields
    is_valid, error = validate_description(args.get('description'))
    if not is_valid:
        return False, error

    is_valid, error = validate_issue_type(args.get('issue_type'))
    if not is_valid:
        return False, error

    is_valid, error = validate_priority(args.get('priority'))
    if not is_valid:
        return False, error

    is_valid, error, _ = validate_labels(args.get('labels'))
    if not is_valid:
        return False, error

    return True, None


def validate_update_issue_args(args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate all arguments for updating an issue.

    Args:
        args: Dictionary of arguments

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Required fields
    is_valid, error = validate_issue_key(args.get('issue_key'))
    if not is_valid:
        return False, error

    # At least one field to update should be provided
    update_fields = ['summary', 'description', 'priority', 'labels']
    has_update = any(args.get(field) is not None for field in update_fields)

    if not has_update:
        return False, "At least one field to update is required"

    # Validate optional fields if provided
    if args.get('summary') is not None:
        is_valid, error = validate_summary(args['summary'])
        if not is_valid:
            return False, error

    if args.get('description') is not None:
        is_valid, error = validate_description(args['description'])
        if not is_valid:
            return False, error

    if args.get('labels') is not None:
        is_valid, error, _ = validate_labels(args['labels'])
        if not is_valid:
            return False, error

    return True, None


def sanitize_string(value: str, max_length: int = None) -> str:
    """
    Sanitize a string value by stripping whitespace and optionally truncating.

    Args:
        value: String to sanitize
        max_length: Optional max length to truncate to

    Returns:
        Sanitized string
    """
    if not value:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if max_length and len(value) > max_length:
        value = value[:max_length]

    return value
