"""
Migration utility to fix imports after refactoring.
This script updates imports in app.py to use the new module structure.
"""
import os
import re
from pathlib import Path

def fix_imports(file_path):
    """Fix imports in a Python file to use the new module structure"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace utility imports
    replacements = [
        (r'from utils.file_processor import', 'from core.file_processor import'),
        (r'from utils.api_config import', 'from config.settings import'),
        (r'from utils.caching import', 'from core.utilities import'),
        (r'import utils.file_processor', 'import core.file_processor'),
        (r'import utils.api_config', 'import config.settings'),
        (r'import utils.caching', 'import core.utilities'),
        (r'utils.file_processor', 'core.file_processor'),
        (r'utils.api_config', 'config.settings'),
        (r'utils.caching', 'core.utilities'),
    ]
    
    for old, new in replacements:
        content = re.sub(old, new, content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Updated imports in {file_path}")

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    python_files = [
        base_dir / "app.py",
        base_dir / "ai_models.py",
        base_dir / "persona.py",
    ]
    
    # Add files from core and services
    for directory in ["core", "services"]:
        dir_path = base_dir / directory
        if dir_path.exists():
            python_files.extend(list(dir_path.glob("*.py")))
    
    # Fix imports in each file
    for file_path in python_files:
        if file_path.exists():
            fix_imports(str(file_path))

if __name__ == "__main__":
    main()
