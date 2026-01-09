#!/bin/bash
# Deployment Verification Script
# This script validates that all deployment configurations are correct

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Configuration Verification${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Track overall status
ALL_CHECKS_PASSED=true

# Function to report check status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ALL_CHECKS_PASSED=false
    fi
}

# Check 1: Python syntax
echo "Checking Python syntax..."
python -m py_compile main.py 2>/dev/null
check_status $? "main.py syntax is valid"

# Check 2: Docker Compose configuration
echo "Validating docker-compose.yml..."
if docker compose config --quiet 2>&1 | grep -q "error"; then
    RESULT=1
else
    RESULT=0
fi
check_status $RESULT "docker-compose.yml is valid"

# Check 3: Nginx configuration syntax (basic check)
echo "Validating nginx.conf..."
if grep -q "http {" nginx.conf && grep -q "server {" nginx.conf; then
    echo -e "${GREEN}✓${NC} nginx.conf structure looks valid"
else
    echo -e "${RED}✗${NC} nginx.conf structure is invalid"
    ALL_CHECKS_PASSED=false
fi

# Check 4: Required files exist
echo "Checking required files..."
REQUIRED_FILES=(
    "docker-compose.yml"
    "Dockerfile"
    "nginx.conf"
    "prometheus.yml"
    "requirements.txt"
    ".env.example"
    "main.py"
    "setup.sh"
    "grafana/datasources/datasources.yml"
    "grafana/dashboards/dashboards.yml"
    "init-scripts/01-init-schema.sql"
)

FILES_MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo -e "${RED}✗${NC} $file is missing"
        FILES_MISSING=$((FILES_MISSING + 1))
    fi
done
if [ $FILES_MISSING -eq 0 ]; then
    check_status 0 "All required files exist"
else
    check_status 1 "All required files exist"
fi

# Check 5: Environment file
echo "Checking environment configuration..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
else
    echo -e "${YELLOW}⚠${NC} .env file does not exist (will be created from .env.example)"
fi

# Check 6: Required directories
echo "Checking required directories..."
REQUIRED_DIRS=(
    "grafana/datasources"
    "grafana/dashboards"
    "init-scripts"
)

DIRS_MISSING=0
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $dir/ exists"
    else
        echo -e "${RED}✗${NC} $dir/ is missing"
        DIRS_MISSING=$((DIRS_MISSING + 1))
    fi
done
if [ $DIRS_MISSING -eq 0 ]; then
    check_status 0 "All required directories exist"
else
    check_status 1 "All required directories exist"
fi

# Check 7: Scripts are executable
echo "Checking script permissions..."
SCRIPTS=("setup.sh" "deploy-to-cloud.sh")
for script in "${SCRIPTS[@]}"; do
    if [ -x "$script" ]; then
        echo -e "${GREEN}✓${NC} $script is executable"
    else
        echo -e "${YELLOW}⚠${NC} $script is not executable (fixing...)"
        chmod +x "$script"
    fi
done

# Check 8: Health endpoint test
echo "Testing health endpoint (if server is running)..."
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Health endpoint is responding"
else
    echo -e "${YELLOW}⚠${NC} Health endpoint not available (server may not be running)"
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}All critical checks passed!${NC}"
    echo -e "${GREEN}✓ Deployment configuration is ready${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed!${NC}"
    echo -e "${YELLOW}Please fix the issues above before deploying${NC}"
    exit 1
fi
