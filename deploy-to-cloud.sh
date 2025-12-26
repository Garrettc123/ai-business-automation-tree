#!/bin/bash
# Deploy to Remote Server Script
# Use this to deploy from Termux/Android to a remote Linux server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Remote Server Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if SSH is available
if ! command -v ssh >/dev/null 2>&1; then
    echo -e "${RED}SSH is not installed!${NC}"
    echo "Install it with: pkg install openssh"
    exit 1
fi

echo -e "${YELLOW}This script will deploy to a remote server.${NC}"
echo ""

# Get server details
read -p "Enter remote server IP or hostname: " SERVER_HOST
read -p "Enter SSH username (default: root): " SERVER_USER
SERVER_USER=${SERVER_USER:-root}
read -p "Enter SSH port (default: 22): " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-22}

echo ""
echo -e "${YELLOW}Testing SSH connection...${NC}"
ssh -p $SERVER_PORT -o ConnectTimeout=10 $SERVER_USER@$SERVER_HOST "echo 'Connection successful!'"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to connect to server${NC}"
    exit 1
fi

echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Copy files to server
echo -e "${YELLOW}Copying files to remote server...${NC}"
scp -P $SERVER_PORT -r . $SERVER_USER@$SERVER_HOST:~/ai-business-automation-tree/

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to copy files${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Files copied${NC}"
echo ""

# Execute deployment on remote server
echo -e "${YELLOW}Deploying on remote server...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd ~/ai-business-automation-tree

# Install Docker if not present
if ! command -v docker >/dev/null 2>&1; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
fi

# Install Docker Compose plugin
if ! docker compose version >/dev/null 2>&1; then
    echo "Installing Docker Compose..."
    mkdir -p ~/.docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
    chmod +x ~/.docker/cli-plugins/docker-compose
fi

# Make scripts executable
chmod +x *.sh

# Run setup
./setup.sh

ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Access your application:${NC}"
    echo "  http://$SERVER_HOST:8000"
    echo ""
    echo -e "${YELLOW}SSH into server:${NC}"
    echo "  ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST"
    echo ""
    echo -e "${YELLOW}View logs remotely:${NC}"
    echo "  ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST 'cd ~/ai-business-automation-tree && docker compose logs -f'"
else
    echo -e "${RED}Deployment failed${NC}"
    exit 1
fi
