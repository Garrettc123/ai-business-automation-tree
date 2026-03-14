"""
Zapier platform agent.

Leaf tasks:
  - trigger_zap      — POST an event to a Zapier Webhook (Catch Hook) URL
  - trigger_webhook  — Generic HTTP POST to any webhook URL (Zapier or other)

Auth: ZAPIER_WEBHOOK_URL environment variable (set per-zap).
Multiple zaps can be configured via ZAPIER_WEBHOOK_URL_<NAME> env vars.
"""

import logging
import os

import requests

from tree import BranchNode, LeafNode, WorkflowState

logger = logging.getLogger(__name__)


def _check_url(url: str) -> bool:
    return bool(url and url.startswith("https://"))


# ---------------------------------------------------------------------------
# Leaf actions
# ---------------------------------------------------------------------------


async def _trigger_zap(state: WorkflowState) -> dict:
    """POST the event payload to the configured Zapier Catch Hook URL."""
    payload = state.trigger_event.get("zapier_trigger", {})
    webhook_url = payload.get("webhook_url") or os.getenv("ZAPIER_WEBHOOK_URL", "")

    if not _check_url(webhook_url):
        return {"status": "skipped", "reason": "ZAPIER_WEBHOOK_URL not configured or invalid"}

    data = payload.get("data", state.trigger_event)
    resp = requests.post(webhook_url, json=data, timeout=15)
    resp.raise_for_status()
    logger.info("Zapier: triggered webhook %s... status=%s", webhook_url[:40], resp.status_code)
    return {"status": "success", "http_status": resp.status_code, "response": resp.text[:200]}


async def _trigger_webhook(state: WorkflowState) -> dict:
    """Generic webhook POST — target URL must be provided in event payload."""
    payload = state.trigger_event.get("zapier_webhook", {})
    url = payload.get("url", "")

    if not _check_url(url):
        return {"status": "skipped", "reason": "zapier_webhook.url not provided or invalid"}

    data = payload.get("data", {})
    method = payload.get("method", "POST").upper()
    headers = payload.get("headers", {})

    if method == "POST":
        resp = requests.post(url, json=data, headers=headers, timeout=15)
    elif method == "GET":
        resp = requests.get(url, params=data, headers=headers, timeout=15)
    else:
        return {"status": "skipped", "reason": f"Unsupported method: {method}"}

    resp.raise_for_status()
    logger.info("Zapier/webhook: %s %s status=%s", method, url[:40], resp.status_code)
    return {"status": "success", "http_status": resp.status_code, "response": resp.text[:200]}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_zapier_branch(enabled: bool = True) -> BranchNode:
    """Return a fully-wired Zapier BranchNode."""
    branch = BranchNode(
        name="Zapier",
        description="Zapier automation: trigger zaps and generic webhooks",
        enabled=enabled,
    )
    branch.add_child(LeafNode("zapier.trigger_zap", "Trigger a Zapier Catch Hook", _trigger_zap))
    branch.add_child(LeafNode("zapier.trigger_webhook", "Fire a generic webhook", _trigger_webhook))
    return branch
