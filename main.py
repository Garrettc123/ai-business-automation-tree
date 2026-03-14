#!/usr/bin/env python3
"""
AI Business Automation Tree — Main entry point.

Hierarchical automation system:
  Root  → MasterOrchestrator
  Branch → GitHub, Linear, Notion, Slack, Stripe, HubSpot, Zapier
  Leaf   → individual task executors

HTTP endpoints:
  GET  /health               — health check
  GET  /api/status           — system status
  GET  /api/tree             — full tree structure as JSON
  GET  /api/workflows        — list recent workflow states
  GET  /api/workflows/<id>   — single workflow state
  POST /webhook              — trigger a tree walk from any external event
  POST /api/trigger          — manually trigger with arbitrary payload
  GET  /dashboard            — HTML dashboard (tree, active automations, events today)
"""

import asyncio
import json
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Build the automation tree
# ---------------------------------------------------------------------------
from tree import RootNode, WorkflowState, traverse
from agents import (
    build_github_branch,
    build_hubspot_branch,
    build_linear_branch,
    build_notion_branch,
    build_slack_branch,
    build_stripe_branch,
    build_zapier_branch,
)


def build_tree() -> RootNode:
    """Construct the full automation tree."""
    root = RootNode(
        name="MasterOrchestrator",
        description="Root orchestrator coordinating all platform agents",
    )
    root.add_child(build_github_branch())
    root.add_child(build_linear_branch())
    root.add_child(build_notion_branch())
    root.add_child(build_slack_branch())
    root.add_child(build_stripe_branch())
    root.add_child(build_hubspot_branch())
    root.add_child(build_zapier_branch())
    return root


# Singleton tree and shared state
_tree = build_tree()
_workflows: Dict[str, WorkflowState] = {}          # workflow_id → state (capped at 1000)
_MAX_WORKFLOWS = 1000
_events_today: int = 0                              # counter, reset at midnight
_events_today_date: str = ""                        # YYYY-MM-DD of last reset
_lock = threading.Lock()


def _get_events_today() -> int:
    global _events_today, _events_today_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _lock:
        if _events_today_date != today:
            _events_today = 0
            _events_today_date = today
        return _events_today


def _increment_events() -> None:
    global _events_today, _events_today_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _lock:
        if _events_today_date != today:
            _events_today = 0
            _events_today_date = today
        _events_today += 1


# ---------------------------------------------------------------------------
# Async tree walk — run in a background thread pool
# ---------------------------------------------------------------------------

def _run_tree_walk(event_payload: Dict[str, Any]) -> str:
    """Kick off an async tree walk and return the workflow_id immediately."""
    state = WorkflowState(trigger_event=event_payload)
    with _lock:
        _workflows[state.workflow_id] = state
        # Evict oldest entries when we exceed the cap
        if len(_workflows) > _MAX_WORKFLOWS:
            oldest_keys = list(_workflows.keys())[:len(_workflows) - _MAX_WORKFLOWS]
            for key in oldest_keys:
                del _workflows[key]
    _increment_events()

    async def _walk():
        await _tree.execute(state)

    def _thread():
        asyncio.run(_walk())

    t = threading.Thread(target=_thread, daemon=True)
    t.start()
    return state.workflow_id


