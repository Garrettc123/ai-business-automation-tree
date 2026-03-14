"""
Comprehensive pytest test suite for the AI Business Automation Tree.

Tests cover:
  - Tree data structures (RootNode, BranchNode, LeafNode)
  - WorkflowState management
  - Tree traversal
  - Async tree walk (top-down execution)
  - Platform agents (GitHub, Linear, Notion, Slack, Stripe, HubSpot, Zapier)
  - HTTP endpoints (health, status, tree, workflows, webhook, dashboard)
  - State management across async walks
  - Event counter
"""

import asyncio
import json
import os
import sys
import threading
import time
import urllib.request
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Tree imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tree import (
    AutomationNode,
    BranchNode,
    LeafNode,
    NodeStatus,
    NodeType,
    RootNode,
    WorkflowState,
    traverse,
)


# ===========================================================================
# WorkflowState tests
# ===========================================================================


class TestWorkflowState:
    def test_default_workflow_id_is_uuid(self):
        state = WorkflowState(trigger_event={"type": "test"})
        assert len(state.workflow_id) == 36  # UUID format
        assert "-" in state.workflow_id

    def test_custom_workflow_id(self):
        state = WorkflowState(trigger_event={}, workflow_id="custom-id")
        assert state.workflow_id == "custom-id"

    def test_initial_status_is_running(self):
        state = WorkflowState(trigger_event={})
        assert state.status == "running"

    def test_record_result(self):
        state = WorkflowState(trigger_event={})
        state.record_result("my_node", {"ok": True})
        assert state.node_results["my_node"] == {"ok": True}

    def test_record_error(self):
        state = WorkflowState(trigger_event={})
        state.record_error("bad_node", "something went wrong")
        assert any("bad_node" in e for e in state.errors)

    def test_complete_sets_status(self):
        state = WorkflowState(trigger_event={})
        state.complete("completed")
        assert state.status == "completed"

    def test_to_dict_has_required_keys(self):
        state = WorkflowState(trigger_event={"event": "webhook"})
        d = state.to_dict()
        for key in ("workflow_id", "status", "created_at", "updated_at", "trigger_event", "node_results", "errors"):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_serialisable(self):
        state = WorkflowState(trigger_event={"x": 1})
        state.record_result("n", {"val": 42})
        json.dumps(state.to_dict())  # must not raise


# ===========================================================================
# LeafNode tests
# ===========================================================================


class TestLeafNode:
    def test_node_type_is_leaf(self):
        node = LeafNode("my_leaf")
        assert node.node_type == NodeType.LEAF

    def test_no_action_returns_no_action_status(self):
        node = LeafNode("bare_leaf")
        state = WorkflowState(trigger_event={})
        result = asyncio.get_event_loop().run_until_complete(node.execute(state))
        assert result["status"] == "no_action_configured"

    def test_action_is_called(self):
        called = []

        async def my_action(state):
            called.append(True)
            return {"status": "done"}

        node = LeafNode("action_leaf", action=my_action)
        state = WorkflowState(trigger_event={})
        result = asyncio.get_event_loop().run_until_complete(node.execute(state))
        assert result["status"] == "done"
        assert called

    def test_action_exception_is_caught(self):
        async def failing_action(state):
            raise ValueError("boom")

        node = LeafNode("bad_leaf", action=failing_action)
        state = WorkflowState(trigger_event={})
        result = asyncio.get_event_loop().run_until_complete(node.execute(state))
        assert result["status"] == "error"
        assert "boom" in result["error"]

    def test_status_becomes_success(self):
        async def ok_action(state):
            return {"status": "ok"}

        node = LeafNode("success_leaf", action=ok_action)
        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(node.execute(state))
        assert node.status == NodeStatus.SUCCESS

    def test_status_becomes_failed_on_error(self):
        async def err_action(state):
            raise RuntimeError("fail")

        node = LeafNode("fail_leaf", action=err_action)
        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(node.execute(state))
        assert node.status == NodeStatus.FAILED

    def test_execution_count_increments(self):
        node = LeafNode("count_leaf")
        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(node.execute(state))
        asyncio.get_event_loop().run_until_complete(node.execute(state))
        assert node.executions == 2

    def test_result_stored_in_state(self):
        async def ok_action(state):
            return {"value": 99}

        node = LeafNode("result_leaf", action=ok_action)
        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(node.execute(state))
        assert state.node_results["result_leaf"] == {"value": 99}

    def test_to_dict(self):
        node = LeafNode("dict_leaf", description="A test leaf")
        d = node.to_dict()
        assert d["name"] == "dict_leaf"
        assert d["type"] == "leaf"
        assert d["description"] == "A test leaf"
        assert d["children"] == []


