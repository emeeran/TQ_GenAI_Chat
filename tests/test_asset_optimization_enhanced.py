"""
Comprehensive Tests for Asset Optimization Pipeline

Tests for Task 2.1.2: Asset Optimization Pipeline
- JavaScript minification and source maps
- CSS optimization and compression
- Image optimization and WebP conversion
- Asset versioning and cache busting
- Flask integration

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from build_assets_enhanced import (
    AssetManifest,
    AssetOptimizationPipeline,
    BuildConfig,
    CSSOptimizer,
    JavaScriptOptimizer,
)
from core.flask_assets import FlaskAssetManager


class TestBuildConfig:
    """Test BuildConfig class"""

    def test_default_config(self):
        """Test default configuration"""
        config = BuildConfig()

        assert config.source_dir == Path("static")
        assert config.output_dir == Path("static/dist")
        assert config.enable_minification is True
        assert config.enable_compression is True
        assert config.enable_source_maps is True
        assert config.enable_cache_busting is True
        assert config.enable_image_optimization is True
        assert config.enable_webp_conversion is True
        assert config.image_quality == 85
        assert config.webp_quality == 80
        assert config.compression_level == 6

    def test_custom_config(self):
        """Test custom configuration"""
        config = BuildConfig(
            source_dir="src",
            output_dir="dist",
            enable_minification=False,
            enable_compression=False,
            image_quality=95,
            webp_quality=90,
        )

        assert config.source_dir == Path("src")
        assert config.output_dir == Path("dist")
        assert config.enable_minification is False
        assert config.enable_compression is False
        assert config.image_quality == 95
        assert config.webp_quality == 90

    def test_output_directory_creation(self):
        """Test that output directory is created"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "assets" / "dist"
            config = BuildConfig(output_dir=str(output_dir))

            assert output_dir.exists()
            assert output_dir.is_dir()


