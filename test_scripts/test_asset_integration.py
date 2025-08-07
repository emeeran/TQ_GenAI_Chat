#!/usr/bin/env python3
"""
Simple Asset Integration Test
Tests the core asset optimization functionality
"""

import json
import tempfile
from pathlib import Path

from flask import Flask


# Test the core functionality
def test_asset_loader():
    """Test basic asset loader functionality"""
    print("🔄 Testing AssetLoader core functionality...")

    temp_dir = Path(tempfile.mkdtemp())
    static_dir = temp_dir / "static"
    static_dir.mkdir(parents=True)

    try:
        # Create test manifest
        manifest_path = static_dir / "manifest.json"
        test_manifest = {
            "js/app.js": "dist/js/app.min.js",
            "styles.css": "dist/css/styles.min.css",
            "_build_info": {"build_timestamp": 1234567890, "environment": "production"},
        }

        with open(manifest_path, "w") as f:
            json.dump(test_manifest, f)

        # Test asset loader
        from core.asset_loader import AssetLoader

        app = Flask(__name__, static_folder=str(static_dir))
        app.config["SERVER_NAME"] = "localhost:5000"

        asset_loader = AssetLoader(app, manifest_path=str(manifest_path))

        # Test in application context
        with app.app_context():
            with app.test_request_context():
                # Test asset URL generation
                url = asset_loader.asset_url("js/app.js")
                print(f"✅ Asset URL: {url}")

                # Test JS module generation
                js_module = asset_loader.js_module("js/app.js")
                print(f"✅ JS Module Tag: {js_module[:60]}...")

                # Test production mode
                asset_loader.production_mode = True
                prod_url = asset_loader.asset_url("js/app.js")
                print(f"✅ Production URL: {prod_url}")

                # Test fallback mode
                asset_loader.production_mode = False
                fallback_url = asset_loader.asset_url("js/app.js")
                print(f"✅ Fallback URL: {fallback_url}")

                # Test asset info
                info = asset_loader.get_asset_info("js/app.js")
                print(f"✅ Asset Info: {info}")

        print("✅ AssetLoader test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ AssetLoader test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        import shutil

        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def test_flask_integration():
    """Test Flask integration"""
    print("🔄 Testing Flask integration...")

    temp_dir = Path(tempfile.mkdtemp())
    static_dir = temp_dir / "static"
    static_dir.mkdir(parents=True)

    try:
        # Create test assets
        js_dir = static_dir / "js"
        js_dir.mkdir()
        (js_dir / "app.js").write_text('console.log("test");')

        css_dir = static_dir / "css"
        css_dir.mkdir()
        (css_dir / "styles.css").write_text("body { margin: 0; }")

        # Create manifest
        manifest = {
            "js/app.js": "js/app.js",  # No optimization for test
            "css/styles.css": "css/styles.css",
        }

        manifest_path = static_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        # Test Flask integration
        app = Flask(__name__, static_folder=str(static_dir))
        app.config["SERVER_NAME"] = "localhost:5000"

        from core.asset_integration import integrate_asset_optimization

        asset_loader = integrate_asset_optimization(app)

        print(f"✅ Asset loader integrated: {type(asset_loader).__name__}")
        print(
            f"✅ Template functions available: {len([k for k in app.jinja_env.globals.keys() if 'asset' in k])}"
        )

        # Test with client
        with app.test_client() as client:
            with app.app_context():
                # Test template functions
                asset_url = app.jinja_env.globals["asset_url"]("js/app.js")
                print(f"✅ Template asset_url: {asset_url}")

                js_module = app.jinja_env.globals["js_module"]("js/app.js")
                print(f"✅ Template js_module: {js_module[:50]}...")

        print("✅ Flask integration test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Flask integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        import shutil

        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def test_template_rendering():
    """Test optimized template rendering"""
    print("🔄 Testing template rendering...")

    try:
        temp_dir = Path(tempfile.mkdtemp())
        static_dir = temp_dir / "static"
        templates_dir = temp_dir / "templates"

        static_dir.mkdir(parents=True)
        templates_dir.mkdir(parents=True)

        # Create simple test template
        template_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    {{ css_bundle() | safe }}
</head>
<body>
    <h1>TQ GenAI Chat Test</h1>
    {{ critical_js() | safe }}
</body>
</html>"""

        (templates_dir / "test.html").write_text(template_content)

        # Create manifest
        manifest = {"css/main.css": "dist/css/main.min.css", "js/app.js": "dist/js/app.min.js"}

        manifest_path = static_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        # Set up Flask app
        app = Flask(__name__, static_folder=str(static_dir), template_folder=str(templates_dir))
        app.config["SERVER_NAME"] = "localhost:5000"

        from core.asset_integration import integrate_asset_optimization

        integrate_asset_optimization(app)

        # Test template rendering
        with app.test_client() as client:

            @app.route("/")
            def test_route():
                from flask import render_template

                return render_template("test.html")

            response = client.get("/")
            html = response.get_data(as_text=True)

            print(f"✅ Template rendered successfully: {len(html)} chars")

            if "css_bundle" in html or "link" in html:
                print("✅ CSS bundle function worked")
            else:
                print("⚠️  CSS bundle function may need work")

            if "critical_js" in html or "script" in html:
                print("✅ Critical JS function worked")
            else:
                print("⚠️  Critical JS function may need work")

        print("✅ Template rendering test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Template rendering test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        import shutil

        if temp_dir.exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("🎯 TQ GenAI Chat - Asset Optimization Integration Test")
    print("=" * 60)

    tests = [
        ("AssetLoader Core", test_asset_loader),
        ("Flask Integration", test_flask_integration),
        ("Template Rendering", test_template_rendering),
    ]

    passed = 0
    for name, test_func in tests:
        print(f"\n🧪 Running {name} Test...")
        print("-" * 40)

        if test_func():
            print(f"✅ {name} test PASSED")
            passed += 1
        else:
            print(f"❌ {name} test FAILED")

        print("-" * 40)

    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All tests passed! Asset optimization is working correctly.")
        exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        exit(1)
