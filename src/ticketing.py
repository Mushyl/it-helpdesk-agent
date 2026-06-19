"""
Map a classified support request to ready-to-POST ticket payloads for the
two most common enterprise ITSM tools: Atlassian Jira and ServiceNow.

These are pure functions (no I/O, no network): they take the classification
fields and return a dict that matches each tool's REST API schema, so it can
be serialised to JSON and sent to the respective `POST` endpoint as-is.
"""

import config

# Our urgency scale -> Jira priority names.
_JIRA_PRIORITY = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}

# Our urgency scale -> ServiceNow numeric scale (1 = High, 2 = Medium, 3 = Low).
_SNOW_LEVEL = {"HIGH": "1", "MEDIUM": "2", "LOW": "3"}


def _issue_type(label: str, urgency: str) -> str:
    """Security requests and anything HIGH are Incidents; the rest are
    Service Requests — the standard ITIL split."""
    if label.upper() == "SECURITY" or urgency.upper() == "HIGH":
        return "Incident"
    return "Service Request"


def _build_description(user_message: str, reply: str) -> str:
    """Compose a ticket body: the verbatim employee request plus the
    AI-drafted resolution, clearly marked as a draft to review."""
    return (
        "Original employee request:\n"
        f"{user_message}\n\n"
        "---\n"
        "AI-suggested resolution (review before sending to the user):\n"
        f"{reply}"
    )


def to_jira_ticket(
    label: str,
    urgency: str,
    summary: str,
    description: str,
    *,
    project_key: str | None = None,
) -> dict:
    """Build a Jira issue-creation payload (`POST /rest/api/3/issue`)."""
    project_key = project_key or config.JIRA_PROJECT_KEY
    return {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": _issue_type(label, urgency)},
            "priority": {"name": _JIRA_PRIORITY.get(urgency.upper(), "Medium")},
            "labels": [label.lower()],
        }
    }


def to_servicenow_ticket(
    label: str,
    urgency: str,
    summary: str,
    description: str,
) -> dict:
    """Build a ServiceNow incident payload (`POST /api/now/table/incident`)."""
    level = _SNOW_LEVEL.get(urgency.upper(), "2")
    return {
        "short_description": summary,
        "description": description,
        "category": label.lower(),
        "urgency": level,
        "impact": level,
    }


def build_tickets(
    label: str,
    urgency: str,
    summary: str,
    user_message: str,
    reply: str,
) -> dict:
    """
    Build both ticket payloads for a single classified request.

    Returns:
        {"jira": {...}, "servicenow": {...}} — both JSON-serialisable and
        ready to POST to the respective ITSM REST API.
    """
    description = _build_description(user_message, reply)
    return {
        "jira": to_jira_ticket(label, urgency, summary, description),
        "servicenow": to_servicenow_ticket(label, urgency, summary, description),
    }