class TestAssetManifest:
    """Test AssetManifest class"""

    def test_empty_manifest(self):
        """Test empty manifest initialization"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "manifest.json"
            manifest = AssetManifest(manifest_path)

            assert manifest.manifest == {}
            assert manifest.get_asset_url("nonexistent.js") is None

            stats = manifest.get_stats()
            assert stats["total_assets"] == 0
            assert stats["total_compression_ratio"] == 0

    def test_add_asset(self):
        """Test adding assets to manifest"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "manifest.json"
            manifest = AssetManifest(manifest_path)

            manifest.add_asset(
                "js/app.js", "js/app.abc123.min.js", "abc123", 1000, 600, "application/javascript"
            )

            assert "js/app.js" in manifest.manifest
            asset = manifest.manifest["js/app.js"]
            assert asset["optimized_path"] == "js/app.abc123.min.js"
            assert asset["hash"] == "abc123"
            assert asset["original_size"] == 1000
            assert asset["optimized_size"] == 600
            assert asset["compression_ratio"] == 0.4
            assert asset["mime_type"] == "application/javascript"

    def test_get_asset_url(self):
        """Test getting asset URL"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "manifest.json"
            manifest = AssetManifest(manifest_path)

            manifest.add_asset(
                "js/app.js", "js/app.abc123.min.js", "abc123", 1000, 600, "application/javascript"
            )

            assert manifest.get_asset_url("js/app.js") == "js/app.abc123.min.js"
            assert manifest.get_asset_url("nonexistent.js") is None

    def test_save_and_load_manifest(self):
        """Test saving and loading manifest"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "manifest.json"

            # Create and save manifest
            manifest1 = AssetManifest(manifest_path)
            manifest1.add_asset(
                "js/app.js", "js/app.abc123.min.js", "abc123", 1000, 600, "application/javascript"
            )
            manifest1.save_manifest()

            # Load manifest
            manifest2 = AssetManifest(manifest_path)

            assert "js/app.js" in manifest2.manifest
            assert manifest2.get_asset_url("js/app.js") == "js/app.abc123.min.js"

    def test_get_stats(self):
        """Test getting statistics"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "manifest.json"
            manifest = AssetManifest(manifest_path)

            # Add multiple assets
            manifest.add_asset(
                "js/app.js", "js/app.min.js", "abc123", 1000, 600, "application/javascript"
            )
            manifest.add_asset("css/style.css", "css/style.min.css", "def456", 500, 300, "text/css")
            manifest.add_asset(
                "images/logo.png", "images/logo.opt.png", "ghi789", 2000, 1200, "image/png"
            )

            stats = manifest.get_stats()

            assert stats["total_assets"] == 3
            assert stats["total_original_size"] == 3500
            assert stats["total_optimized_size"] == 2100
            assert abs(stats["total_compression_ratio"] - 0.4) < 0.01

            assets_by_type = stats["assets_by_type"]
            assert assets_by_type["application"] == 1
            assert assets_by_type["text"] == 1
            assert assets_by_type["image"] == 1


class TestJavaScriptOptimizer:
    """Test JavaScriptOptimizer class"""

    @pytest.mark.asyncio
    async def test_basic_optimization(self):
        """Test basic JavaScript optimization"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir) / "src"
            output_dir = Path(tmp_dir) / "dist"
            source_dir.mkdir()
            output_dir.mkdir()

            # Create test JavaScript file
            js_content = """
            // This is a comment
            function hello() {
                console.log("Hello, world!");

                // Another comment
                return true;
            }
            """

            js_file = source_dir / "test.js"
            js_file.write_text(js_content)

            config = BuildConfig(
                source_dir=str(source_dir), output_dir=str(output_dir), enable_cache_busting=False
            )
            optimizer = JavaScriptOptimizer(config)

            # Optimize file
            output_path, info = await optimizer.optimize_file(js_file, output_dir)

            assert output_path.exists()
            assert output_path.name == "test.min.js"
            assert info["original_size"] > 0
            assert info["optimized_size"] > 0
            assert info["optimized_size"] <= info["original_size"]

    @pytest.mark.asyncio
    async def test_cache_busting(self):
        """Test cache busting functionality"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir) / "src"
            output_dir = Path(tmp_dir) / "dist"
            source_dir.mkdir()
            output_dir.mkdir()

            js_content = "function test() { return 42; }"
            js_file = source_dir / "test.js"
            js_file.write_text(js_content)

            config = BuildConfig(
                source_dir=str(source_dir), output_dir=str(output_dir), enable_cache_busting=True
            )
            optimizer = JavaScriptOptimizer(config)

            output_path, info = await optimizer.optimize_file(js_file, output_dir)

            assert output_path.exists()
            assert ".min.js" in output_path.name
            assert len(info["file_hash"]) == 8
            assert info["file_hash"] in output_path.name

    @pytest.mark.asyncio
    async def test_source_maps(self):
        """Test source map generation"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir) / "src"
            output_dir = Path(tmp_dir) / "dist"
            source_dir.mkdir()
            output_dir.mkdir()

            js_content = "function test() { return 42; }"
            js_file = source_dir / "test.js"
            js_file.write_text(js_content)

            config = BuildConfig(
                source_dir=str(source_dir), output_dir=str(output_dir), enable_source_maps=True
            )
            optimizer = JavaScriptOptimizer(config)

            output_path, info = await optimizer.optimize_file(js_file, output_dir)

            # Check for source map file
            source_map_path = output_path.with_suffix(".js.map")
            assert source_map_path.exists()

            # Check source map content
            source_map = json.loads(source_map_path.read_text())
            assert source_map["version"] == 3
            assert source_map["file"] == output_path.name

            # Check source map reference in minified file
            minified_content = output_path.read_text()
            assert f"sourceMappingURL={source_map_path.name}" in minified_content


