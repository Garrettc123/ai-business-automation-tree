"""
Core tree architecture for AI Business Automation System.

Implements a hierarchical node structure with top-down traversal:
  - RootNode: master orchestrator coordinating all child nodes
  - BranchNode: platform-specific automation agents
  - LeafNode: individual task executors
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NodeType(str, Enum):
    ROOT = "root"
    BRANCH = "branch"
    LEAF = "leaf"


class NodeStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Workflow state — persists across an entire tree walk
# ---------------------------------------------------------------------------


class WorkflowState:
    """Track workflow state across async tree walks."""

    def __init__(self, trigger_event: Dict[str, Any], workflow_id: Optional[str] = None):
        self.workflow_id: str = workflow_id or str(uuid.uuid4())
        self.trigger_event: Dict[str, Any] = trigger_event
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.status: str = "running"
        self.node_results: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}
        self.errors: List[str] = []

    def record_result(self, node_name: str, result: Any) -> None:
        self.node_results[node_name] = result
        self.updated_at = datetime.now(timezone.utc)

    def record_error(self, node_name: str, error: str) -> None:
        self.errors.append(f"{node_name}: {error}")
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, status: str = "completed") -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "trigger_event": self.trigger_event,
            "node_results": self.node_results,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Base node
# ---------------------------------------------------------------------------


class AutomationNode:
    """Base class for all tree nodes."""

    def __init__(
        self,
        name: str,
        node_type: NodeType,
        description: str = "",
        enabled: bool = True,
    ):
        self.name: str = name
        self.node_type: NodeType = node_type
        self.description: str = description
        self.enabled: bool = enabled
        self.children: List["AutomationNode"] = []
        self.parent: Optional["AutomationNode"] = None
        self.status: NodeStatus = NodeStatus.IDLE
        self.executions: int = 0
        self.last_executed: Optional[datetime] = None

    def add_child(self, node: "AutomationNode") -> "AutomationNode":
        """Attach a child node and return it."""
        node.parent = self
        self.children.append(node)
        return node

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.node_type.value,
            "description": self.description,
            "enabled": self.enabled,
            "status": self.status.value,
            "executions": self.executions,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "children": [c.to_dict() for c in self.children],
        }


# ---------------------------------------------------------------------------
# Leaf node — individual task executor
# ---------------------------------------------------------------------------


class LeafNode(AutomationNode):
    """Leaf node that executes a single, concrete task."""

    def __init__(
        self,
        name: str,
        description: str = "",
        action: Optional[Callable[["WorkflowState"], Any]] = None,
        enabled: bool = True,
    ):
        super().__init__(name, NodeType.LEAF, description, enabled)
        self._action: Optional[Callable] = action

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        self.status = NodeStatus.RUNNING
        self.executions += 1
        self.last_executed = datetime.now(timezone.utc)

        try:
            if self._action:
                result = await self._action(state)
            else:
                result = {"status": "no_action_configured", "node": self.name}

            self.status = NodeStatus.SUCCESS
            state.record_result(self.name, result)
            logger.info("LeafNode %s succeeded", self.name)
            return result
        except Exception as exc:
            self.status = NodeStatus.FAILED
            error_msg = str(exc)
            state.record_error(self.name, error_msg)
            logger.error("LeafNode %s failed: %s", self.name, error_msg)
            return {"status": "error", "error": error_msg, "node": self.name}


# ---------------------------------------------------------------------------
# Branch node — platform-specific agent
# ---------------------------------------------------------------------------


class BranchNode(AutomationNode):
    """Branch node representing a platform-specific automation agent."""

    def __init__(
        self,
        name: str,
        description: str = "",
        enabled: bool = True,
        parallel: bool = False,
    ):
        super().__init__(name, NodeType.BRANCH, description, enabled)
        self.parallel: bool = parallel

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        self.status = NodeStatus.RUNNING
        self.executions += 1
        self.last_executed = datetime.now(timezone.utc)

        results: Dict[str, Any] = {}
        enabled_children = [c for c in self.children if c.enabled]

        try:
            if self.parallel and enabled_children:
                tasks = [child.execute(state) for child in enabled_children]
                raw = await asyncio.gather(*tasks, return_exceptions=True)
                for child, res in zip(enabled_children, raw):
                    if isinstance(res, Exception):
                        results[child.name] = {"status": "error", "error": str(res)}
                    else:
                        results[child.name] = res
            else:
                for child in enabled_children:
                    results[child.name] = await child.execute(state)

            self.status = NodeStatus.SUCCESS
            outcome = {"status": "success", "branch": self.name, "results": results}
            state.record_result(self.name, outcome)
            logger.info("BranchNode %s succeeded (%d tasks)", self.name, len(results))
            return outcome
        except Exception as exc:
            self.status = NodeStatus.FAILED
            error_msg = str(exc)
            state.record_error(self.name, error_msg)
            logger.error("BranchNode %s failed: %s", self.name, error_msg)
            return {"status": "error", "error": error_msg, "branch": self.name}


# ---------------------------------------------------------------------------
# Root node — master orchestrator
# ---------------------------------------------------------------------------


class RootNode(AutomationNode):
    """Root node — master orchestrator that coordinates all branch nodes."""

    def __init__(
        self,
        name: str = "MasterOrchestrator",
        description: str = "Root orchestrator coordinating all platform agents",
    ):
        super().__init__(name, NodeType.ROOT, description, enabled=True)

    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Walk the tree top-down, executing every enabled branch."""
        self.status = NodeStatus.RUNNING
        self.executions += 1
        self.last_executed = datetime.now(timezone.utc)

        branch_results: Dict[str, Any] = {}
        errors: List[str] = []

        for branch in self.children:
            if not branch.enabled:
                logger.info("Skipping disabled branch: %s", branch.name)
                continue
            try:
                result = await branch.execute(state)
                branch_results[branch.name] = result
            except Exception as exc:
                msg = str(exc)
                errors.append(f"{branch.name}: {msg}")
                branch_results[branch.name] = {"status": "error", "error": msg}
                logger.error("Branch %s raised during tree walk: %s", branch.name, msg)

        self.status = NodeStatus.SUCCESS if not errors else NodeStatus.FAILED

        final: Dict[str, Any] = {
            "workflow_id": state.workflow_id,
            "status": "completed" if not errors else "partial",
            "orchestrator": self.name,
            "branches_executed": len(branch_results),
            "results": branch_results,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        state.record_result(self.name, final)
        state.complete("completed" if not errors else "partial")
        return final


# ---------------------------------------------------------------------------
# Tree traversal helper — walk and collect results without executing
# ---------------------------------------------------------------------------


def traverse(node: AutomationNode, depth: int = 0) -> List[Dict[str, Any]]:
    """Return a flat list representing the tree (pre-order traversal)."""
    items: List[Dict[str, Any]] = []
    info = {
        "depth": depth,
        "name": node.name,
        "type": node.node_type.value,
        "description": node.description,
        "enabled": node.enabled,
        "status": node.status.value,
        "executions": node.executions,
        "children_count": len(node.children),
    }
    items.append(info)
    for child in node.children:
        items.extend(traverse(child, depth + 1))
    return items
