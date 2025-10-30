#!/bin/bash
# Final Optimization Setup Script
# Completes the optimization by recreating the virtual environment

set -e

echo "🚀 TQ GenAI Chat - Final Optimization Setup"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found!${NC}"
    echo "Please run this script from the TQ_GenAI_Chat directory"
    exit 1
fi

echo "This script will:"
echo "  1. Deactivate current virtual environment"
echo "  2. Remove old virtual environment"
echo "  3. Create fresh lightweight environment"
echo "  4. Install optimized dependencies"
echo "  5. Verify installation"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "📊 Current state:"
du -sh . 2>/dev/null | awk '{print "   Total project: " $1}'
du -sh .venv 2>/dev/null | awk '{print "   Current venv: " $1}' || true
du -sh fastapi_env 2>/dev/null | awk '{print "   Old fastapi_env: " $1}' || true

# Deactivate if active
if [ -n "$VIRTUAL_ENV" ]; then
    echo ""
    echo "🔄 Deactivating current virtual environment..."
    deactivate 2>/dev/null || true
fi

# Remove old environments
echo ""
echo "🗑️  Removing old virtual environments..."
rm -rf .venv fastapi_env venv ENV env 2>/dev/null || true
echo -e "${GREEN}✅ Old environments removed${NC}"

# Create new environment
echo ""
echo "📦 Creating fresh virtual environment..."
python3.12 -m venv .venv
echo -e "${GREEN}✅ New environment created${NC}"

# Activate environment
echo ""
echo "🔌 Activating new environment..."
source .venv/bin/activate
echo -e "${GREEN}✅ Environment activated${NC}"

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip -q
echo -e "${GREEN}✅ Pip upgraded${NC}"

# Install production dependencies
echo ""
echo "📥 Installing optimized production dependencies..."
echo "   This may take a few minutes..."
pip install -r requirements.txt -q
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Verify installation
echo ""
echo "🔍 Verifying installation..."
INSTALLED_PACKAGES=$(pip list | wc -l)
EXPECTED_PACKAGES=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
echo "   Packages installed: $INSTALLED_PACKAGES"
echo "   Expected packages: ~$EXPECTED_PACKAGES"

# Check final sizes
echo ""
echo "💾 Final sizes:"
du -sh . 2>/dev/null | awk '{print "   Total project: " $1}'
du -sh .venv 2>/dev/null | awk '{print "   New venv: " $1}'

# Cache check
CACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
echo "   Cache directories: $CACHE_COUNT (should be 0)"

echo ""
echo -e "${GREEN}✅ Optimization Complete!${NC}"
echo ""
echo "📋 Next steps:"
echo "   1. Test the application:"
echo "      python main.py"
echo ""
echo "   2. Verify functionality in browser:"
echo "      http://localhost:8000"
echo ""
echo "   3. For development, install dev dependencies:"
echo "      pip install -r requirements-dev.txt"
echo ""
echo "   4. Run tests:"
echo "      pytest tests/"
echo ""
echo -e "${YELLOW}⚠️  Remember to activate the environment in new shells:${NC}"
echo "   source .venv/bin/activate"
echo ""
echo "🎉 Your optimized GenAI Chat is ready!"
