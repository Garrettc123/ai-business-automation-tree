#!/bin/bash
# AI Business Automation Tree - Setup and Deployment Script
# This script automates the setup and deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AI Business Automation Tree Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Docker
echo -e "${YELLOW}Checking Docker installation...${NC}"
if ! command_exists docker; then
    echo -e "${RED}Docker is not installed!${NC}"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"
docker --version
echo ""

# Check for Docker Compose (both old and new syntax)
echo -e "${YELLOW}Checking Docker Compose...${NC}"
if command_exists docker-compose; then
    COMPOSE_CMD="docker-compose"
    echo -e "${GREEN}✓ docker-compose found${NC}"
    docker-compose --version
elif docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    echo -e "${GREEN}✓ docker compose (plugin) found${NC}"
    docker compose version
else
    echo -e "${RED}Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi
echo ""

# Check if .env file exists
echo -e "${YELLOW}Checking environment configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${RED}⚠ WARNING: Please edit .env file and update the following:${NC}"
    echo "  - Database passwords (DB_PASSWORD, REDIS_PASSWORD, MONGO_PASSWORD)"
    echo "  - API keys (OPENAI_API_KEY, etc.)"
    echo "  - JWT_SECRET_KEY and SECRET_KEY"
    echo ""
    read -p "Press Enter to continue after updating .env file, or Ctrl+C to exit..."
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi
echo ""

# Create required directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p logs data models data/uploads data/backups
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Stop any existing containers
echo -e "${YELLOW}Stopping any existing containers...${NC}"
$COMPOSE_CMD down 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned up existing containers${NC}"
echo ""

# Pull latest images
echo -e "${YELLOW}Pulling Docker images...${NC}"
$COMPOSE_CMD pull
echo -e "${GREEN}✓ Images pulled${NC}"
echo ""

# Build application image
echo -e "${YELLOW}Building application image...${NC}"
$COMPOSE_CMD build
echo -e "${GREEN}✓ Application built${NC}"
echo ""

# Start services
echo -e "${YELLOW}Starting services...${NC}"
$COMPOSE_CMD up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check service status
echo -e "${YELLOW}Service Status:${NC}"
$COMPOSE_CMD ps
echo ""

# Display access information
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Access your services:${NC}"
echo "  • Application:     http://localhost:8000"
echo "  • API Docs:        http://localhost:8000/docs"
echo "  • Grafana:         http://localhost:3000 (admin/changeme)"
echo "  • Prometheus:      http://localhost:9090"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  • View logs:       $COMPOSE_CMD logs -f"
echo "  • Stop services:   $COMPOSE_CMD stop"
echo "  • Restart:         $COMPOSE_CMD restart"
echo "  • Stop & remove:   $COMPOSE_CMD down"
echo "  • View status:     $COMPOSE_CMD ps"
echo ""
echo -e "${GREEN}Happy automating! 🚀${NC}"
