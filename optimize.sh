#!/bin/bash
set -e

echo "🚀 TQ GenAI Chat Optimization Script"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Confirm before proceeding
echo -e "${YELLOW}This script will:${NC}"
echo "  1. Clean __pycache__ directories and .pyc files"
echo "  2. Remove deprecated directories (trash2review)"
echo "  3. Analyze dependencies"
echo "  4. Update .gitignore"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Store initial size
INITIAL_SIZE=$(du -sb . 2>/dev/null | awk '{print $1}')

# Clean caches
echo ""
echo "🧹 Cleaning cache files..."
CACHE_DIRS=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC_FILES=$(find . -name "*.pyc" 2>/dev/null | wc -l)
echo "   Found: $CACHE_DIRS __pycache__ directories, $PYC_FILES .pyc files"

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null
echo -e "${GREEN}✅ Cache cleaned${NC}"

# Remove trash directories
echo ""
echo "🗑️  Removing deprecated directories..."
if [ -d "trash2review" ]; then
    rm -rf trash2review/
    echo "   Removed: trash2review/"
fi
if [ -d "services/trash2review" ]; then
    rm -rf services/trash2review/
    echo "   Removed: services/trash2review/"
fi
echo -e "${GREEN}✅ Deprecated directories removed${NC}"

# Update .gitignore
echo ""
echo "📝 Updating .gitignore..."
if ! grep -q "__pycache__" .gitignore 2>/dev/null; then
    cat >> .gitignore << 'EOF'

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# Virtual environments
.env
.venv
venv/
fastapi_env/
ENV/
env/

# Database
*.db
*.sqlite
*.sqlite3

# Uploads and temporary files
uploads/*
!uploads/.gitkeep
saved_chats/*
!saved_chats/.gitkeep
exports/*
!exports/.gitkeep

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOF
    echo -e "${GREEN}✅ .gitignore updated${NC}"
else
    echo "   .gitignore already contains Python cache patterns"
fi

# Analyze dependencies
echo ""
echo "📦 Analyzing dependencies..."
if [ -f "requirements.txt" ]; then
    TOTAL_DEPS=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
    echo "   Total dependencies in requirements.txt: $TOTAL_DEPS"
    
    # Check for heavy/optional dependencies
    echo ""
    echo "   Potentially removable dependencies (optional/dev-only):"
    for dep in "selenium" "webdriver-manager" "pytesseract" "pdf2image" "pyttsx3" "gunicorn" "black" "isort" "mypy"; do
        if grep -qi "^$dep" requirements.txt; then
            echo -e "   ${YELLOW}⚠️  $dep${NC} (consider moving to requirements-dev.txt)"
        fi
    done
fi

# Check virtual environment
echo ""
echo "🔍 Checking virtual environments..."
for venv_dir in "fastapi_env" ".venv" "venv"; do
    if [ -d "$venv_dir" ]; then
        VENV_SIZE=$(du -sh "$venv_dir" 2>/dev/null | awk '{print $1}')
        echo "   Found: $venv_dir ($VENV_SIZE)"
    fi
done

# Calculate savings
echo ""
FINAL_SIZE=$(du -sb . 2>/dev/null | awk '{print $1}')
SAVED=$((INITIAL_SIZE - FINAL_SIZE))
SAVED_MB=$((SAVED / 1024 / 1024))
INITIAL_MB=$((INITIAL_SIZE / 1024 / 1024))
FINAL_MB=$((FINAL_SIZE / 1024 / 1024))

echo "💾 Disk Space Analysis:"
echo "   Before: ${INITIAL_MB}MB"
echo "   After:  ${FINAL_MB}MB"
if [ $SAVED_MB -gt 0 ]; then
    echo -e "   ${GREEN}Saved:  ${SAVED_MB}MB${NC}"
else
    echo "   Saved:  ~0MB (cache may rebuild)"
fi

echo ""
echo -e "${GREEN}✅ Phase 1 Optimization Complete!${NC}"
echo ""
echo "📋 Next steps:"
echo "   1. Review OPTIMIZATION_RECOMMENDATIONS.md for detailed guide"
echo "   2. Create requirements-prod.txt and requirements-dev.txt"
echo "   3. Consider recreating virtual environment:"
echo "      rm -rf fastapi_env && python3 -m venv .venv"
echo "   4. Install optimized dependencies:"
echo "      source .venv/bin/activate && pip install -r requirements-prod.txt"
echo "   5. Test the application:"
echo "      python main.py"
echo ""
echo -e "${YELLOW}⚠️  Remember to backup important data before major changes!${NC}"
