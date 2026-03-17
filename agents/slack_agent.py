"""
Slack platform agent.

Leaf tasks:
  - send_message       — post a message to a channel
  - create_channel     — create a new public channel
  - post_thread_reply  — reply inside an existing thread
  - upload_file        — upload a file to a channel

Auth: SLACK_BOT_TOKEN environment variable (Bot User OAuth Token, xoxb-...).
Uses slack-sdk (already in requirements.txt).
"""

import logging
import os

from tree import BranchNode, LeafNode, WorkflowState

logger = logging.getLogger(__name__)


def _client():
    from slack_sdk import WebClient  # lazy import — only when actually needed

    return WebClient(token=os.getenv("SLACK_BOT_TOKEN", ""))


def _check_key() -> bool:
    return bool(os.getenv("SLACK_BOT_TOKEN"))


# ---------------------------------------------------------------------------
# Leaf actions
# ---------------------------------------------------------------------------


async def _send_message(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "SLACK_BOT_TOKEN not configured"}

    payload = state.trigger_event.get("slack_message", {})
    channel = payload.get("channel") or os.getenv("SLACK_DEFAULT_CHANNEL", "#general")
    text = payload.get("text", "Automated message from AI Business Automation Tree")
    blocks = payload.get("blocks")

    kwargs: dict = {"channel": channel, "text": text}
    if blocks:
        kwargs["blocks"] = blocks

    resp = _client().chat_postMessage(**kwargs)
    ts = resp.get("ts")
    logger.info("Slack: posted message to %s (ts=%s)", channel, ts)
    return {"status": "success", "channel": channel, "ts": ts}


async def _create_channel(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "SLACK_BOT_TOKEN not configured"}

    payload = state.trigger_event.get("slack_channel", {})
    name = payload.get("name", "automation-channel")
    is_private = payload.get("is_private", False)

    resp = _client().conversations_create(name=name, is_private=is_private)
    channel_id = resp.get("channel", {}).get("id")
    logger.info("Slack: created channel %s (%s)", name, channel_id)
    return {"status": "success", "channel_id": channel_id, "name": name}


async def _post_thread_reply(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "SLACK_BOT_TOKEN not configured"}

    payload = state.trigger_event.get("slack_thread_reply", {})
    channel = payload.get("channel") or os.getenv("SLACK_DEFAULT_CHANNEL", "#general")
    thread_ts = payload.get("thread_ts")
    text = payload.get("text", "Automated reply from AI Business Automation Tree")

    if not thread_ts:
        return {"status": "skipped", "reason": "slack_thread_reply.thread_ts not provided"}

    resp = _client().chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
    logger.info("Slack: replied in thread %s in %s", thread_ts, channel)
    return {"status": "success", "channel": channel, "thread_ts": thread_ts, "reply_ts": resp.get("ts")}


async def _upload_file(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "SLACK_BOT_TOKEN not configured"}

    payload = state.trigger_event.get("slack_upload", {})
    channel = payload.get("channel") or os.getenv("SLACK_DEFAULT_CHANNEL", "#general")
    filename = payload.get("filename", "automation_report.txt")
    content = payload.get("content", "AI Business Automation Tree report")
    title = payload.get("title", "Automation Report")

    resp = _client().files_upload_v2(
        channel=channel,
        content=content,
        filename=filename,
        title=title,
    )
    file_id = resp.get("file", {}).get("id") if isinstance(resp.get("file"), dict) else None
    logger.info("Slack: uploaded file '%s' to %s", filename, channel)
    return {"status": "success", "channel": channel, "file_id": file_id}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_slack_branch(enabled: bool = True) -> BranchNode:
    """Return a fully-wired Slack BranchNode."""
    branch = BranchNode(
        name="Slack",
        description="Slack automation: messages, channels, threads, files",
        enabled=enabled,
    )
    branch.add_child(LeafNode("slack.send_message", "Post a Slack message", _send_message))
    branch.add_child(LeafNode("slack.create_channel", "Create a Slack channel", _create_channel))
    branch.add_child(LeafNode("slack.post_thread_reply", "Reply in a Slack thread", _post_thread_reply))
    branch.add_child(LeafNode("slack.upload_file", "Upload a file to Slack", _upload_file))
    return branch
