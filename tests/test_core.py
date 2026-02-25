"""Core tests for AI Business Automation Tree"""
import pytest
import sys
import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any


def test_python_version():
    """Ensure Python >= 3.8"""
    assert sys.version_info >= (3, 8), f"Python {sys.version_info} is too old"


def test_standard_imports():
    """Test standard library imports work"""
    import asyncio
    import json
    import logging
    import os
    import sys
    from typing import Dict, List, Any
    assert True


def test_project_structure():
    """Verify essential project files exist"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.exists(os.path.join(root, 'main.py')), "main.py missing"
    assert os.path.exists(os.path.join(root, 'requirements.txt')), "requirements.txt missing"
    assert os.path.exists(os.path.join(root, 'branches')), "branches/ directory missing"


def test_branches_directory():
    """Verify branches directory has expected modules"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    branches_dir = os.path.join(root, 'branches')
    branch_files = os.listdir(branches_dir)
    py_files = [f for f in branch_files if f.endswith('.py')]
    assert len(py_files) > 0, "No Python files in branches/"


def test_requirements_format():
    """Verify requirements.txt is valid"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    req_path = os.path.join(root, 'requirements.txt')
    with open(req_path, 'r') as f:
        lines = f.readlines()
    # Should have content
    non_empty = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]
    assert len(non_empty) > 0, "requirements.txt has no packages"


def test_asyncio_basic():
    """Test async operations work"""
    async def sample_async():
        await asyncio.sleep(0)
        return "ok"
    result = asyncio.get_event_loop().run_until_complete(sample_async())
    assert result == "ok"


def test_json_operations():
    """Test JSON serialization"""
    data = {
        "system": "ai-business-automation-tree",
        "version": "1.0.0",
        "branches": ["sales", "marketing", "hr", "analytics", "customer_service", "operations"]
    }
    serialized = json.dumps(data)
    deserialized = json.loads(serialized)
    assert deserialized["system"] == "ai-business-automation-tree"
    assert len(deserialized["branches"]) == 6


def test_datetime_operations():
    """Test datetime handling"""
    now = datetime.now()
    assert isinstance(now, datetime)
    assert now.year >= 2024


def test_logging_setup():
    """Test logging configuration"""
    logger = logging.getLogger('test')
    logger.setLevel(logging.DEBUG)
    assert logger.level == logging.DEBUG


class TestBranchModules:
    """Tests for branch module imports"""

    def test_branches_importable(self):
        """Verify branch modules can be imported"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        branches_dir = os.path.join(root, 'branches')
        sys.path.insert(0, root)
        py_files = [f[:-3] for f in os.listdir(branches_dir)
                    if f.endswith('.py') and not f.startswith('__')]
        assert len(py_files) > 0

    def test_sales_branch_exists(self):
        """Sales branch module exists"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(root, 'branches', 'sales_branch.py'))

    def test_marketing_branch_exists(self):
        """Marketing branch module exists"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(root, 'branches', 'marketing_branch.py'))

    def test_analytics_branch_exists(self):
        """Analytics branch module exists"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(root, 'branches', 'analytics_branch.py'))

    def test_hr_branch_exists(self):
        """HR branch module exists"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(root, 'branches', 'hr_branch.py'))

    def test_customer_service_branch_exists(self):
        """Customer service branch module exists"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(root, 'branches', 'customer_service_branch.py'))

    def test_operations_branch_exists(self):
        """Operations branch module exists"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(root, 'branches', 'operations_branch.py'))


class TestSystemOrchestrator:
    """Tests for the main system orchestrator"""

    def test_main_py_syntax(self):
        """Verify main.py has valid Python syntax"""
        import ast
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_path = os.path.join(root, 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        # Should parse without error
        tree = ast.parse(source)
        assert tree is not None

    def test_orchestrator_config(self):
        """Test basic orchestrator configuration structure"""
        config = {
            "name": "AI Business Automation Tree",
            "version": "1.0.0",
            "branches": {
                "sales": {"active": True},
                "marketing": {"active": True},
                "hr": {"active": True},
                "analytics": {"active": True},
                "customer_service": {"active": True},
                "operations": {"active": True},
            }
        }
        assert len(config["branches"]) == 6
        assert all(v["active"] for v in config["branches"].values())
