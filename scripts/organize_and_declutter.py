#!/usr/bin/env python3
"""
Project Organization and Decluttering Script

This script optimizes the project for SPEED and PERFORMANCE by:
1. Moving deprecated, obsolete files to ./trash2review
2. Moving all summary/documentation files to ./trash2review
3. Cleaning up cache files and temporary data
4. Organizing the project structure for optimal performance
"""

import shutil
from datetime import datetime
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
TRASH_DIR = PROJECT_ROOT / "trash2review"

# Files and patterns to move to trash2review
DEPRECATED_FILES = [
    # Refactor and implementation summaries
    "COMPREHENSIVE_REFACTOR_PLAN.md",
    "IMPLEMENTATION_COMPLETE.md",
    "OPTIMIZATION_SUMMARY.md",
    "PHASE2_COMPLETE.md",
    "PROVIDERS_MODERNIZATION.md",
    "QUICK_START_GUIDE.md",
    "REFACTORING_IMPLEMENTATION.md",
    "REFACTOR_PLAN.md",
    "REFACTOR_README.md",
    "REFACTOR_SUMMARY.md",
    "CHANGELOG.md",
    "DOCUMENTATION.md",

    # Deprecated app files
    "app_integration.py",
    "app_refactored.py",
    "ai_models.py",
    "persona.py",

    # Test and utility files
    "test_audio_features.py",
    "test_integration.py",
    "deploy.py",
    "setup.py",

    # Cache and temporary files
    "defaults_cache.json",
    "models_cache.json",
    "documents.db",
    "app.log",
    "dependency_report.md",
    "idea.md",
    "modify.md",

    # Lock files (can be regenerated)
    "uv.lock",
]

# Directories to move to trash2review
DEPRECATED_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".cache_ggshield",
    "refactor_backup",
    "exports",
    "saved_chats",
    "uploads",
    "docs",
]

# Cache patterns to clean
CACHE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "__pycache__",
    ".pytest_cache",
    "*.log",
    "*.tmp",
    "*.cache",
]

def create_trash_structure():
    """Create organized trash directory structure"""
    TRASH_DIR.mkdir(exist_ok=True)

    # Create subdirectories for organization
    subdirs = [
        "deprecated_files",
        "documentation",
        "summaries",
        "cache_files",
        "test_files",
        "old_apps",
        "utilities"
    ]

    for subdir in subdirs:
        (TRASH_DIR / subdir).mkdir(exist_ok=True)

def move_file_safely(src_path, dest_dir, category="deprecated_files"):
    """Move file to trash with safety checks"""
    if not src_path.exists():
        return False

    dest_path = TRASH_DIR / category / src_path.name

    # Handle name conflicts
    counter = 1
    original_dest = dest_path
    while dest_path.exists():
        stem = original_dest.stem
        suffix = original_dest.suffix
        dest_path = original_dest.parent / f"{stem}_{counter}{suffix}"
        counter += 1

    try:
        if src_path.is_dir():
            shutil.move(str(src_path), str(dest_path))
        else:
            shutil.move(str(src_path), str(dest_path))
        print(f"✅ Moved: {src_path.name} → trash2review/{category}/")
        return True
    except Exception as e:
        print(f"❌ Failed to move {src_path.name}: {e}")
        return False

def categorize_and_move_files():
    """Move files to appropriate trash categories"""
    moved_count = 0

    # Move deprecated files by category
    file_categories = {
        "summaries": [
            "COMPREHENSIVE_REFACTOR_PLAN.md",
            "IMPLEMENTATION_COMPLETE.md",
            "OPTIMIZATION_SUMMARY.md",
            "PHASE2_COMPLETE.md",
            "REFACTORING_IMPLEMENTATION.md",
            "REFACTOR_PLAN.md",
            "REFACTOR_SUMMARY.md",
        ],
        "documentation": [
            "PROVIDERS_MODERNIZATION.md",
            "QUICK_START_GUIDE.md",
            "REFACTOR_README.md",
            "CHANGELOG.md",
            "DOCUMENTATION.md",
            "dependency_report.md",
        ],
        "old_apps": [
            "app_integration.py",
            "app_refactored.py",
            "ai_models.py",
            "persona.py",
        ],
        "test_files": [
            "test_audio_features.py",
            "test_integration.py",
        ],
        "utilities": [
            "deploy.py",
            "setup.py",
            "idea.md",
            "modify.md",
        ],
        "cache_files": [
            "defaults_cache.json",
            "models_cache.json",
            "documents.db",
            "app.log",
            "uv.lock",
        ]
    }

    # Move files by category
    for category, files in file_categories.items():
        for filename in files:
            file_path = PROJECT_ROOT / filename
            if move_file_safely(file_path, TRASH_DIR / category, category):
                moved_count += 1

    # Move deprecated directories
    for dirname in DEPRECATED_DIRS:
        dir_path = PROJECT_ROOT / dirname
        if dir_path.exists() and dir_path.is_dir():
            if move_file_safely(dir_path, TRASH_DIR / "cache_files", "cache_files"):
                moved_count += 1

    return moved_count

