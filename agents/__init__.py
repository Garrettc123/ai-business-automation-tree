"""Platform-specific automation agents for the AI Business Automation Tree."""

from agents.github_agent import build_github_branch
from agents.hubspot_agent import build_hubspot_branch
from agents.linear_agent import build_linear_branch
from agents.notion_agent import build_notion_branch
from agents.slack_agent import build_slack_branch
from agents.stripe_agent import build_stripe_branch
from agents.zapier_agent import build_zapier_branch

__all__ = [
    "build_github_branch",
    "build_hubspot_branch",
    "build_linear_branch",
    "build_notion_branch",
    "build_slack_branch",
    "build_stripe_branch",
    "build_zapier_branch",
]
