#!/usr/bin/env python3
"""
This script helps identify and fix issues with the XAI API key configuration.
"""
import argparse
import os


def find_xai_references():
    """Find files that reference XAI API"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xai_files = []

    for root, _, files in os.walk(project_dir):
        # Skip virtual environment directories
        if '.venv' in root or '__pycache__' in root:
            continue

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath) as f:
                    try:
                        content = f.read()
                        if 'xai' in content.lower() and ('api' in content.lower() or 'key' in content.lower()):
                            xai_files.append(filepath)
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue

    return xai_files

def check_env_file():
    """Check if .env file exists and contains XAI API key"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_dir, '.env')

    if not os.path.exists(env_path):
        print(f"⚠️ .env file not found at {env_path}")
        return False

    with open(env_path) as f:
        content = f.read()
        if 'XAI_API_KEY' not in content:
            print("⚠️ XAI_API_KEY not found in .env file")
            return False

    return True

def ensure_env_file():
    """Create or update .env file with XAI API key entry"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_dir, '.env')

    if os.path.exists(env_path):
        with open(env_path) as f:
            content = f.read()

        if 'XAI_API_KEY' not in content:
            with open(env_path, 'a') as f:
                f.write("\n# XAI API Configuration\nXAI_API_KEY=your_xai_key_here\n")
    else:
        # Create new .env file based on example
        env_example_path = os.path.join(project_dir, '.env.example')
        if os.path.exists(env_example_path):
            with open(env_example_path) as f:
                content = f.read()

            with open(env_path, 'w') as f:
                f.write(content)
        else:
            # Create minimal .env file
            with open(env_path, 'w') as f:
                f.write("# API Keys\nXAI_API_KEY=your_xai_key_here\n")

    print(f"✅ Updated .env file at {env_path}")
    print("⚠️ Please edit the file and set your actual XAI API key.")

def main():
    parser = argparse.ArgumentParser(description='Fix XAI API key configuration issues')
    parser.add_argument('--scan', action='store_true', help='Scan for files using XAI API')
    parser.add_argument('--fix', action='store_true', help='Fix .env file')
    args = parser.parse_args()

    if args.scan:
        print("🔍 Scanning for files that reference XAI API...")
        xai_files = find_xai_references()
        if xai_files:
            print(f"Found {len(xai_files)} files with XAI references:")
            for file in xai_files:
                print(f"  - {file}")
        else:
            print("No files with XAI references found.")

    if args.fix or not args.scan:
        print("🔧 Checking .env file configuration...")
        if not check_env_file():
            ensure_env_file()
        else:
            print("✅ XAI_API_KEY is configured in .env file")

    print("\n👉 To use XAI services, make sure to:")
    print("  1. Set your actual XAI API key in the .env file")
    print("  2. Load environment variables using the 'dotenv' package")
    print("  3. Access the API key via: os.environ.get('XAI_API_KEY')")

if __name__ == "__main__":
    main()
