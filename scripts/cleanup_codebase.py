#!/usr/bin/env python3
"""
Codebase Cleanup Script

Moves deprecated files to trash2review and performs cleanup operations.
"""

import shutil
from pathlib import Path


def move_to_trash(source_path: Path, trash_dir: Path):
    """Move file or directory to trash"""
    if source_path.exists():
        trash_target = trash_dir / source_path.name
        if trash_target.exists():
            shutil.rmtree(trash_target) if trash_target.is_dir() else trash_target.unlink()
        shutil.move(str(source_path), str(trash_target))
        print(f"Moved {source_path} -> {trash_target}")


def cleanup_codebase():
    """Perform comprehensive codebase cleanup"""
    base_dir = Path(__file__).parent
    trash_dir = base_dir / "trash2review"
    
    # Ensure trash directory exists
    trash_dir.mkdir(exist_ok=True)
    (trash_dir / "deprecated_scripts").mkdir(exist_ok=True)
    (trash_dir / "old_docs").mkdir(exist_ok=True)
    (trash_dir / "unused_files").mkdir(exist_ok=True)
    
    # Move deprecated scripts
    deprecated_scripts = [
        "deploy.py",
        "test_audio_features.py",
        "app_integration.py",
        "ai_models.py",
        "modify.md",
        "idea.md"
    ]
    
    for script in deprecated_scripts:
        script_path = base_dir / script
        if script_path.exists():
            move_to_trash(script_path, trash_dir / "deprecated_scripts")
    
    # Move old documentation
    old_docs = [
        "dependency_report.md",
        "IMPLEMENTATION_COMPLETE.md",
        "OPTIMIZATION_SUMMARY.md"
    ]
    
    for doc in old_docs:
        doc_path = base_dir / doc
        if doc_path.exists():
            move_to_trash(doc_path, trash_dir / "old_docs")
    
    # Move unused cache files
    unused_files = [
        "models_cache.json",
        "defaults_cache.json",
        "documents.db"
    ]
    
    for file in unused_files:
        file_path = base_dir / file
        if file_path.exists():
            move_to_trash(file_path, trash_dir / "unused_files")
    
    # Clean up __pycache__ directories
    for pycache in base_dir.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
            print(f"Removed {pycache}")
    
    # Clean up .pyc files
    for pyc_file in base_dir.rglob("*.pyc"):
        pyc_file.unlink()
        print(f"Removed {pyc_file}")
    
    print("✅ Codebase cleanup completed!")


if __name__ == "__main__":
    cleanup_codebase()
