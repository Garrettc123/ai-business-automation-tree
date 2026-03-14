"""
Notion platform agent.

Leaf tasks:
  - create_page      — create a new page inside a parent page or database
  - update_page      — update page properties
  - query_database   — query a Notion database and return matching rows
  - create_database  — create a new inline database inside a page

Auth: NOTION_API_KEY environment variable (Internal Integration Token).
API: Notion REST API v1 at https://api.notion.com/v1
"""

import logging
import os

import requests

from tree import BranchNode, LeafNode, WorkflowState

logger = logging.getLogger(__name__)

_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def _headers() -> dict:
    api_key = os.getenv("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _check_key() -> bool:
    return bool(os.getenv("NOTION_API_KEY"))


# ---------------------------------------------------------------------------
# Leaf actions
# ---------------------------------------------------------------------------


async def _create_page(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "NOTION_API_KEY not configured"}

    payload = state.trigger_event.get("notion_page", {})
    parent_id = payload.get("parent_id") or os.getenv("NOTION_DEFAULT_PAGE_ID", "")
    parent_type = payload.get("parent_type", "page_id")  # "page_id" or "database_id"
    title = payload.get("title", "Automated page from AI Automation Tree")
    content = payload.get("content", "")

    if not parent_id:
        return {"status": "skipped", "reason": "notion_page.parent_id / NOTION_DEFAULT_PAGE_ID not set"}

    body: dict = {
        "parent": {parent_type: parent_id},
        "properties": {
            "title": {"title": [{"text": {"content": title}}]}
        },
    }
    if content:
        body["children"] = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            }
        ]

    resp = requests.post(f"{_BASE}/pages", headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    logger.info("Notion: created page '%s'", title)
    return {"status": "success", "page_id": data.get("id"), "url": data.get("url")}


async def _update_page(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "NOTION_API_KEY not configured"}

    payload = state.trigger_event.get("notion_update", {})
    page_id = payload.get("page_id")
    if not page_id:
        return {"status": "skipped", "reason": "notion_update.page_id not provided"}

    properties = payload.get("properties", {})
    archived = payload.get("archived", None)

    body: dict = {}
    if properties:
        body["properties"] = properties
    if archived is not None:
        body["archived"] = archived

    resp = requests.patch(f"{_BASE}/pages/{page_id}", headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    logger.info("Notion: updated page %s", page_id)
    return {"status": "success", "page_id": data.get("id"), "url": data.get("url")}


async def _query_database(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "NOTION_API_KEY not configured"}

    payload = state.trigger_event.get("notion_query", {})
    database_id = payload.get("database_id") or os.getenv("NOTION_DATABASE_ID", "")
    if not database_id:
        return {"status": "skipped", "reason": "notion_query.database_id / NOTION_DATABASE_ID not set"}

    body: dict = {}
    if "filter" in payload:
        body["filter"] = payload["filter"]
    if "sorts" in payload:
        body["sorts"] = payload["sorts"]

    resp = requests.post(f"{_BASE}/databases/{database_id}/query", headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    logger.info("Notion: queried database %s, got %d rows", database_id, len(results))
    return {"status": "success", "rows": len(results), "has_more": data.get("has_more", False)}


async def _create_database(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "NOTION_API_KEY not configured"}

    payload = state.trigger_event.get("notion_database", {})
    parent_page_id = payload.get("parent_page_id") or os.getenv("NOTION_DEFAULT_PAGE_ID", "")
    if not parent_page_id:
        return {"status": "skipped", "reason": "notion_database.parent_page_id / NOTION_DEFAULT_PAGE_ID not set"}

    title = payload.get("title", "Automated Database")
    properties = payload.get("properties", {"Name": {"title": {}}})

    body = {
        "parent": {"page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": properties,
    }
    resp = requests.post(f"{_BASE}/databases", headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    logger.info("Notion: created database '%s'", title)
    return {"status": "success", "database_id": data.get("id"), "url": data.get("url")}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_notion_branch(enabled: bool = True) -> BranchNode:
    """Return a fully-wired Notion BranchNode."""
    branch = BranchNode(
        name="Notion",
        description="Notion automation: pages, databases, queries",
        enabled=enabled,
    )
    branch.add_child(LeafNode("notion.create_page", "Create a Notion page", _create_page))
    branch.add_child(LeafNode("notion.update_page", "Update a Notion page", _update_page))
    branch.add_child(LeafNode("notion.query_database", "Query a Notion database", _query_database))
    branch.add_child(LeafNode("notion.create_database", "Create a Notion database", _create_database))
    return branch
