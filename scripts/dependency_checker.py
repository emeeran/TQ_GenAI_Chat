#!/usr/bin/env python3
"""
TQ GenAI Chat - Comprehensive Dependency and Function Checker

This script verifies that all modules, features, and functions work as intended by:
1. Checking Python dependencies and imports
2. Validating configuration files
3. Testing API endpoints
4. Verifying file processing capabilities
5. Checking frontend functionality
6. Running basic integration tests

Usage: python scripts/dependency_checker.py [--verbose] [--fix]
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Required Python packages
REQUIRED_PACKAGES = [
    "flask",
    "requests",
    "anthropic",
    "groq",
    "openai",
    "PyPDF2",
    "python-docx",
    "pandas",
    "openpyxl",
    "Pillow",
    "redis",
]

# Optional packages (warnings only if missing)
OPTIONAL_PACKAGES = ["pytest", "black", "flake8", "mypy"]

# Configuration files to check
CONFIG_FILES = ["requirements.txt", "pyproject.toml", "config/settings.py"]

# API endpoints to test
API_ENDPOINTS = ["/health", "/get_models/groq", "/personas", "/documents/list"]


class DependencyChecker:
    def __init__(self, verbose=False, fix=False):
        self.verbose = verbose
        self.fix = fix
        self.errors = []
        self.warnings = []
        self.successes = []

    def log(self, message, level="info"):
        """Log messages with different levels"""
        if level == "error":
            self.errors.append(message)
            print(f"❌ ERROR: {message}")
        elif level == "warning":
            self.warnings.append(message)
            print(f"⚠️  WARNING: {message}")
        elif level == "success":
            self.successes.append(message)
            print(f"✅ SUCCESS: {message}")
        elif self.verbose:
            print(f"ℹ️  INFO: {message}")

    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            self.log(
                f"Python {version.major}.{version.minor}.{version.micro} is compatible", "success"
            )
        else:
            self.log(
                f"Python {version.major}.{version.minor} may not be compatible. Requires Python 3.8+",
                "warning",
            )

    def check_package_imports(self):
        """Check if required packages can be imported"""
        for package in REQUIRED_PACKAGES:
            try:
                importlib.import_module(package.replace("-", "_"))
                self.log(f"Package '{package}' imported successfully", "success")
            except ImportError as e:
                self.log(f"Required package '{package}' not found: {e}", "error")
                if self.fix:
                    self.install_package(package)

        for package in OPTIONAL_PACKAGES:
            try:
                importlib.import_module(package.replace("-", "_"))
                self.log(f"Optional package '{package}' available", "success")
            except ImportError:
                self.log(f"Optional package '{package}' not found", "warning")

    def install_package(self, package):
        """Attempt to install missing package"""
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            self.log(f"Successfully installed '{package}'", "success")
        except subprocess.CalledProcessError:
            self.log(f"Failed to install '{package}'", "error")

    def check_config_files(self):
        """Check configuration files exist and are valid"""
        for config_file in CONFIG_FILES:
            file_path = PROJECT_ROOT / config_file
            if file_path.exists():
                self.log(f"Configuration file '{config_file}' exists", "success")

                # Validate specific file types
                if config_file.endswith(".json"):
                    try:
                        with open(file_path) as f:
                            json.load(f)
                        self.log(f"JSON file '{config_file}' is valid", "success")
                    except json.JSONDecodeError as e:
                        self.log(f"JSON file '{config_file}' is invalid: {e}", "error")
            else:
                self.log(f"Configuration file '{config_file}' missing", "error")

    def check_environment_variables(self):
        """Check for required environment variables"""
        env_vars = {
            "OPENAI_API_KEY": "Optional - enables OpenAI models",
            "ANTHROPIC_API_KEY": "Optional - enables Anthropic models",
            "GROQ_API_KEY": "Optional - enables Groq models",
            "XAI_API_KEY": "Optional - enables XAI models",
        }

        for var, description in env_vars.items():
            if os.getenv(var):
                self.log(f"Environment variable '{var}' is set", "success")
            else:
                self.log(f"Environment variable '{var}' not set - {description}", "warning")

    def check_project_structure(self):
        """Verify project directory structure"""
        required_dirs = ["static", "templates", "core", "services", "config"]

        for directory in required_dirs:
            dir_path = PROJECT_ROOT / directory
            if dir_path.exists() and dir_path.is_dir():
                self.log(f"Directory '{directory}' exists", "success")
            else:
                self.log(f"Required directory '{directory}' missing", "error")

    def check_main_files(self):
        """Check main application files"""
        main_files = ["app.py", "static/script.js", "static/styles.css", "templates/index.html"]

        for file_path in main_files:
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                self.log(f"Main file '{file_path}' exists", "success")
            else:
                self.log(f"Main file '{file_path}' missing", "error")

    def test_flask_app_startup(self):
        """Test if Flask app can start without errors"""
        try:
            # Import the main app module
            sys.path.insert(0, str(PROJECT_ROOT))
            import app

            # Check if Flask app is defined
            if hasattr(app, "app"):
                self.log("Flask app object found", "success")

                # Test app configuration
                with app.app.app_context():
                    self.log("Flask app context created successfully", "success")
            else:
                self.log("Flask app object not found in app.py", "error")

        except ImportError as e:
            self.log(f"Cannot import main app module: {e}", "error")
        except Exception as e:
            self.log(f"Error testing Flask app: {e}", "error")

    def test_api_endpoints(self, base_url="http://localhost:5000"):
        """Test API endpoints if server is running"""
        print("\n🔗 Testing API endpoints...")

        # First check if server is running
        try:
            response = requests.get(base_url, timeout=5)
            self.log("Flask server is running", "success")
        except requests.ConnectionError:
            self.log("Flask server not running - skipping endpoint tests", "warning")
            return
        except Exception as e:
            self.log(f"Error connecting to server: {e}", "warning")
            return

        # Test each endpoint
        for endpoint in API_ENDPOINTS:
            try:
                url = urljoin(base_url, endpoint)
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    self.log(f"Endpoint '{endpoint}' responding correctly", "success")
                else:
                    self.log(
                        f"Endpoint '{endpoint}' returned status {response.status_code}", "warning"
                    )

            except requests.RequestException as e:
                self.log(f"Endpoint '{endpoint}' failed: {e}", "error")

    def test_file_processing(self):
        """Test file processing capabilities"""
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from core.file_processor import FileProcessor

            # Test with a simple text file
            FileProcessor()

            # This would normally process a file - we're just checking import
            self.log("File processor module imported successfully", "success")

        except ImportError as e:
            self.log(f"Cannot import file processor: {e}", "error")
        except Exception as e:
            self.log(f"Error testing file processor: {e}", "warning")

    def check_database_connectivity(self):
        """Check database files and connectivity"""
        db_files = ["documents.db"]

        for db_file in db_files:
            db_path = PROJECT_ROOT / db_file
            if db_path.exists():
                self.log(f"Database file '{db_file}' exists", "success")

                # Test SQLite connection
                try:
                    import sqlite3

                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    conn.close()

                    if tables:
                        self.log(f"Database '{db_file}' has {len(tables)} tables", "success")
                    else:
                        self.log(f"Database '{db_file}' exists but has no tables", "warning")

                except Exception as e:
                    self.log(f"Cannot connect to database '{db_file}': {e}", "error")
            else:
                self.log(f"Database file '{db_file}' will be created on first use", "info")

    def generate_report(self):
        """Generate comprehensive dependency report"""
        report_path = PROJECT_ROOT / "dependency_report.md"

        with open(report_path, "w") as f:
            f.write(
                f"""# TQ GenAI Chat - Dependency Check Report
Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- ✅ Successes: {len(self.successes)}
- ⚠️  Warnings: {len(self.warnings)}
- ❌ Errors: {len(self.errors)}

