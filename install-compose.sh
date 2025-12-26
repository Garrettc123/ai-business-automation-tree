#!/bin/bash
# Docker Compose Installation Script for Linux
# Automatically installs Docker Compose plugin

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Docker Compose Plugin Installer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        COMPOSE_ARCH="x86_64"
        ;;
    aarch64|arm64)
        COMPOSE_ARCH="aarch64"
        ;;
    armv7l)
        COMPOSE_ARCH="armv7"
        ;;
    *)
        echo -e "${RED}Unsupported architecture: $ARCH${NC}"
        exit 1
        ;;
esac

echo -e "${YELLOW}Detected architecture: $ARCH${NC}"
echo ""

# Create plugin directory
echo -e "${YELLOW}Creating Docker plugin directory...${NC}"
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
echo -e "${GREEN}✓ Plugin directory ready${NC}"
echo ""

# Get latest version
echo -e "${YELLOW}Fetching latest Docker Compose version...${NC}"
LATEST_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST_VERSION" ]; then
    echo -e "${RED}Failed to fetch latest version. Using fallback version v2.24.0${NC}"
    LATEST_VERSION="v2.24.0"
fi

echo -e "${GREEN}Latest version: $LATEST_VERSION${NC}"
echo ""

# Download Docker Compose
echo -e "${YELLOW}Downloading Docker Compose plugin...${NC}"
COMPOSE_URL="https://github.com/docker/compose/releases/download/${LATEST_VERSION}/docker-compose-linux-${COMPOSE_ARCH}"

curl -SL "$COMPOSE_URL" -o $DOCKER_CONFIG/cli-plugins/docker-compose

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to download Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker Compose downloaded${NC}"
echo ""

# Make it executable
echo -e "${YELLOW}Setting permissions...${NC}"
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

# Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"
if docker compose version >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker Compose installed successfully!${NC}"
    echo ""
    docker compose version
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}You can now use Docker Compose with:${NC}"
    echo "  docker compose up -d"
    echo "  docker compose ps"
    echo "  docker compose logs -f"
    echo ""
    echo -e "${YELLOW}Or run the setup script:${NC}"
    echo "  ./setup.sh"
    echo ""
else
    echo -e "${RED}Installation verification failed${NC}"
    echo "Please check your Docker installation and try again."
    exit 1
fi
