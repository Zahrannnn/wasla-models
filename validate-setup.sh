#!/bin/bash

# Wasla AI Agent - Docker Setup Validation Script
# This script checks if your environment is ready for Docker deployment

echo "🔍 Wasla AI Agent - Docker Setup Validation"
echo "=========================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo -n "Checking Docker installation... "
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    echo -e "${GREEN}✓${NC} Found version $DOCKER_VERSION"
else
    echo -e "${RED}✗${NC} Docker not found"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check Docker Compose
echo -n "Checking Docker Compose... "
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    echo -e "${GREEN}✓${NC} Found version $COMPOSE_VERSION"
elif docker-compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose version --short)
    echo -e "${GREEN}✓${NC} Found version $COMPOSE_VERSION"
else
    echo -e "${RED}✗${NC} Docker Compose not found"
    echo "Please install Docker Compose from https://docs.docker.com/compose"
    exit 1
fi

# Check if Docker daemon is running
echo -n "Checking Docker daemon... "
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Running"
else
    echo -e "${RED}✗${NC} Not running"
    echo "Please start Docker Desktop or the Docker daemon"
    exit 1
fi

# Check .env file
echo ""
echo "Checking configuration..."

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠${NC}  .env file not found"
    echo "Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓${NC} Created .env from .env.example"
        echo -e "${YELLOW}⚠${NC}  Please edit .env and set your LLM_API_KEY"
    else
        echo -e "${RED}✗${NC} .env.example not found"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

# Check if API key is set
echo -n "Checking LLM_API_KEY... "
if grep -q "^LLM_API_KEY=sk-" .env || grep -q "^LLM_API_KEY=hf_" .env; then
    echo -e "${GREEN}✓${NC} API key is set"
else
    echo -e "${YELLOW}⚠${NC}  API key not set or invalid"
    echo "Please edit .env and set LLM_API_KEY"
    echo "Get a free key from https://openrouter.ai (recommended) or https://hf.co/settings/tokens"
fi

# Check required files
echo ""
echo "Checking required files..."

REQUIRED_FILES=(
    "Dockerfile"
    "docker-compose.yml"
    "requirements.txt"
    "app/main.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file not found"
        exit 1
    fi
done

# Check docker-compose.yml syntax
echo ""
echo -n "Validating docker-compose.yml... "
if docker compose config &> /dev/null; then
    echo -e "${GREEN}✓${NC} Valid"
else
    echo -e "${RED}✗${NC} Invalid"
    exit 1
fi

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✓ All checks passed!${NC}"
echo ""
echo "You're ready to deploy! Run:"
echo ""
echo "  docker-compose up -d"
echo ""
echo "Then access the API at http://localhost:8000/docs"
echo ""
echo "For more information, see:"
echo "  - QUICKSTART.md - Get running in 5 minutes"
echo "  - DOCKER_SETUP.md - Full deployment guide"
echo ""
