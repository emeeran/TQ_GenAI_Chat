#!/usr/bin/env python3
"""
TQ GenAI Chat - Project Cleanup and Organization Script

This script helps maintain the project by:
1. Moving deprecated and redundant files to trash2review
2. Organizing test scripts to ./scripts
3. Purging cache files and temporary data
4. Organizing project structure

Usage: python scripts/cleanup_project.py [--dry-run] [--verbose]
"""

import argparse
import glob
import os
import shutil
from datetime import datetime
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Files and directories to move to trash2review (deprecated/redundant)
DEPRECATED_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.bak",
    "*.tmp",
    "*.old",
    "*~",
    "test_*.py",  # Test files should go to scripts
    "*_test.py",
    "temp_*",
    "backup_*",
    "old_*",
    "deprecated_*",
    "unused_*"
]

# Cache directories and files to purge
CACHE_PATTERNS = [
    "__pycache__",
    "*.log",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    "node_modules",
    ".DS_Store",
    "Thumbs.db",
    "*.sqlite-journal",
    "*.db-journal"
]

# Test scripts to move to scripts directory
TEST_SCRIPT_PATTERNS = [
    "test_*.py",
    "*_test.py",
    "*_tests.py",
    "tests.py"
]

# Directories to organize
ORGANIZE_DIRS = {
    'logs': ['*.log', '*.out'],
    'docs': ['*.md', '*.txt', '*.rst'],
    'config': ['*.ini', '*.cfg', '*.conf', '*.yaml', '*.yml', '*.json'],
    'scripts': ['*.sh', '*.bat', '*.ps1']
}

def log_action(message, verbose=False):
    """Log action with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if verbose:
        print(f"[{timestamp}] {message}")

def find_files_by_patterns(directory, patterns):
    """Find files matching given patterns in directory"""
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(directory, pattern), recursive=True))
        files.extend(glob.glob(os.path.join(directory, "**", pattern), recursive=True))
    return list(set(files))  # Remove duplicates

def move_deprecated_files(dry_run=False, verbose=False):
    """Move deprecated and redundant files to trash2review"""
    trash_dir = PROJECT_ROOT / "trash2review"
    trash_dir.mkdir(exist_ok=True)

    deprecated_files = find_files_by_patterns(PROJECT_ROOT, DEPRECATED_PATTERNS)

    # Filter out files that are actually needed
    exclude_files = [
        str(PROJECT_ROOT / "test_get_models.py"),
        str(PROJECT_ROOT / "test_update_models.py"),
        str(PROJECT_ROOT / "test_edit_functionality.py")
    ]

    deprecated_files = [f for f in deprecated_files if f not in exclude_files]

    for file_path in deprecated_files:
        if os.path.exists(file_path):
            relative_path = os.path.relpath(file_path, PROJECT_ROOT)
            dest_path = trash_dir / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if not dry_run:
                shutil.move(file_path, dest_path)

            log_action(f"{'[DRY RUN] ' if dry_run else ''}Moved {relative_path} to trash2review/", verbose)

def move_test_scripts(dry_run=False, verbose=False):
    """Move test scripts to scripts directory"""
    scripts_dir = PROJECT_ROOT / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    test_files = find_files_by_patterns(PROJECT_ROOT, TEST_SCRIPT_PATTERNS)

    for file_path in test_files:
        if os.path.exists(file_path) and PROJECT_ROOT in Path(file_path).parents:
            # Don't move files already in scripts directory
            if "scripts" in file_path:
                continue

            filename = os.path.basename(file_path)
            dest_path = scripts_dir / filename

            if not dry_run:
                shutil.move(file_path, dest_path)

            log_action(f"{'[DRY RUN] ' if dry_run else ''}Moved {filename} to scripts/", verbose)

def purge_cache_files(dry_run=False, verbose=False):
    """Remove cache files and temporary data"""
    cache_files = find_files_by_patterns(PROJECT_ROOT, CACHE_PATTERNS)

    for item_path in cache_files:
        if os.path.exists(item_path):
            relative_path = os.path.relpath(item_path, PROJECT_ROOT)

            if not dry_run:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)

            log_action(f"{'[DRY RUN] ' if dry_run else ''}Removed cache: {relative_path}", verbose)

def organize_project_structure(dry_run=False, verbose=False):
    """Organize files into appropriate directories"""
    for dir_name, patterns in ORGANIZE_DIRS.items():
        if dir_name == 'scripts':  # Skip scripts as we handle them separately
            continue

        target_dir = PROJECT_ROOT / dir_name

        files = find_files_by_patterns(PROJECT_ROOT, patterns)

        # Filter to only root level files
        root_files = [f for f in files if Path(f).parent == PROJECT_ROOT]

        if root_files and not dry_run:
            target_dir.mkdir(exist_ok=True)

        for file_path in root_files:
            filename = os.path.basename(file_path)
            dest_path = target_dir / filename

            # Skip if file is already in the target directory
            if Path(file_path).parent == target_dir:
                continue

            if not dry_run:
                shutil.move(file_path, dest_path)

            log_action(f"{'[DRY RUN] ' if dry_run else ''}Organized {filename} to {dir_name}/", verbose)

def create_gitignore():
    """Create or update .gitignore file"""
    gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
.venv/
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
*.log
logs/

# Database
*.db
*.sqlite
*.sqlite3

# Cache
.cache/
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db

# Project specific
trash2review/
uploads/
saved_chats/
exports/
documents.db
*.bak
*.tmp
*.old
""".strip()

    gitignore_path = PROJECT_ROOT / ".gitignore"

    if gitignore_path.exists():
        # Read existing content
        with open(gitignore_path) as f:
            existing = f.read()

        # Add missing entries
        lines_to_add = []
        for line in gitignore_content.split('\n'):
            if line.strip() and line not in existing:
                lines_to_add.append(line)

        if lines_to_add:
            with open(gitignore_path, 'a') as f:
                f.write('\n\n# Added by cleanup script\n')
                f.write('\n'.join(lines_to_add))
    else:
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)

