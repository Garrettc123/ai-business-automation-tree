"""
GitHub platform agent.

Leaf tasks:
  - create_issue       — open a new issue in a repository
  - create_pr          — open a pull request
  - add_comment        — post a comment on an issue or PR
  - close_issue        — close an existing issue
  - merge_pr           — merge a pull request

All calls use the GitHub REST API v3 via requests.
Auth: GITHUB_TOKEN environment variable (Personal-Access-Token or GitHub App token).
"""

import logging
import os

import requests

from tree import BranchNode, LeafNode, WorkflowState

logger = logging.getLogger(__name__)

_BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _repo(state: WorkflowState) -> str:
    """Return 'owner/repo' from event payload or env var."""
    evt = state.trigger_event
    repo = (
        evt.get("repository")
        or evt.get("repo")
        or os.getenv("GITHUB_REPO", "")
    )
    return repo


# ---------------------------------------------------------------------------
# Leaf actions
# ---------------------------------------------------------------------------


async def _create_issue(state: WorkflowState) -> dict:
    repo = _repo(state)
    if not repo:
        return {"status": "skipped", "reason": "GITHUB_REPO not configured"}

    payload = state.trigger_event.get("github_issue", {})
    title = payload.get("title", "Automated issue from AI Automation Tree")
    body = payload.get("body", "Created automatically by the AI Business Automation Tree.")
    labels = payload.get("labels", [])

    url = f"{_BASE}/repos/{repo}/issues"
    resp = requests.post(
        url,
        headers=_headers(),
        json={"title": title, "body": body, "labels": labels},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info("GitHub: created issue #%s in %s", data.get("number"), repo)
    return {"status": "success", "issue_number": data.get("number"), "url": data.get("html_url")}


async def _create_pr(state: WorkflowState) -> dict:
    repo = _repo(state)
    if not repo:
        return {"status": "skipped", "reason": "GITHUB_REPO not configured"}

    payload = state.trigger_event.get("github_pr", {})
    title = payload.get("title", "Automated PR from AI Automation Tree")
    body = payload.get("body", "")
    head = payload.get("head", "feature/automation")
    base = payload.get("base", "main")

    url = f"{_BASE}/repos/{repo}/pulls"
    resp = requests.post(
        url,
        headers=_headers(),
        json={"title": title, "body": body, "head": head, "base": base},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info("GitHub: created PR #%s in %s", data.get("number"), repo)
    return {"status": "success", "pr_number": data.get("number"), "url": data.get("html_url")}


async def _add_comment(state: WorkflowState) -> dict:
    repo = _repo(state)
    if not repo:
        return {"status": "skipped", "reason": "GITHUB_REPO not configured"}

    payload = state.trigger_event.get("github_comment", {})
    issue_number = payload.get("issue_number")
    body = payload.get("body", "Automated comment from AI Business Automation Tree.")

    if not issue_number:
        return {"status": "skipped", "reason": "github_comment.issue_number not provided"}

    url = f"{_BASE}/repos/{repo}/issues/{issue_number}/comments"
    resp = requests.post(url, headers=_headers(), json={"body": body}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    logger.info("GitHub: added comment to issue #%s", issue_number)
    return {"status": "success", "comment_id": data.get("id"), "url": data.get("html_url")}


async def _close_issue(state: WorkflowState) -> dict:
    repo = _repo(state)
    if not repo:
        return {"status": "skipped", "reason": "GITHUB_REPO not configured"}

    payload = state.trigger_event.get("github_close", {})
    issue_number = payload.get("issue_number")
    if not issue_number:
        return {"status": "skipped", "reason": "github_close.issue_number not provided"}

    url = f"{_BASE}/repos/{repo}/issues/{issue_number}"
    resp = requests.patch(url, headers=_headers(), json={"state": "closed"}, timeout=15)
    resp.raise_for_status()
    logger.info("GitHub: closed issue #%s in %s", issue_number, repo)
    return {"status": "success", "issue_number": issue_number}


async def _merge_pr(state: WorkflowState) -> dict:
    repo = _repo(state)
    if not repo:
        return {"status": "skipped", "reason": "GITHUB_REPO not configured"}

    payload = state.trigger_event.get("github_merge", {})
    pr_number = payload.get("pr_number")
    if not pr_number:
        return {"status": "skipped", "reason": "github_merge.pr_number not provided"}

    url = f"{_BASE}/repos/{repo}/pulls/{pr_number}/merge"
    resp = requests.put(
        url,
        headers=_headers(),
        json={"merge_method": payload.get("merge_method", "merge")},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info("GitHub: merged PR #%s in %s", pr_number, repo)
    return {"status": "success", "merged": data.get("merged"), "sha": data.get("sha")}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_github_branch(enabled: bool = True) -> BranchNode:
    """Return a fully-wired GitHub BranchNode."""
    branch = BranchNode(
        name="GitHub",
        description="GitHub automation: issues, PRs, comments",
        enabled=enabled,
    )
    branch.add_child(LeafNode("github.create_issue", "Open a new GitHub issue", _create_issue))
    branch.add_child(LeafNode("github.create_pr", "Open a pull request", _create_pr))
    branch.add_child(LeafNode("github.add_comment", "Post a comment on an issue/PR", _add_comment))
    branch.add_child(LeafNode("github.close_issue", "Close an existing issue", _close_issue))
    branch.add_child(LeafNode("github.merge_pr", "Merge a pull request", _merge_pr))
    return branch
