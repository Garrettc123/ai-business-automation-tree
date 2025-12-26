# 🤝 Contributing to AI Business Automation Tree

Thank you for your interest in contributing to the AI Business Automation Tree! This document provides guidelines and instructions for contributing to this project.

## 🌟 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Branch Structure](#branch-structure)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)
- [Community](#community)

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of:
- Experience level
- Background
- Identity
- Location

### Expected Behavior

- ✅ Be respectful and constructive in all communications
- ✅ Welcome newcomers and help them get started
- ✅ Accept constructive criticism gracefully
- ✅ Focus on what's best for the project and community
- ✅ Show empathy towards other community members

### Unacceptable Behavior

- ❌ Harassment, discrimination, or offensive comments
- ❌ Trolling, insulting, or derogatory remarks
- ❌ Personal or political attacks
- ❌ Publishing others' private information
- ❌ Any conduct that could reasonably be considered inappropriate

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment tool (venv, conda, or virtualenv)
- GitHub account

### Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-business-automation-tree.git
cd ai-business-automation-tree

# Add upstream remote
git remote add upstream https://github.com/Garrettc123/ai-business-automation-tree.git
```

### Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install
```

### Verify Installation

```bash
# Run the demo to ensure everything works
python system_demo.py

# Run tests
pytest tests/
```

## 🔄 Development Workflow

### 1. Sync Your Fork

```bash
# Fetch latest changes from upstream
git fetch upstream
git checkout main
git merge upstream/main
```

### 2. Create a Feature Branch

```bash
# Create a descriptive branch name
git checkout -b feature/add-slack-integration
# or
git checkout -b fix/customer-service-timeout
# or
git checkout -b docs/update-api-examples
```

### Branch Naming Convention

- `feature/` - New features or enhancements
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests
- `perf/` - Performance improvements

### 3. Make Your Changes

- Write clean, readable code
- Follow the coding standards (see below)
- Add tests for new functionality
- Update documentation as needed
- Commit frequently with clear messages

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add Slack integration to customer service branch"
```

#### Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, etc.)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks
- `perf` - Performance improvements

**Examples:**
```
feat(sales): add lead scoring algorithm with ML model

Implemented XGBoost model for lead scoring with 92% accuracy.
Includes training pipeline and real-time prediction endpoint.

Closes #123
```

```
fix(customer-service): resolve ticket routing timeout issue

Fixed race condition in parallel ticket processing that caused
timeouts when handling >100 concurrent tickets.

Fixes #456
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/add-slack-integration

# Go to GitHub and create a Pull Request
```

## 🌿 Branch Structure

Our project follows a modular branch architecture. When contributing:

### Adding a New Branch (Department)

```python
# Create new file: branches/new_branch_name.py

import asyncio
from typing import Dict, Any

class NewBranchCoordinator:
    """
    Coordinates [Department Name] automation workflows.
    
    This branch handles:
    - Specific functionality 1
    - Specific functionality 2
    - Specific functionality 3
    """
    
    def __init__(self):
        self.name = "new_branch"
        self.agents = []
        
    async def process_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process workflow for this branch.
        
        Args:
            data: Input data containing workflow parameters
            
        Returns:
            Dict containing results and metrics
        """
        # Implementation here
        pass
```

### Modifying Existing Branches

- Maintain backward compatibility
- Add comprehensive tests
- Update documentation
- Follow existing patterns and conventions

## 📝 Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

```python
# Use 4 spaces for indentation
# Maximum line length: 100 characters
# Use snake_case for functions and variables
# Use PascalCase for classes

# Good example
async def calculate_lead_score(lead_data: Dict[str, Any]) -> float:
    """Calculate lead score using ML model."""
    score = await ml_model.predict(lead_data)
    return round(score, 2)

# Use type hints
def process_data(input_data: List[str]) -> Dict[str, int]:
    """Process input data and return statistics."""
    return {"count": len(input_data)}

# Comprehensive docstrings
class MarketingAgent:
    """
    AI agent for marketing automation tasks.
    
    This agent handles campaign creation, content generation,
    and performance tracking across multiple channels.
    
    Attributes:
        name (str): Agent identifier
        capabilities (List[str]): List of supported operations
        
    Example:
        >>> agent = MarketingAgent()
        >>> result = await agent.create_campaign({"type": "email"})
    """
    pass
```

### Code Quality Tools

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Lint with pylint
pylint branches/ leaves/ roots/

# Type check with mypy
mypy branches/ --strict

# Check security issues
bandit -r .
```

### Best Practices

1. **Async/Await**: Use async functions for I/O operations
2. **Error Handling**: Always use try/except blocks with specific exceptions
3. **Logging**: Use Python's logging module, not print statements
4. **Configuration**: Use config files, not hardcoded values
5. **Dependencies**: Pin versions in requirements.txt

## 🧪 Testing Requirements

### Test Coverage

- Minimum 80% code coverage required
- All new features must include tests
- Bug fixes must include regression tests

### Writing Tests

```python
# tests/branches/test_marketing_branch.py

import pytest
import asyncio
from branches.marketing_branch import MarketingBranchCoordinator

@pytest.fixture
async def marketing_branch():
    """Create marketing branch instance for testing."""
    return MarketingBranchCoordinator()

@pytest.mark.asyncio
async def test_campaign_creation(marketing_branch):
    """Test that campaigns are created successfully."""
    campaign_data = {
        "type": "email",
        "subject": "Test Campaign",
        "target_audience": "customers"
    }
    
    result = await marketing_branch.create_campaign(campaign_data)
    
    assert result["status"] == "success"
    assert "campaign_id" in result
    assert result["channels"] == ["email"]

@pytest.mark.asyncio
async def test_invalid_campaign_type(marketing_branch):
    """Test handling of invalid campaign types."""
    campaign_data = {"type": "invalid_type"}
    
    with pytest.raises(ValueError):
        await marketing_branch.create_campaign(campaign_data)
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/branches/test_marketing_branch.py

# Run with coverage
pytest --cov=branches --cov-report=html

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf
```

## 📚 Documentation

### Code Documentation

- All functions must have docstrings
- Use Google-style docstring format
- Include type hints for all parameters
- Provide usage examples for complex functions

### README Updates

- Update README.md if adding new features
- Add examples for new functionality
- Update performance metrics if relevant
- Include integration instructions

### API Documentation

```python
def process_leads(leads: List[Dict], threshold: float = 0.7) -> List[Dict]:
    """
    Process and score leads using AI model.
    
    Args:
        leads: List of lead dictionaries containing contact information
            and engagement data. Required keys: 'email', 'company', 
            'engagement_score'.
        threshold: Minimum score threshold for qualified leads.
            Must be between 0 and 1. Default is 0.7.
            
    Returns:
        List of qualified leads with added 'ai_score' key,
        sorted by score descending.
        
    Raises:
        ValueError: If leads list is empty or threshold is invalid.
        KeyError: If required keys are missing from lead dictionaries.
        
    Example:
        >>> leads = [
        ...     {"email": "john@example.com", "company": "ACME", 
        ...      "engagement_score": 0.8}
        ... ]
        >>> qualified = process_leads(leads, threshold=0.7)
        >>> print(qualified[0]['ai_score'])
        0.85
        
    Note:
        This function uses a pre-trained XGBoost model. Model must
        be initialized before calling this function.
    """
    pass
```

## 🔀 Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] Tests pass locally (`pytest`)
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with main
- [ ] No merge conflicts

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added and passing
- [ ] No new warnings

## Screenshots (if applicable)

## Related Issues
Closes #123
Related to #456
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and quality checks
2. **Code Review**: Maintainers review code and provide feedback
3. **Revisions**: Address feedback and push updates
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainer will merge when ready

### After Merge

- Your contribution will be credited in release notes
- Branch will be automatically deleted
- Update your fork with latest changes

## 🐛 Reporting Issues

### Before Reporting

- Search existing issues to avoid duplicates
- Verify the issue on the latest version
- Collect relevant information (logs, screenshots, etc.)

### Issue Template

```markdown
**Bug Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Run command '...'
3. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.10.5]
- Project Version: [e.g., 1.2.0]

**Logs/Screenshots**
Include relevant logs or screenshots

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

We welcome feature suggestions! When requesting a feature:

1. **Describe the Problem**: What problem would this solve?
2. **Proposed Solution**: How do you envision this working?
3. **Alternatives**: What alternatives have you considered?
4. **Use Cases**: Provide specific examples of how this would be used
5. **Priority**: Indicate if this is critical or nice-to-have

### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature

**Problem It Solves**
What problem does this address?

**Proposed Implementation**
How should this work?

**Use Cases**
- Use case 1
- Use case 2

**Alternatives Considered**
What other approaches did you think about?

**Additional Context**
Screenshots, mockups, or examples
```

## 🌐 Community

### Communication Channels

- **GitHub Discussions**: General questions and discussions
- **GitHub Issues**: Bug reports and feature requests
- **Pull Requests**: Code contributions and reviews

### Getting Help

- Check existing documentation first
- Search closed issues for similar questions
- Ask in GitHub Discussions for general help
- Tag maintainers only for urgent issues

### Recognition

Contributors are recognized in several ways:

- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Badges for significant contributions
- Opportunity to become a maintainer

## 🎖️ Contribution Levels

### Good First Issues

Look for issues tagged `good first issue` - perfect for newcomers!

### Areas Needing Help

- 📝 Documentation improvements
- 🧪 Test coverage expansion
- 🔌 New integrations (CRM, communication tools)
- 🤖 AI model improvements
- 🐛 Bug fixes
- 🌐 Internationalization

### Becoming a Maintainer

Regular contributors with high-quality submissions may be invited to become maintainers with:
- Commit access to main repository
- Ability to review and merge PRs
- Input on project direction

## 📄 License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers this project.

## 🙏 Thank You!

Every contribution, no matter how small, helps make this project better. We appreciate your time and effort!

---

**Questions?** Open a discussion on GitHub or reach out to maintainers.

**Happy Contributing! 🚀🌳**