# ===========================================================================
# BranchNode tests
# ===========================================================================


class TestBranchNode:
    def test_node_type_is_branch(self):
        node = BranchNode("my_branch")
        assert node.node_type == NodeType.BRANCH

    def test_add_child(self):
        branch = BranchNode("parent")
        leaf = LeafNode("child")
        branch.add_child(leaf)
        assert leaf in branch.children
        assert leaf.parent is branch

    def test_executes_children_sequentially(self):
        order = []

        def make_action(name):
            async def action(state):
                order.append(name)
                return {"status": "ok"}
            return action

        branch = BranchNode("seq_branch")
        for name in ("a", "b", "c"):
            branch.add_child(LeafNode(name, action=make_action(name)))

        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(branch.execute(state))
        assert order == ["a", "b", "c"]

    def test_disabled_children_are_skipped(self):
        called = []

        async def action(state):
            called.append(True)
            return {"status": "ok"}

        branch = BranchNode("skip_branch")
        branch.add_child(LeafNode("enabled_leaf", action=action, enabled=True))
        branch.add_child(LeafNode("disabled_leaf", action=action, enabled=False))

        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(branch.execute(state))
        assert len(called) == 1

    def test_parallel_execution(self):
        async def slow_action(state):
            await asyncio.sleep(0.05)
            return {"status": "ok"}

        branch = BranchNode("parallel_branch", parallel=True)
        for i in range(4):
            branch.add_child(LeafNode(f"leaf_{i}", action=slow_action))

        state = WorkflowState(trigger_event={})
        start = time.monotonic()
        asyncio.get_event_loop().run_until_complete(branch.execute(state))
        elapsed = time.monotonic() - start
        # Should be < 4 × 0.05 = 0.2 s if truly parallel
        assert elapsed < 0.18

    def test_branch_result_contains_children_results(self):
        async def action(state):
            return {"value": 1}

        branch = BranchNode("res_branch")
        branch.add_child(LeafNode("leaf_a", action=action))
        branch.add_child(LeafNode("leaf_b", action=action))

        state = WorkflowState(trigger_event={})
        result = asyncio.get_event_loop().run_until_complete(branch.execute(state))
        assert "leaf_a" in result["results"]
        assert "leaf_b" in result["results"]

    def test_branch_to_dict_includes_children(self):
        branch = BranchNode("dict_branch")
        branch.add_child(LeafNode("child_leaf"))
        d = branch.to_dict()
        assert len(d["children"]) == 1
        assert d["children"][0]["name"] == "child_leaf"


# ===========================================================================
# RootNode tests
# ===========================================================================


class TestRootNode:
    def test_node_type_is_root(self):
        root = RootNode()
        assert root.node_type == NodeType.ROOT

    def test_default_name(self):
        root = RootNode()
        assert root.name == "MasterOrchestrator"

    def test_tree_walk_executes_all_branches(self):
        visited = []

        async def record(state):
            visited.append(True)
            return {"status": "ok"}

        root = RootNode()
        for name in ("b1", "b2", "b3"):
            branch = BranchNode(name)
            branch.add_child(LeafNode(f"{name}_leaf", action=record))
            root.add_child(branch)

        state = WorkflowState(trigger_event={"test": True})
        result = asyncio.get_event_loop().run_until_complete(root.execute(state))
        assert result["branches_executed"] == 3
        assert len(visited) == 3

    def test_disabled_branches_are_skipped(self):
        called = []

        async def action(state):
            called.append(True)
            return {"status": "ok"}

        root = RootNode()
        b_enabled = BranchNode("enabled_b", enabled=True)
        b_enabled.add_child(LeafNode("e_leaf", action=action))
        b_disabled = BranchNode("disabled_b", enabled=False)
        b_disabled.add_child(LeafNode("d_leaf", action=action))
        root.add_child(b_enabled)
        root.add_child(b_disabled)

        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(root.execute(state))
        assert len(called) == 1  # only the enabled branch ran

    def test_branch_error_does_not_crash_root(self):
        async def bad_action(state):
            raise RuntimeError("branch error")

        root = RootNode()
        bad_branch = BranchNode("bad_b")
        bad_branch.add_child(LeafNode("bad_leaf", action=bad_action))
        good_branch = BranchNode("good_b")

        async def good_action(state):
            return {"status": "ok"}

        good_branch.add_child(LeafNode("good_leaf", action=good_action))
        root.add_child(bad_branch)
        root.add_child(good_branch)

        state = WorkflowState(trigger_event={})
        result = asyncio.get_event_loop().run_until_complete(root.execute(state))
        # Good branch still ran
        assert "good_b" in result["results"]
        assert result["results"]["good_b"]["status"] == "success"

    def test_state_is_completed_after_walk(self):
        root = RootNode()
        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(root.execute(state))
        assert state.status in ("completed", "partial")

    def test_result_stored_in_state(self):
        root = RootNode()
        state = WorkflowState(trigger_event={})
        asyncio.get_event_loop().run_until_complete(root.execute(state))
        assert "MasterOrchestrator" in state.node_results