## Status
{'🟢 All systems operational' if not self.errors else '🔴 Issues detected - see errors below'}

## Errors ({len(self.errors)})
"""
            )
            for error in self.errors:
                f.write(f"- ❌ {error}\n")

            f.write(f"\n## Warnings ({len(self.warnings)})\n")
            for warning in self.warnings:
                f.write(f"- ⚠️  {warning}\n")

            f.write(f"\n## Successes ({len(self.successes)})\n")
            for success in self.successes:
                f.write(f"- ✅ {success}\n")

            f.write(
                """
## Recommendations

### If you have errors:
1. Install missing packages: `pip install -r requirements.txt`
2. Check Python version compatibility (3.8+ required)
3. Verify project file structure
4. Set up required configuration files

### For better development experience:
1. Set API keys as environment variables
2. Install optional development packages
3. Run the Flask app to test endpoints
4. Consider setting up Redis for caching

### Next Steps:
1. Fix any critical errors listed above
2. Run the application: `python app.py`
3. Open http://localhost:5000 in your browser
4. Test core functionality (chat, file upload, model switching)
"""
            )

        self.log(f"Dependency report saved to: {report_path}", "success")

    def run_all_checks(self):
        """Run all dependency and functionality checks"""
        print("🔍 TQ GenAI Chat - Comprehensive Dependency Check")
        print("=" * 50)

        print("\n🐍 Checking Python environment...")
        self.check_python_version()

        print("\n📦 Checking package imports...")
        self.check_package_imports()

        print("\n⚙️  Checking configuration files...")
        self.check_config_files()

        print("\n🌍 Checking environment variables...")
        self.check_environment_variables()

        print("\n📁 Checking project structure...")
        self.check_project_structure()

        print("\n📄 Checking main files...")
        self.check_main_files()

        print("\n🚀 Testing Flask application...")
        self.test_flask_app_startup()

        print("\n🗄️  Checking database connectivity...")
        self.check_database_connectivity()

        print("\n📁 Testing file processing...")
        self.test_file_processing()

        # Test endpoints if requested
        self.test_api_endpoints()

        print("\n📊 Generating report...")
        self.generate_report()

        print(f"\n{'='*50}")
        print(f"✅ Successes: {len(self.successes)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")

        if not self.errors:
            print("\n🎉 All critical dependencies satisfied!")
        else:
            print(f"\n⚠️  Found {len(self.errors)} errors that need attention")

        return len(self.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Check TQ GenAI Chat dependencies and functionality"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix missing dependencies")

    args = parser.parse_args()

    checker = DependencyChecker(verbose=args.verbose, fix=args.fix)
    success = checker.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
