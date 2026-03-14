"""
Linear platform agent.

Leaf tasks:
  - create_issue    — create a new Linear issue
  - update_issue    — update an existing issue's state or priority
  - create_project  — create a new project
  - assign_issue    — assign an issue to a team member

Auth: LINEAR_API_KEY environment variable.
API: Linear GraphQL API at https://api.linear.app/graphql
"""

import logging
import os

import requests

from tree import BranchNode, LeafNode, WorkflowState

logger = logging.getLogger(__name__)

_GRAPHQL_URL = "https://api.linear.app/graphql"


def _headers() -> dict:
    api_key = os.getenv("LINEAR_API_KEY", "")
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _gql(query: str, variables: dict | None = None) -> dict:
    resp = requests.post(
        _GRAPHQL_URL,
        headers=_headers(),
        json={"query": query, "variables": variables or {}},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    # GraphQL errors are returned as 200 responses with an "errors" key
    if "errors" in payload:
        messages = [e.get("message", str(e)) for e in payload["errors"]]
        raise RuntimeError(f"Linear GraphQL errors: {'; '.join(messages)}")
    return payload


def _check_key() -> bool:
    return bool(os.getenv("LINEAR_API_KEY"))


# ---------------------------------------------------------------------------
# Leaf actions
# ---------------------------------------------------------------------------


async def _create_issue(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "LINEAR_API_KEY not configured"}

    payload = state.trigger_event.get("linear_issue", {})
    title = payload.get("title", "Automated issue from AI Automation Tree")
    description = payload.get("description", "")
    team_id = payload.get("team_id") or os.getenv("LINEAR_TEAM_ID", "")

    if not team_id:
        return {"status": "skipped", "reason": "linear_issue.team_id / LINEAR_TEAM_ID not set"}

    mutation = """
    mutation CreateIssue($title: String!, $description: String, $teamId: String!) {
      issueCreate(input: { title: $title, description: $description, teamId: $teamId }) {
        success
        issue { id identifier url title }
      }
    }
    """
    data = _gql(mutation, {"title": title, "description": description, "teamId": team_id})
    result = data.get("data", {}).get("issueCreate", {})
    if result.get("success"):
        issue = result.get("issue", {})
        logger.info("Linear: created issue %s", issue.get("identifier"))
        return {"status": "success", "issue_id": issue.get("id"), "identifier": issue.get("identifier"), "url": issue.get("url")}
    errors = data.get("errors", [])
    return {"status": "error", "errors": errors}


async def _update_issue(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "LINEAR_API_KEY not configured"}

    payload = state.trigger_event.get("linear_update", {})
    issue_id = payload.get("issue_id")
    if not issue_id:
        return {"status": "skipped", "reason": "linear_update.issue_id not provided"}

    state_id = payload.get("state_id")
    priority = payload.get("priority")
    update_input: dict = {}
    if state_id:
        update_input["stateId"] = state_id
    if priority is not None:
        update_input["priority"] = priority

    mutation = """
    mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) {
        success
        issue { id identifier state { name } }
      }
    }
    """
    data = _gql(mutation, {"id": issue_id, "input": update_input})
    result = data.get("data", {}).get("issueUpdate", {})
    if result.get("success"):
        issue = result.get("issue", {})
        logger.info("Linear: updated issue %s", issue.get("identifier"))
        return {"status": "success", "issue_id": issue.get("id"), "state": issue.get("state", {}).get("name")}
    return {"status": "error", "errors": data.get("errors", [])}


async def _create_project(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "LINEAR_API_KEY not configured"}

    payload = state.trigger_event.get("linear_project", {})
    name = payload.get("name", "Automated Project")
    team_ids = payload.get("team_ids") or [os.getenv("LINEAR_TEAM_ID", "")]
    team_ids = [t for t in team_ids if t]

    if not team_ids:
        return {"status": "skipped", "reason": "linear_project.team_ids / LINEAR_TEAM_ID not set"}

    mutation = """
    mutation CreateProject($name: String!, $teamIds: [String!]!) {
      projectCreate(input: { name: $name, teamIds: $teamIds }) {
        success
        project { id name url }
      }
    }
    """
    data = _gql(mutation, {"name": name, "teamIds": team_ids})
    result = data.get("data", {}).get("projectCreate", {})
    if result.get("success"):
        project = result.get("project", {})
        logger.info("Linear: created project '%s'", project.get("name"))
        return {"status": "success", "project_id": project.get("id"), "url": project.get("url")}
    return {"status": "error", "errors": data.get("errors", [])}


async def _assign_issue(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "LINEAR_API_KEY not configured"}

    payload = state.trigger_event.get("linear_assign", {})
    issue_id = payload.get("issue_id")
    assignee_id = payload.get("assignee_id")
    if not issue_id or not assignee_id:
        return {"status": "skipped", "reason": "linear_assign requires issue_id and assignee_id"}

    mutation = """
    mutation AssignIssue($id: String!, $assigneeId: String!) {
      issueUpdate(id: $id, input: { assigneeId: $assigneeId }) {
        success
        issue { id identifier assignee { name } }
      }
    }
    """
    data = _gql(mutation, {"id": issue_id, "assigneeId": assignee_id})
    result = data.get("data", {}).get("issueUpdate", {})
    if result.get("success"):
        issue = result.get("issue", {})
        logger.info("Linear: assigned issue %s", issue.get("identifier"))
        return {"status": "success", "issue_id": issue.get("id"), "assignee": issue.get("assignee", {}).get("name")}
    return {"status": "error", "errors": data.get("errors", [])}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_linear_branch(enabled: bool = True) -> BranchNode:
    """Return a fully-wired Linear BranchNode."""
    branch = BranchNode(
        name="Linear",
        description="Linear automation: issues, projects, assignments",
        enabled=enabled,
    )
    branch.add_child(LeafNode("linear.create_issue", "Create a Linear issue", _create_issue))
    branch.add_child(LeafNode("linear.update_issue", "Update a Linear issue", _update_issue))
    branch.add_child(LeafNode("linear.create_project", "Create a Linear project", _create_project))
    branch.add_child(LeafNode("linear.assign_issue", "Assign a Linear issue", _assign_issue))
    return branch