# ===========================================================================
# Traverse tests
# ===========================================================================


class TestTraverse:
    def test_traverse_returns_root_first(self):
        root = RootNode()
        nodes = traverse(root)
        assert nodes[0]["name"] == "MasterOrchestrator"
        assert nodes[0]["depth"] == 0

    def test_traverse_depth_increments(self):
        root = RootNode()
        branch = BranchNode("b")
        leaf = LeafNode("l")
        branch.add_child(leaf)
        root.add_child(branch)

        nodes = traverse(root)
        depths = {n["name"]: n["depth"] for n in nodes}
        assert depths["MasterOrchestrator"] == 0
        assert depths["b"] == 1
        assert depths["l"] == 2

    def test_traverse_counts_children(self):
        root = RootNode()
        branch = BranchNode("b")
        branch.add_child(LeafNode("l1"))
        branch.add_child(LeafNode("l2"))
        root.add_child(branch)

        nodes = traverse(root)
        branch_info = next(n for n in nodes if n["name"] == "b")
        assert branch_info["children_count"] == 2


# ===========================================================================
# Platform agent factory tests
# ===========================================================================


class TestPlatformAgents:
    """Test that every agent factory creates a correctly-shaped BranchNode."""

    def _assert_branch_shape(self, branch: BranchNode, name: str, min_leaves: int = 2):
        assert isinstance(branch, BranchNode)
        assert branch.name == name
        assert len(branch.children) >= min_leaves
        for child in branch.children:
            assert isinstance(child, LeafNode)

    def test_github_branch(self):
        from agents.github_agent import build_github_branch
        branch = build_github_branch(enabled=True)
        self._assert_branch_shape(branch, "GitHub", min_leaves=5)

    def test_linear_branch(self):
        from agents.linear_agent import build_linear_branch
        branch = build_linear_branch(enabled=True)
        self._assert_branch_shape(branch, "Linear", min_leaves=4)

    def test_notion_branch(self):
        from agents.notion_agent import build_notion_branch
        branch = build_notion_branch(enabled=True)
        self._assert_branch_shape(branch, "Notion", min_leaves=4)

    def test_slack_branch(self):
        from agents.slack_agent import build_slack_branch
        branch = build_slack_branch(enabled=True)
        self._assert_branch_shape(branch, "Slack", min_leaves=4)

    def test_stripe_branch(self):
        from agents.stripe_agent import build_stripe_branch
        branch = build_stripe_branch(enabled=True)
        self._assert_branch_shape(branch, "Stripe", min_leaves=4)

    def test_hubspot_branch(self):
        from agents.hubspot_agent import build_hubspot_branch
        branch = build_hubspot_branch(enabled=True)
        self._assert_branch_shape(branch, "HubSpot", min_leaves=4)

    def test_zapier_branch(self):
        from agents.zapier_agent import build_zapier_branch
        branch = build_zapier_branch(enabled=True)
        self._assert_branch_shape(branch, "Zapier", min_leaves=2)

    def test_all_agents_importable(self):
        from agents import (
            build_github_branch,
            build_hubspot_branch,
            build_linear_branch,
            build_notion_branch,
            build_slack_branch,
            build_stripe_branch,
            build_zapier_branch,
        )
        assert all([
            build_github_branch,
            build_linear_branch,
            build_notion_branch,
            build_slack_branch,
            build_stripe_branch,
            build_hubspot_branch,
            build_zapier_branch,
        ])


# ===========================================================================
# Skipping behavior when API keys are absent
# ===========================================================================