class TestCSSOptimizer:
    """Test CSSOptimizer class"""

    @pytest.mark.asyncio
    async def test_basic_optimization(self):
        """Test basic CSS optimization"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir) / "src"
            output_dir = Path(tmp_dir) / "dist"
            source_dir.mkdir()
            output_dir.mkdir()

            # Create test CSS file
            css_content = """
            /* Main styles */
            body {
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
            }

            /* Header styles */
            .header {
                background-color: #333;
                color: white;
            }
            """

            css_file = source_dir / "test.css"
            css_file.write_text(css_content)

            config = BuildConfig(
                source_dir=str(source_dir), output_dir=str(output_dir), enable_cache_busting=False
            )
            optimizer = CSSOptimizer(config)

            # Optimize file
            output_path, info = await optimizer.optimize_file(css_file, output_dir)

            assert output_path.exists()
            assert output_path.name == "test.min.css"
            assert info["original_size"] > 0
            assert info["optimized_size"] > 0
            assert info["optimized_size"] <= info["original_size"]

            # Check minified content
            minified_content = output_path.read_text()
            assert "/* Main styles */" not in minified_content  # Comments removed
            assert "body{" in minified_content  # Whitespace removed

    @pytest.mark.asyncio
    async def test_compression(self):
        """Test CSS compression"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir) / "src"
            output_dir = Path(tmp_dir) / "dist"
            source_dir.mkdir()
            output_dir.mkdir()

            css_content = "body { margin: 0; padding: 0; }"
            css_file = source_dir / "test.css"
            css_file.write_text(css_content)

            config = BuildConfig(
                source_dir=str(source_dir), output_dir=str(output_dir), enable_compression=True
            )
            optimizer = CSSOptimizer(config)

            output_path, info = await optimizer.optimize_file(css_file, output_dir)

            # Check for gzipped file
            gzipped_path = output_path.with_suffix(output_path.suffix + ".gz")
            assert gzipped_path.exists()
            assert gzipped_path.stat().st_size < output_path.stat().st_size


class TestAssetOptimizationPipeline:
    """Test AssetOptimizationPipeline class"""

    @pytest.mark.asyncio
    async def test_build_assets(self):
        """Test building assets"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir) / "src"
            output_dir = Path(tmp_dir) / "dist"
            source_dir.mkdir()
            output_dir.mkdir()

            # Create test files
            (source_dir / "js").mkdir()
            (source_dir / "css").mkdir()

            js_file = source_dir / "js" / "app.js"
            js_file.write_text("function test() { return 42; }")

            css_file = source_dir / "css" / "style.css"
            css_file.write_text("body { margin: 0; }")

            config = BuildConfig(source_dir=str(source_dir), output_dir=str(output_dir))
            pipeline = AssetOptimizationPipeline(config)

            # Build assets
            results = await pipeline.build_assets()

            assert results["processed_files"] == 2
            assert results["javascript"]["count"] == 1
            assert results["css"]["count"] == 1
            assert results["build_time"] > 0
            assert results["compression_ratio"] >= 0

            # Check manifest
            manifest_path = output_dir / "manifest.json"
            assert manifest_path.exists()

            manifest_data = json.loads(manifest_path.read_text())
            assert "js/app.js" in manifest_data
            assert "css/style.css" in manifest_data

    @pytest.mark.asyncio
    async def test_get_asset_url(self):
        """Test getting asset URL"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir) / "src"
            output_dir = Path(tmp_dir) / "dist"
            source_dir.mkdir()
            output_dir.mkdir()

            js_file = source_dir / "app.js"
            js_file.write_text("function test() { return 42; }")

            config = BuildConfig(source_dir=str(source_dir), output_dir=str(output_dir))
            pipeline = AssetOptimizationPipeline(config)

            await pipeline.build_assets()

            # Test asset URL retrieval
            url = pipeline.get_asset_url("app.js")
            assert url is not None
            assert "min.js" in url