def clean_remaining_cache():
    """Clean any remaining cache files"""
    cleaned_count = 0

    # Find and remove cache files
    for pattern in CACHE_PATTERNS:
        for cache_file in PROJECT_ROOT.rglob(pattern):
            if cache_file.exists() and "trash2review" not in str(cache_file):
                try:
                    if cache_file.is_dir():
                        shutil.rmtree(cache_file)
                    else:
                        cache_file.unlink()
                    print(f"🧹 Cleaned: {cache_file.relative_to(PROJECT_ROOT)}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"⚠️  Could not clean {cache_file.name}: {e}")

    return cleaned_count

def optimize_project_structure():
    """Optimize remaining project structure for performance"""
    print("\n🚀 Optimizing project structure for SPEED and PERFORMANCE...")

    # Ensure core directories exist and are organized
    core_dirs = [
        "core",
        "config",
        "services",
        "templates",
        "static",
        "scripts",
    ]

    for dirname in core_dirs:
        dir_path = PROJECT_ROOT / dirname
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"📁 Created: {dirname}/")

    # Create performance-optimized .gitignore if needed
    gitignore_path = PROJECT_ROOT / ".gitignore"
    performance_ignores = [
        "# Performance optimization",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".pytest_cache/",
        ".ruff_cache/",
        "*.log",
        "*.tmp",
        "documents.db",
        "models_cache.json",
        "defaults_cache.json",
        "uv.lock",
        "trash2review/",
    ]

    if gitignore_path.exists():
        with open(gitignore_path, 'a') as f:
            f.write("\n" + "\n".join(performance_ignores) + "\n")
        print("📝 Updated .gitignore for performance")

def create_cleanup_summary():
    """Create summary of cleanup actions"""
    summary_path = TRASH_DIR / "CLEANUP_SUMMARY.md"

    summary_content = f"""# Project Cleanup Summary

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Action:** Organized and decluttered project for SPEED and PERFORMANCE

## Files Moved to trash2review/

### 📋 Summaries and Documentation
- All refactor summaries and implementation notes
- Comprehensive documentation files
- Change logs and phase completion reports

### 🗂️ Deprecated Application Files
- Old app versions (app_refactored.py, app_integration.py)
- Deprecated model files (ai_models.py)
- Legacy persona configurations

### 🧪 Test and Utility Files
- Standalone test scripts
- Deployment utilities
- Development notes and ideas

### 💾 Cache and Temporary Files
- JSON cache files
- Database files
- Log files
- Lock files

## Project Structure Optimized

The project is now optimized for:
- ⚡ **SPEED**: Removed unnecessary files and cache
- 🚀 **PERFORMANCE**: Clean directory structure
- 🧹 **MAINTAINABILITY**: Organized core modules only
- 📦 **DEPLOYMENT**: Minimal file footprint

## Core Files Remaining

```
TQ_GenAI_Chat/
├── app.py                 # Main application
├── core/                  # Core business logic
├── config/                # Configuration
├── services/              # Service layer
├── templates/             # HTML templates
├── static/                # CSS/JS assets
├── scripts/               # Utility scripts
├── requirements.txt       # Dependencies
├── pyproject.toml         # Project config
└── README.md              # Main documentation
```

## Next Steps

1. **Review trash2review/** - Verify nothing important was moved
2. **Test application** - Ensure all functionality works
3. **Deploy optimized version** - Enjoy improved performance
4. **Delete trash2review/** - After confirming everything works (optional)

---
*Generated by organize_and_declutter.py*
"""

    with open(summary_path, 'w') as f:
        f.write(summary_content)

    print(f"📄 Created cleanup summary: {summary_path}")

def main():
    """Main cleanup execution"""
    print("🧹 Starting project organization and decluttering...")
    print("🎯 Goal: Optimize for SPEED and PERFORMANCE\n")

    # Create trash directory structure
    create_trash_structure()
    print("📁 Created organized trash2review/ structure")

    # Move deprecated files
    moved_count = categorize_and_move_files()
    print(f"\n📦 Moved {moved_count} deprecated files to trash2review/")

    # Clean remaining cache
    cleaned_count = clean_remaining_cache()
    print(f"🧹 Cleaned {cleaned_count} cache files")

    # Optimize project structure
    optimize_project_structure()

    # Create summary
    create_cleanup_summary()

    print("\n✅ PROJECT DECLUTTERING COMPLETE!")
    print(f"📊 Total files processed: {moved_count + cleaned_count}")
    print("📁 Files organized in: trash2review/")
    print("🚀 Project optimized for SPEED and PERFORMANCE")

    print("\n🔍 Next steps:")
    print("1. Review trash2review/ directory")
    print("2. Test application: python app.py")
    print("3. Delete trash2review/ when satisfied (optional)")

if __name__ == "__main__":
    main()