def generate_cleanup_report():
    """Generate a cleanup report"""
    report_path = PROJECT_ROOT / "cleanup_report.md"

    with open(report_path, 'w') as f:
        f.write(f"""# Project Cleanup Report
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Project Structure
```
TQ_GenAI_Chat/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── config/               # Configuration files
├── core/                 # Business logic modules
├── services/             # Provider-specific implementations
├── static/               # Frontend assets (CSS, JS)
├── templates/            # HTML templates
├── scripts/              # Test and utility scripts
├── trash2review/         # Deprecated files for review
├── uploads/              # User uploaded files
├── saved_chats/          # Saved chat sessions
└── exports/              # Exported chat data
```

## Cleanup Actions Performed
- Moved deprecated files to `trash2review/`
- Organized test scripts to `scripts/`
- Purged cache files and temporary data
- Updated .gitignore for better version control

## Files Moved to trash2review/
Files that appeared to be deprecated, redundant, or temporary have been moved
to the `trash2review/` directory for manual review before permanent deletion.

## Next Steps
1. Review files in `trash2review/` directory
2. Permanently delete confirmed unnecessary files
3. Update documentation as needed
4. Commit organized project structure
""")

def main():
    parser = argparse.ArgumentParser(description="Clean up and organize TQ GenAI Chat project")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    print("🧹 TQ GenAI Chat Project Cleanup")
    print("=" * 40)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        print()

    # Step 1: Move deprecated files
    print("📦 Moving deprecated files to trash2review...")
    move_deprecated_files(args.dry_run, args.verbose)

    # Step 2: Move test scripts
    print("🧪 Moving test scripts to scripts directory...")
    move_test_scripts(args.dry_run, args.verbose)

    # Step 3: Purge cache files
    print("🗑️  Purging cache files...")
    purge_cache_files(args.dry_run, args.verbose)

    # Step 4: Organize structure
    print("📁 Organizing project structure...")
    organize_project_structure(args.dry_run, args.verbose)

    if not args.dry_run:
        # Step 5: Update .gitignore
        print("📝 Updating .gitignore...")
        create_gitignore()

        # Step 6: Generate report
        print("📊 Generating cleanup report...")
        generate_cleanup_report()

    print()
    print("✅ Cleanup completed!")
    if args.dry_run:
        print("💡 Run without --dry-run to actually perform the cleanup")
    else:
        print("📋 Check cleanup_report.md for details")

if __name__ == "__main__":
    main()
