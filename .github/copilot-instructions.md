# AI Business Automation Tree — Copilot Instructions

## Purpose
Hierarchical AI business automation — tree-structured multi-agent system for seamless platform integration.

## Standards
- Python 3.11+, tree-structured agent architecture
- Parent nodes coordinate child agents via async message passing
- All nodes must implement `execute()`, `health_check()`, and `rollback()`
- Secrets from env vars or AWS SSM
- All workflows use `continue-on-error: true` on cloud steps

## Architecture
- Root node: `orchestrator.py`
- Branch nodes: `agents/{domain}/coordinator.py`
- Leaf nodes: `agents/{domain}/workers/*.py`
- State: persisted in S3 or Redis
