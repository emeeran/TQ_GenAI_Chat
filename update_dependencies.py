#!/usr/bin/env python3
"""
Update dependencies for the TQ_GenAI_Chat application.
"""
import subprocess
import sys
import os

def update_dependencies():
    """Update dependencies to ensure async Flask support."""
    print("Updating dependencies for TQ_GenAI_Chat...")

    # Upgrade pip first
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

    # Install required packages
    required_packages = [
        'asgiref>=3.5.0',
        'flask[async]>=2.0.1'
    ]

    for package in required_packages:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

    # Install all other dependencies from requirements.txt
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    print(f"Installing dependencies from {requirements_path}...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])

    print("\nDependencies updated successfully!")
    print("\nTo fix the async view error, either:")
    print("1. Run the application with the modified synchronous upload_files function")
    print("2. Or use the flask[async] package which was just installed")

if __name__ == "__main__":
    update_dependencies()