# ---------------------------------------------------------------------------
# HTML dashboard
# ---------------------------------------------------------------------------

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Business Automation Tree — Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  header {{ background: #1e293b; padding: 1rem 2rem; border-bottom: 1px solid #334155;
            display: flex; align-items: center; gap: 1rem; }}
  header h1 {{ font-size: 1.25rem; font-weight: 700; color: #38bdf8; }}
  header .badge {{ background: #22c55e; color: #fff; border-radius: 9999px;
                   padding: .2rem .7rem; font-size: .75rem; font-weight: 600; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
           gap: 1rem; padding: 1.5rem 2rem; }}
  .card {{ background: #1e293b; border-radius: .75rem; padding: 1.25rem;
           border: 1px solid #334155; }}
  .card .label {{ font-size: .75rem; color: #94a3b8; text-transform: uppercase;
                  letter-spacing: .05em; margin-bottom: .5rem; }}
  .card .value {{ font-size: 2rem; font-weight: 700; color: #38bdf8; }}
  .card .sub {{ font-size: .8rem; color: #64748b; margin-top: .25rem; }}
  section {{ padding: 0 2rem 2rem; }}
  section h2 {{ font-size: 1rem; font-weight: 600; color: #94a3b8; margin-bottom: 1rem;
                text-transform: uppercase; letter-spacing: .05em; }}
  .tree-wrap {{ background: #1e293b; border-radius: .75rem; padding: 1.25rem;
                border: 1px solid #334155; overflow-x: auto; }}
  .tree-node {{ display: flex; align-items: center; gap: .5rem; padding: .3rem 0; }}
  .tree-node .indent {{ display: inline-block; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
  .dot-root {{ background: #f59e0b; }}
  .dot-branch {{ background: #38bdf8; }}
  .dot-leaf {{ background: #22c55e; }}
  .node-name {{ font-weight: 600; font-size: .9rem; }}
  .node-meta {{ font-size: .75rem; color: #64748b; }}
  .node-status {{ font-size: .7rem; padding: .15rem .5rem; border-radius: 9999px;
                  background: #334155; color: #94a3b8; }}
  .status-success {{ background: #14532d; color: #86efac; }}
  .status-failed {{ background: #7f1d1d; color: #fca5a5; }}
  .status-running {{ background: #1e3a5f; color: #7dd3fc; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
  th {{ text-align: left; padding: .5rem .75rem; background: #0f172a;
        color: #64748b; font-weight: 500; border-bottom: 1px solid #334155; }}
  td {{ padding: .6rem .75rem; border-bottom: 1px solid #1e293b; }}
  tr:hover td {{ background: #1e293b55; }}
  .pill {{ display: inline-block; padding: .15rem .55rem; border-radius: 9999px;
           font-size: .72rem; font-weight: 600; }}
  .pill-completed {{ background: #14532d; color: #86efac; }}
  .pill-running  {{ background: #1e3a5f; color: #7dd3fc; }}
  .pill-partial  {{ background: #78350f; color: #fcd34d; }}
  .pill-error    {{ background: #7f1d1d; color: #fca5a5; }}
  #refresh {{ background: #334155; border: none; color: #e2e8f0; padding: .4rem .9rem;
              border-radius: .4rem; cursor: pointer; font-size: .8rem; margin-left: auto; }}
  #refresh:hover {{ background: #475569; }}
</style>
</head>
<body>
<header>
  <h1>🌳 AI Business Automation Tree</h1>
  <span class="badge" id="health-badge">Loading…</span>
  <button id="refresh" onclick="loadAll()">↺ Refresh</button>
</header>

<div class="grid">
  <div class="card">
    <div class="label">Branch nodes</div>
    <div class="value" id="stat-branches">—</div>
    <div class="sub">Platform agents</div>
  </div>
  <div class="card">
    <div class="label">Total leaf tasks</div>
    <div class="value" id="stat-leaves">—</div>
    <div class="sub">Individual executors</div>
  </div>
  <div class="card">
    <div class="label">Workflows today</div>
    <div class="value" id="stat-events">—</div>
    <div class="sub">Events processed</div>
  </div>
  <div class="card">
    <div class="label">Active workflows</div>
    <div class="value" id="stat-active">—</div>
    <div class="sub">Currently running</div>
  </div>
</div>

<section>
  <h2>Tree Structure</h2>
  <div class="tree-wrap" id="tree-container">Loading…</div>
</section>

<section>
  <h2>Recent Automation Runs</h2>
  <div style="background:#1e293b; border-radius:.75rem; border:1px solid #334155; overflow:hidden;">
    <table>
      <thead>
        <tr>
          <th>Workflow ID</th>
          <th>Status</th>
          <th>Trigger</th>
          <th>Started</th>
          <th>Updated</th>
        </tr>
      </thead>
      <tbody id="workflows-body"><tr><td colspan="5" style="color:#64748b">Loading…</td></tr></tbody>
    </table>
  </div>
</section>

<script>
async function loadAll() {
  try {
    const [status, tree, workflows] = await Promise.all([
      fetch('/api/status').then(r => r.json()),
      fetch('/api/tree').then(r => r.json()),
      fetch('/api/workflows').then(r => r.json()),
    ]);

    // Health badge
    const badge = document.getElementById('health-badge');
    badge.textContent = status.status || 'ok';
    badge.style.background = status.status === 'healthy' ? '#22c55e' : '#ef4444';

    // Stats
    document.getElementById('stat-events').textContent = status.events_today ?? '—';
    document.getElementById('stat-active').textContent = workflows.filter(w => w.status === 'running').length;

    // Tree
    const nodes = tree.nodes || [];
    let branches = 0, leaves = 0;
    const html = nodes.map(n => {
      const indent = '&nbsp;&nbsp;&nbsp;&nbsp;'.repeat(n.depth);
      const dotClass = n.type === 'root' ? 'dot-root' : n.type === 'branch' ? 'dot-branch' : 'dot-leaf';
      if (n.type === 'branch') branches++;
      if (n.type === 'leaf') leaves++;
      const statusClass = n.status === 'success' ? 'status-success' : n.status === 'failed' ? 'status-failed' : n.status === 'running' ? 'status-running' : '';
      return `<div class="tree-node">
        <span class="indent">${indent}</span>
        <span class="dot ${dotClass}"></span>
        <span class="node-name">${n.name}</span>
        <span class="node-meta">(${n.type}${n.children_count > 0 ? ' · ' + n.children_count + ' children' : ''})</span>
        <span class="node-status ${statusClass}">${n.status}</span>
        ${n.executions > 0 ? '<span class="node-meta">· ' + n.executions + ' runs</span>' : ''}
      </div>`;
    }).join('');
    document.getElementById('tree-container').innerHTML = html || '<em>No tree data</em>';
    document.getElementById('stat-branches').textContent = branches;
    document.getElementById('stat-leaves').textContent = leaves;

    // Workflows table
    const tbody = document.getElementById('workflows-body');
    if (!workflows.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="color:#64748b">No workflows run yet. POST to /webhook to trigger one.</td></tr>';
      return;
    }
    tbody.innerHTML = workflows.slice().reverse().slice(0, 50).map(w => {
      const pillClass = 'pill pill-' + (w.status || 'running');
      const trigger = JSON.stringify(w.trigger_event || {}).slice(0, 60);
      return `<tr>
        <td><code style="font-size:.78rem;color:#7dd3fc">${w.workflow_id.slice(0,8)}…</code></td>
        <td><span class="${pillClass}">${w.status}</span></td>
        <td style="color:#94a3b8;font-size:.78rem">${trigger}</td>
        <td style="color:#64748b;font-size:.78rem">${w.created_at}</td>
        <td style="color:#64748b;font-size:.78rem">${w.updated_at}</td>
      </tr>`;
    }).join('');
  } catch(e) {
    console.error(e);
  }
}
loadAll();
setInterval(loadAll, 10000);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------


class AutomationHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: A002
        logger.info("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, status_code: int, data: Any) -> None:
        body = json.dumps(data, default=str).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path in ("/health", "/"):
            self._send_json(200, {
                "status": "healthy",
                "message": "AI Business Automation Tree is running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events_today": _get_events_today(),
            })

        elif path == "/api/status":
            nodes = traverse(_tree)
            branches = [n for n in nodes if n["type"] == "branch"]
            leaves = [n for n in nodes if n["type"] == "leaf"]
            active = [w for w in _workflows.values() if w.status == "running"]
            self._send_json(200, {
                "status": "healthy",
                "version": "2.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tree": {
                    "total_nodes": len(nodes),
                    "branches": len(branches),
                    "leaves": len(leaves),
                },
                "workflows": {
                    "total": len(_workflows),
                    "active": len(active),
                },
                "events_today": _get_events_today(),
            })

        elif path == "/api/tree":
            nodes = traverse(_tree)
            self._send_json(200, {"nodes": nodes, "total": len(nodes)})

        elif path == "/api/workflows":
            result = [w.to_dict() for w in list(_workflows.values())[-100:]]
            self._send_json(200, result)

        elif path.startswith("/api/workflows/"):
            wid = path.split("/api/workflows/")[-1]
            state = _workflows.get(wid)
            if state:
                self._send_json(200, state.to_dict())
            else:
                self._send_json(404, {"error": "Workflow not found", "workflow_id": wid})

        elif path == "/dashboard":
            self._send_html(_DASHBOARD_HTML)

        else:
            self._send_json(404, {
                "error": "Not Found",
                "path": path,
                "available_endpoints": [
                    "GET  /health",
                    "GET  /api/status",
                    "GET  /api/tree",
                    "GET  /api/workflows",
                    "GET  /api/workflows/<id>",
                    "POST /webhook",
                    "POST /api/trigger",
                    "GET  /dashboard",
                ],
            })

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        payload = self._read_body() or {}

        if path in ("/webhook", "/api/trigger"):
            # Any external event can trigger a full tree walk
            workflow_id = _run_tree_walk(payload)
            logger.info("Tree walk triggered: workflow_id=%s", workflow_id)
            self._send_json(202, {
                "status": "accepted",
                "workflow_id": workflow_id,
                "message": "Tree walk started asynchronously",
            })
        else:
            self._send_json(404, {"error": "Not Found", "path": path})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


def run_server(port: int = 8000) -> None:
    server = HTTPServer(("", port), AutomationHandler)
    logger.info("AI Business Automation Tree server started on port %d", port)
    logger.info("Health:    http://localhost:%d/health", port)
    logger.info("Dashboard: http://localhost:%d/dashboard", port)
    logger.info("API tree:  http://localhost:%d/api/tree", port)
    logger.info("Webhook:   POST http://localhost:%d/webhook", port)
    server.serve_forever()


def main() -> None:
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    try:
        run_server(port)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully…")
    except Exception as exc:
        logger.error("Server error: %s", exc)
        raise


if __name__ == "__main__":
    main()