class TestFlaskAssetManager:
    """Test Flask integration"""

    def test_init_app(self):
        """Test Flask app initialization"""
        from flask import Flask

        app = Flask(__name__)
        manager = FlaskAssetManager()

        with app.app_context():
            manager.init_app(app)

            # Check configuration
            assert "ASSET_SOURCE_DIR" in app.config
            assert "ASSET_OUTPUT_DIR" in app.config
            assert manager.pipeline is not None

    def test_template_helpers_registration(self):
        """Test template helpers registration"""
        from flask import Flask

        app = Flask(__name__)
        manager = FlaskAssetManager(app)

        with app.app_context():
            # Check that template globals are registered
            assert "asset_url" in app.jinja_env.globals
            assert "js_asset" in app.jinja_env.globals
            assert "css_asset" in app.jinja_env.globals
            assert "img_asset" in app.jinja_env.globals
            assert "preload_assets" in app.jinja_env.globals

    def test_get_asset_url_fallback(self):
        """Test asset URL fallback"""
        from flask import Flask

        app = Flask(__name__)
        manager = FlaskAssetManager(app)

        with app.app_context():
            # Should fallback to static URL when asset not in manifest
            url = manager.get_asset_url("nonexistent.js")
            assert "/static/nonexistent.js" in url


@pytest.mark.asyncio
async def test_integration_workflow():
    """Test complete integration workflow"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        source_dir = Path(tmp_dir) / "static"
        output_dir = Path(tmp_dir) / "dist"

        # Create directory structure
        (source_dir / "js").mkdir(parents=True)
        (source_dir / "css").mkdir()
        (source_dir / "images").mkdir()

        # Create test files
        js_content = """
        // App JavaScript
        function initApp() {
            console.log("App initialized");
            return true;
        }

        // Export function
        window.app = { init: initApp };
        """

        css_content = """
        /* Reset styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        /* Layout */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        """

        (source_dir / "js" / "app.js").write_text(js_content)
        (source_dir / "css" / "main.css").write_text(css_content)

        # Create build configuration
        config = BuildConfig(
            source_dir=str(source_dir),
            output_dir=str(output_dir),
            enable_minification=True,
            enable_compression=True,
            enable_source_maps=True,
            enable_cache_busting=True,
        )

        # Initialize pipeline
        pipeline = AssetOptimizationPipeline(config)

        # Build assets
        results = await pipeline.build_assets()

        # Verify results
        assert results["processed_files"] == 2
        assert results["javascript"]["count"] == 1
        assert results["css"]["count"] == 1
        assert results["errors"] == []
        assert results["compression_ratio"] > 0

        # Verify output files
        js_output_dir = output_dir / "js"
        css_output_dir = output_dir / "css"

        assert js_output_dir.exists()
        assert css_output_dir.exists()

        # Check JavaScript files
        js_files = list(js_output_dir.glob("*.js"))
        assert len(js_files) >= 1

        # Check for minified file
        min_js_files = [f for f in js_files if "min.js" in f.name]
        assert len(min_js_files) >= 1

        # Check for source map
        source_map_files = list(js_output_dir.glob("*.js.map"))
        assert len(source_map_files) >= 1

        # Check CSS files
        css_files = list(css_output_dir.glob("*.css"))
        assert len(css_files) >= 1

        # Check manifest
        manifest_path = output_dir / "manifest.json"
        assert manifest_path.exists()

        manifest_data = json.loads(manifest_path.read_text())
        assert "js/app.js" in manifest_data
        assert "css/main.css" in manifest_data

        # Verify manifest content
        js_asset = manifest_data["js/app.js"]
        assert js_asset["original_size"] > 0
        assert js_asset["optimized_size"] > 0
        assert js_asset["compression_ratio"] >= 0
        assert len(js_asset["hash"]) == 8

        css_asset = manifest_data["css/main.css"]
        assert css_asset["original_size"] > 0
        assert css_asset["optimized_size"] > 0
        assert css_asset["compression_ratio"] >= 0

        print("✅ Integration test passed - Asset optimization pipeline working correctly!")
        print(f"📊 Processed {results['processed_files']} files")
        print(f"📦 JavaScript: {results['javascript']['count']} files")
        print(f"🎨 CSS: {results['css']['count']} files")
        print(f"📉 Compression: {results['compression_ratio']:.1%}")


if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_integration_workflow())