class TestAgentSkipWhenUnconfigured:
    """Agents must return skipped status when API keys are missing (not crash)."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _state(self, **kwargs):
        return WorkflowState(trigger_event=kwargs)

    def test_github_skips_without_token(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        from agents.github_agent import _create_issue
        result = self._run(_create_issue(self._state()))
        assert result["status"] == "skipped"

    def test_linear_skips_without_key(self, monkeypatch):
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        from agents.linear_agent import _create_issue
        result = self._run(_create_issue(self._state()))
        assert result["status"] == "skipped"

    def test_notion_skips_without_key(self, monkeypatch):
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        from agents.notion_agent import _create_page
        result = self._run(_create_page(self._state()))
        assert result["status"] == "skipped"

    def test_slack_skips_without_token(self, monkeypatch):
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        from agents.slack_agent import _send_message
        result = self._run(_send_message(self._state()))
        assert result["status"] == "skipped"

    def test_stripe_skips_without_key(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        from agents.stripe_agent import _charge_card
        result = self._run(_charge_card(self._state()))
        assert result["status"] == "skipped"

    def test_hubspot_skips_without_key(self, monkeypatch):
        monkeypatch.delenv("HUBSPOT_API_KEY", raising=False)
        from agents.hubspot_agent import _create_contact
        result = self._run(_create_contact(self._state()))
        assert result["status"] == "skipped"

    def test_zapier_skips_without_url(self, monkeypatch):
        monkeypatch.delenv("ZAPIER_WEBHOOK_URL", raising=False)
        from agents.zapier_agent import _trigger_zap
        result = self._run(_trigger_zap(self._state()))
        assert result["status"] == "skipped"

    def test_zapier_generic_skips_without_url(self):
        from agents.zapier_agent import _trigger_webhook
        result = self._run(_trigger_webhook(self._state()))
        assert result["status"] == "skipped"


# ===========================================================================
# Full tree integration test (all agents, no external calls)
# ===========================================================================


class TestFullTreeIntegration:
    """Build the full tree and do a dry-run walk with all APIs absent."""

    def test_full_tree_walk_completes(self, monkeypatch):
        """Tree walk should succeed (all agents skip gracefully) when no API keys."""
        for key in (
            "GITHUB_TOKEN", "GITHUB_REPO",
            "LINEAR_API_KEY",
            "NOTION_API_KEY",
            "SLACK_BOT_TOKEN",
            "STRIPE_SECRET_KEY",
            "HUBSPOT_API_KEY",
            "ZAPIER_WEBHOOK_URL",
        ):
            monkeypatch.delenv(key, raising=False)

        from tree import RootNode
        from agents import (
            build_github_branch, build_linear_branch, build_notion_branch,
            build_slack_branch, build_stripe_branch, build_hubspot_branch,
            build_zapier_branch,
        )

        root = RootNode()
        root.add_child(build_github_branch())
        root.add_child(build_linear_branch())
        root.add_child(build_notion_branch())
        root.add_child(build_slack_branch())
        root.add_child(build_stripe_branch())
        root.add_child(build_hubspot_branch())
        root.add_child(build_zapier_branch())

        state = WorkflowState(trigger_event={"source": "test"})
        result = asyncio.get_event_loop().run_until_complete(root.execute(state))

        assert result["branches_executed"] == 7
        assert state.status in ("completed", "partial")

    def test_tree_has_seven_branches(self):
        from main import build_tree
        root = build_tree()
        assert len(root.children) == 7

    def test_traverse_full_tree(self):
        from main import build_tree
        root = build_tree()
        nodes = traverse(root)
        types = [n["type"] for n in nodes]
        assert "root" in types
        assert "branch" in types
        assert "leaf" in types


# ===========================================================================
# HTTP server endpoint tests
# ===========================================================================


def _start_test_server(port: int):
    """Start the server in a daemon thread for testing."""
    from main import run_server
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
    # Poll until the server responds (up to 5 seconds)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1)
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"Test server on port {port} did not start in time")


class TestHTTPEndpoints:
    """Integration tests for the HTTP API."""

    PORT = 18765  # unique port to avoid collisions

    @classmethod
    def setup_class(cls):
        _start_test_server(cls.PORT)

    def _get(self, path: str):
        url = f"http://localhost:{self.PORT}{path}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())

    def _post(self, path: str, data: dict):
        url = f"http://localhost:{self.PORT}{path}"
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())

    def test_health_endpoint(self):
        status, data = self._get("/health")
        assert status == 200
        assert data["status"] == "healthy"

    def test_api_status(self):
        status, data = self._get("/api/status")
        assert status == 200
        assert "tree" in data
        assert data["tree"]["branches"] == 7

    def test_api_tree(self):
        status, data = self._get("/api/tree")
        assert status == 200
        assert "nodes" in data
        assert data["total"] > 1

    def test_api_tree_has_root(self):
        _, data = self._get("/api/tree")
        root_nodes = [n for n in data["nodes"] if n["type"] == "root"]
        assert len(root_nodes) == 1

    def test_api_tree_has_seven_branches(self):
        _, data = self._get("/api/tree")
        branch_nodes = [n for n in data["nodes"] if n["type"] == "branch"]
        assert len(branch_nodes) == 7

    def test_api_workflows_initially_empty(self):
        status, data = self._get("/api/workflows")
        assert status == 200
        assert isinstance(data, list)

    def test_webhook_returns_202(self):
        status, data = self._post("/webhook", {"source": "test", "event": "pytest"})
        assert status == 202
        assert data["status"] == "accepted"
        assert "workflow_id" in data

    def test_api_trigger_returns_202(self):
        status, data = self._post("/api/trigger", {"source": "manual"})
        assert status == 202
        assert "workflow_id" in data

    def test_workflow_appears_after_trigger(self):
        _, trigger_data = self._post("/webhook", {"type": "test_workflow"})
        wid = trigger_data["workflow_id"]
        time.sleep(0.1)
        status, wf_data = self._get("/api/workflows")
        assert status == 200
        wf_ids = [w["workflow_id"] for w in wf_data]
        assert wid in wf_ids

    def test_get_specific_workflow(self):
        _, trigger_data = self._post("/webhook", {"type": "specific_workflow"})
        wid = trigger_data["workflow_id"]
        time.sleep(0.1)
        status, data = self._get(f"/api/workflows/{wid}")
        assert status == 200
        assert data["workflow_id"] == wid

    def test_dashboard_returns_html(self):
        url = f"http://localhost:{self.PORT}/dashboard"
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status == 200
            content_type = resp.headers.get("Content-Type", "")
            assert "text/html" in content_type
            body = resp.read().decode()
            assert "AI Business Automation Tree" in body

    def test_dashboard_contains_tree_script(self):
        url = f"http://localhost:{self.PORT}/dashboard"
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode()
            assert "/api/tree" in body
            assert "/api/workflows" in body

    def test_404_for_unknown_path(self):
        url = f"http://localhost:{self.PORT}/nonexistent"
        try:
            urllib.request.urlopen(url, timeout=5)
            assert False, "Expected 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404

    def test_events_today_increments(self):
        _, before = self._get("/health")
        count_before = before.get("events_today", 0)
        self._post("/webhook", {"event": "count_test"})
        time.sleep(0.1)
        _, after = self._get("/health")
        assert after.get("events_today", 0) >= count_before + 1


# ===========================================================================
# Project structure tests
# ===========================================================================


class TestProjectStructure:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_main_py_exists(self):
        assert os.path.exists(os.path.join(self.ROOT, "main.py"))

    def test_tree_py_exists(self):
        assert os.path.exists(os.path.join(self.ROOT, "tree.py"))

    def test_agents_dir_exists(self):
        assert os.path.isdir(os.path.join(self.ROOT, "agents"))

    def test_all_agent_files_present(self):
        agents_dir = os.path.join(self.ROOT, "agents")
        for name in ("github_agent", "linear_agent", "notion_agent", "slack_agent",
                     "stripe_agent", "hubspot_agent", "zapier_agent"):
            assert os.path.exists(os.path.join(agents_dir, f"{name}.py")), f"Missing: {name}.py"

    def test_railway_toml_exists(self):
        assert os.path.exists(os.path.join(self.ROOT, "railway.toml"))

    def test_dockerfile_cmd_is_main(self):
        dockerfile_path = os.path.join(self.ROOT, "Dockerfile")
        with open(dockerfile_path) as f:
            content = f.read()
        assert 'CMD ["python", "main.py"]' in content, "Dockerfile CMD must point to main.py"
        assert "trunk.py" not in content, "Dockerfile must not reference trunk.py"

    def test_requirements_has_requests(self):
        req_path = os.path.join(self.ROOT, "requirements.txt")
        with open(req_path) as f:
            content = f.read()
        assert "requests" in content

    def test_ci_workflow_mentions_railway(self):
        ci_path = os.path.join(self.ROOT, ".github", "workflows", "ci.yml")
        with open(ci_path) as f:
            content = f.read()
        assert "railway" in content.lower()

    def test_deploy_workflow_mentions_railway(self):
        deploy_path = os.path.join(self.ROOT, ".github", "workflows", "deploy.yml")
        with open(deploy_path) as f:
            content = f.read()
        assert "railway" in content.lower()

    def test_main_py_syntax(self):
        import ast
        with open(os.path.join(self.ROOT, "main.py")) as f:
            source = f.read()
        ast.parse(source)  # raises SyntaxError on bad syntax

    def test_tree_py_syntax(self):
        import ast
        with open(os.path.join(self.ROOT, "tree.py")) as f:
            source = f.read()
        ast.parse(source)
