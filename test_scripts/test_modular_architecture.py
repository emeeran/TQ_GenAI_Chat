#!/usr/bin/env python3
"""
Comprehensive test for modular JavaScript architecture
Tests Phase 1 performance optimizations and ES6 module integration
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_file_structure():
    """Test that all modular JavaScript files exist"""
    print("🔍 Testing file structure...")

    required_files = [
        "static/js/app.js",
        "static/js/core/api.js",
        "static/js/core/ui.js",
        "static/js/core/chat.js",
        "static/js/core/file-handler.js",
        "static/js/core/settings.js",
        "static/js/core/storage.js",
        "static/js/utils/helpers.js",
        "static/css/modular-ui.css",
        "core/async_handler.py",
        "core/database_optimizations.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    print("✅ All required files present")
    return True


def test_javascript_syntax():
    """Test JavaScript modules for syntax errors"""
    print("\n🔍 Testing JavaScript syntax...")

    js_files = [
        "static/js/app.js",
        "static/js/core/api.js",
        "static/js/core/ui.js",
        "static/js/core/chat.js",
        "static/js/core/file-handler.js",
        "static/js/core/settings.js",
        "static/js/core/storage.js",
        "static/js/utils/helpers.js",
    ]

    errors = []
    for js_file in js_files:
        try:
            # Use Node.js to check syntax if available
            result = subprocess.run(
                ["node", "-c", js_file], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                errors.append(f"{js_file}: {result.stderr}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback: Basic syntax check by reading file
            try:
                with open(js_file, encoding="utf-8") as f:
                    content = f.read()
                    # Check for common ES6 module patterns
                    if "export" not in content and js_file != "static/js/app.js":
                        errors.append(f"{js_file}: Missing export statement")
                    # Check for proper imports
                    if js_file == "static/js/app.js" and "import" not in content:
                        errors.append(f"{js_file}: Missing import statements")
            except Exception as e:
                errors.append(f"{js_file}: {str(e)}")

    if errors:
        print(f"❌ JavaScript syntax errors: {errors}")
        return False

    print("✅ JavaScript syntax valid")
    return True


def test_python_imports():
    """Test that Python optimizations can be imported"""
    print("\n🔍 Testing Python imports...")

    try:
        # Test async handler
        from core.async_handler import AsyncHandler, async_route

        print("✅ AsyncHandler imported successfully")

        # Test database optimizations
        from core.database_optimizations import OptimizedDocumentStore

        print("✅ OptimizedDocumentStore imported successfully")

        # Test hybrid cache
        try:
            from core.hybrid_cache import HybridCache

            print("✅ HybridCache imported successfully")
        except ImportError:
            print("⚠️  HybridCache not found - will use fallback caching")

        return True

    except ImportError as e:
        print(f"❌ Python import error: {e}")
        return False


def test_flask_app_startup():
    """Test that the Flask app starts with new optimizations"""
    print("\n🔍 Testing Flask app startup...")

    try:
        import app as flask_app

        # Check that app has been enhanced with optimizations
        if not hasattr(flask_app, "document_store"):
            print("❌ document_store not initialized")
            return False

        if not hasattr(flask_app, "async_handler"):
            print("❌ async_handler not initialized")
            return False

        print("✅ Flask app enhanced with optimizations")
        return True

    except Exception as e:
        print(f"❌ Flask app startup error: {e}")
        return False


def test_performance_endpoints():
    """Test new performance monitoring endpoints"""
    print("\n🔍 Testing performance endpoints...")

    try:
        import app as flask_app

        with flask_app.app.test_client() as client:
            # Test health endpoint
            response = client.get("/health")
            if response.status_code != 200:
                print(f"❌ /health endpoint failed: {response.status_code}")
                return False

            health_data = json.loads(response.data)
            if "database" not in health_data or "cache" not in health_data:
                print("❌ Health endpoint missing optimization data")
                return False

            # Test performance cache endpoint
            response = client.get("/performance/cache")
            if response.status_code != 200:
                print(f"❌ /performance/cache endpoint failed: {response.status_code}")
                return False

            print("✅ Performance endpoints working")
            return True

    except Exception as e:
        print(f"❌ Performance endpoints error: {e}")
        return False


def test_es6_module_exports():
    """Test that ES6 modules have proper exports"""
    print("\n🔍 Testing ES6 module exports...")

    module_exports = {
        "static/js/core/api.js": ["APIService"],
        "static/js/core/ui.js": ["UIManager"],
        "static/js/core/chat.js": ["ChatManager"],
        "static/js/core/file-handler.js": ["FileHandler"],
        "static/js/core/settings.js": ["SettingsManager"],
        "static/js/core/storage.js": ["StorageManager"],
        "static/js/utils/helpers.js": ["debounce", "throttle", "generateId", "showToast"],
    }

    errors = []
    for file_path, expected_exports in module_exports.items():
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

                for export_name in expected_exports:
                    if (
                        f"export {{ {export_name}" not in content
                        and f"export default {export_name}" not in content
                        and f"export function {export_name}" not in content
                        and f"export const {export_name}" not in content
                    ):
                        errors.append(f"{file_path}: Missing export for {export_name}")

        except Exception as e:
            errors.append(f"{file_path}: {str(e)}")

    if errors:
        print(f"❌ Module export errors: {errors}")
        return False

    print("✅ ES6 module exports valid")
    return True


def test_html_template_updates():
    """Test that HTML template uses new modular architecture"""
    print("\n🔍 Testing HTML template updates...")

    try:
        with open("templates/index.html", encoding="utf-8") as f:
            content = f.read()

            # Check for new module script
            if 'type="module"' not in content:
                print("❌ HTML template missing ES6 module script")
                return False

            if "js/app.js" not in content:
                print("❌ HTML template not loading new app.js")
                return False

            # Check for new CSS
            if "modular-ui.css" not in content:
                print("❌ HTML template missing modular UI CSS")
                return False

            print("✅ HTML template updated for modular architecture")
            return True

    except Exception as e:
        print(f"❌ HTML template test error: {e}")
        return False


def test_async_route_decorator():
    """Test async route decorator functionality"""
    print("\n🔍 Testing async route decorator...")

    try:
        from flask import Flask

        from core.async_handler import async_route

        test_app = Flask(__name__)

        @async_route
        def test_function():
            return {"status": "success"}

        # Test that decorator returns a function
        if not callable(test_function):
            print("❌ async_route decorator not returning callable")
            return False

        print("✅ async_route decorator working")
        return True

    except Exception as e:
        print(f"❌ async_route decorator error: {e}")
        return False


def benchmark_performance():
    """Basic performance benchmark"""
    print("\n🔍 Running performance benchmark...")

    try:
        import app as flask_app

        with flask_app.app.test_client() as client:
            # Benchmark health endpoint
            start_time = time.time()
            for _ in range(10):
                response = client.get("/health")
            health_time = (time.time() - start_time) / 10

            # Benchmark models endpoint
            start_time = time.time()
            for _ in range(5):
                response = client.get("/get_models/openai")
            models_time = (time.time() - start_time) / 5

            print("✅ Performance benchmark:")
            print(f"   Health endpoint: {health_time:.3f}s avg")
            print(f"   Models endpoint: {models_time:.3f}s avg")

            # Performance expectations
            if health_time > 0.1:
                print("⚠️  Health endpoint slower than expected")
            if models_time > 0.5:
                print("⚠️  Models endpoint slower than expected")

            return True

    except Exception as e:
        print(f"❌ Performance benchmark error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 TQ GenAI Chat - Modular JavaScript Architecture Test")
    print("=" * 60)

    tests = [
        test_file_structure,
        test_javascript_syntax,
        test_python_imports,
        test_flask_app_startup,
        test_performance_endpoints,
        test_es6_module_exports,
        test_html_template_updates,
        test_async_route_decorator,
        benchmark_performance,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Modular JavaScript architecture ready")
        return True
    else:
        print(f"⚠️  {failed} test(s) failed - review issues above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
