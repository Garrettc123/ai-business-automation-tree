#!/usr/bin/env python3
"""
AI Business Automation Tree - Main Orchestrator
Hierarchical system coordinator for multi-branch automation
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Any
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemOrchestrator:
    """Root-level orchestrator managing all automation branches"""
    
    def __init__(self):
        self.branches = {}
        self.status = "healthy"
        self.start_time = datetime.now()
        logger.info("System Orchestrator initialized")
    
    def register_branch(self, name: str, branch_config: Dict[str, Any]):
        """Register a new automation branch"""
        self.branches[name] = {
            "config": branch_config,
            "status": "registered",
            "agents": [],
            "last_execution": None
        }
        logger.info(f"Branch registered: {name}")
    
    async def initialize_branches(self):
        """Initialize all registered branches"""
        tasks = []
        for branch_name in self.branches:
            tasks.append(self._initialize_branch(branch_name))
        
        results = await asyncio.gather(*tasks)
        logger.info(f"Initialized {len(results)} branches")
        return results
    
    async def _initialize_branch(self, branch_name: str):
        """Initialize a single branch"""
        logger.info(f"Initializing branch: {branch_name}")
        self.branches[branch_name]["status"] = "active"
        return {"branch": branch_name, "status": "active"}
    
    async def execute_workflow(self, workflow_name: str, parameters: Dict[str, Any]):
        """Execute a cross-branch workflow"""
        logger.info(f"Executing workflow: {workflow_name}")
        
        # Parallel execution across relevant branches
        results = {}
        for branch_name, branch in self.branches.items():
            if branch["status"] == "active":
                result = await self._execute_branch_task(branch_name, workflow_name, parameters)
                results[branch_name] = result
        
        return {
            "workflow": workflow_name,
            "status": "completed",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_branch_task(self, branch: str, task: str, params: Dict):
        """Execute task in specific branch"""
        await asyncio.sleep(0.1)  # Simulate processing
        return {"status": "success", "processed": True}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        return {
            "status": self.status,
            "uptime_seconds": uptime_seconds,
            "uptime_human": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m",
            "branches_count": len(self.branches),
            "branches": {name: b["status"] for name, b in self.branches.items()},
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }


# Global orchestrator instance
orchestrator = SystemOrchestrator()


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks and basic API"""
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def _send_json_response(self, status_code: int, data: dict):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/health' or path == '/':
            # Health check endpoint
            status = orchestrator.get_system_status()
            self._send_json_response(200, {
                "status": "ok",
                "message": "AI Business Automation Tree is running",
                "system": status
            })
        
        elif path == '/api/status':
            # Detailed status endpoint
            status = orchestrator.get_system_status()
            self._send_json_response(200, status)
        
        elif path == '/api/branches':
            # List all branches
            branches = {
                name: {
                    "status": branch["status"],
                    "type": branch["config"].get("type", "unknown"),
                    "last_execution": branch["last_execution"]
                }
                for name, branch in orchestrator.branches.items()
            }
            self._send_json_response(200, {"branches": branches})
        
        else:
            self._send_json_response(404, {
                "error": "Not Found",
                "path": path,
                "available_endpoints": ["/health", "/api/status", "/api/branches"]
            })
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def run_http_server(port: int = 8000):
    """Run HTTP server for health checks and API"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"HTTP Server started on port {port}")
    logger.info(f"Health check available at: http://localhost:{port}/health")
    logger.info(f"API documentation: http://localhost:{port}/api/status")
    httpd.serve_forever()


async def initialize_system():
    """Initialize the automation system"""
    logger.info("Starting AI Business Automation Tree System")
    
    # Register branches
    orchestrator.register_branch("marketing", {"type": "marketing_automation"})
    orchestrator.register_branch("sales", {"type": "sales_automation"})
    orchestrator.register_branch("operations", {"type": "operations_automation"})
    orchestrator.register_branch("customer_service", {"type": "service_automation"})
    orchestrator.register_branch("analytics", {"type": "analytics_automation"})
    orchestrator.register_branch("hr", {"type": "hr_automation"})
    
    # Initialize all branches
    await orchestrator.initialize_branches()
    
    # Display system status
    status = orchestrator.get_system_status()
    logger.info(f"System Status: {status}")
    
    return orchestrator


def main():
    """Main entry point"""
    # Initialize system in async context
    orchestrator_future = asyncio.run(initialize_system())
    
    # Get port from environment (PORT for Vercel, API_PORT for Docker)
    port = int(os.getenv('PORT', os.getenv('API_PORT', 8000)))
    
    # Run HTTP server in main thread
    try:
        run_http_server(port)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()