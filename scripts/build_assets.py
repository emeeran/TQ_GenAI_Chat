#!/usr/bin/env python3
"""
Production Asset Build System for TQ GenAI Chat
Handles ES6 module optimization, minification, and deployment preparation
"""

import asyncio
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Optional

try:
    import terser

    TERSER_AVAILABLE = True
except ImportError:
    TERSER_AVAILABLE = False

try:
    import cssmin
    import jsmin

    MINIFICATION_AVAILABLE = True
except ImportError:
    MINIFICATION_AVAILABLE = False

from core.cdn_optimization import AssetOptimizer

logger = logging.getLogger(__name__)


class ModularAssetBuilder:
    """
    Enhanced asset build system for ES6 modular JavaScript architecture
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or self.get_default_config()
        self.source_dir = Path(self.config["source_dir"])
        self.build_dir = Path(self.config["build_dir"])
        self.static_dir = Path(self.config["static_dir"])

        # Build directories
        self.js_build_dir = self.build_dir / "js"
        self.css_build_dir = self.build_dir / "css"
        self.assets_build_dir = self.build_dir / "assets"

        # Asset tracking
        self.asset_manifest = {}
        self.build_stats = {
            "start_time": 0,
            "end_time": 0,
            "files_processed": 0,
            "total_size_before": 0,
            "total_size_after": 0,
            "modules_bundled": 0,
            "errors": [],
        }

        # Initialize build system
        self.init_build_system()

    def get_default_config(self) -> dict:
        """Get default build configuration"""
        return {
            "source_dir": "static",
            "build_dir": "static/dist",
            "static_dir": "static",
            "minify_js": True,
            "minify_css": True,
            "generate_sourcemaps": True,
            "optimize_images": True,
            "enable_compression": True,
            "cache_busting": True,
            "module_bundling": True,
            "tree_shaking": True,
            "dead_code_elimination": True,
            "compression_level": 9,
            "image_quality": 85,
            "target_browsers": ["> 1%", "last 2 versions", "not dead"],
            "es_version": "es2018",
        }

    def init_build_system(self):
        """Initialize build system directories and files"""
        # Create build directories
        for dir_path in [
            self.build_dir,
            self.js_build_dir,
            self.css_build_dir,
            self.assets_build_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Initialize manifest
        self.manifest_path = self.build_dir / "manifest.json"
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                self.asset_manifest = json.load(f)

    async def build_production(self) -> dict[str, Any]:
        """
        Complete production build process
        """
        logger.info("🚀 Starting production build...")
        self.build_stats["start_time"] = time.time()

        try:
            # Clean previous build
            await self.clean_build()

            # Build JavaScript modules
            await self.build_javascript_modules()

            # Build CSS assets
            await self.build_css_assets()

            # Optimize other assets
            await self.optimize_static_assets()

            # Generate asset manifest
            await self.generate_manifest()

            # Create compressed versions
            if self.config["enable_compression"]:
                await self.create_compressed_assets()

            # Generate build report
            build_report = await self.generate_build_report()

            self.build_stats["end_time"] = time.time()

            logger.info(
                f"✅ Production build completed in {self.build_stats['end_time'] - self.build_stats['start_time']:.2f}s"
            )

            return build_report

        except Exception as e:
            logger.error(f"❌ Production build failed: {e}")
            self.build_stats["errors"].append(str(e))
            raise

    async def clean_build(self):
        """Clean previous build artifacts"""
        logger.info("🧹 Cleaning previous build...")

        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)

        # Recreate directories
        self.init_build_system()

    async def build_javascript_modules(self):
        """
        Build and optimize ES6 JavaScript modules
        """
        logger.info("📦 Building JavaScript modules...")

        # Define module dependencies and build order
        module_config = {
            "utils/helpers.js": {"dependencies": [], "type": "utility", "critical": True},
            "core/api.js": {"dependencies": ["utils/helpers.js"], "type": "core", "critical": True},
            "core/ui.js": {"dependencies": ["utils/helpers.js"], "type": "core", "critical": True},
            "core/storage.js": {
                "dependencies": ["utils/helpers.js"],
                "type": "core",
                "critical": False,
            },
            "core/settings.js": {
                "dependencies": ["utils/helpers.js"],
                "type": "core",
                "critical": False,
            },
            "core/chat.js": {
                "dependencies": ["utils/helpers.js"],
                "type": "feature",
                "critical": False,
            },
            "core/file-handler.js": {
                "dependencies": ["utils/helpers.js"],
                "type": "feature",
                "critical": False,
            },
            "app.js": {
                "dependencies": [
                    "utils/helpers.js",
                    "core/api.js",
                    "core/ui.js",
                    "core/storage.js",
                    "core/settings.js",
                ],
                "type": "main",
                "critical": True,
            },
        }

        # Process each module
        for module_path, config in module_config.items():
            await self.process_javascript_module(module_path, config)

        # Create module bundles
        if self.config["module_bundling"]:
            await self.create_module_bundles(module_config)

    async def process_javascript_module(self, module_path: str, config: dict):
        """Process individual JavaScript module"""
        source_file = self.source_dir / "js" / module_path

        if not source_file.exists():
            logger.warning(f"⚠️  Module not found: {source_file}")
            return

        logger.info(f"🔄 Processing module: {module_path}")

        # Read source
        with open(source_file, encoding="utf-8") as f:
            source_content = f.read()

        original_size = len(source_content.encode("utf-8"))
        self.build_stats["total_size_before"] += original_size

        # Process module
        processed_content = source_content

        # Add module metadata
        module_info = f"""
/**
 * Module: {module_path}
 * Type: {config['type']}
 * Critical: {config['critical']}
 * Dependencies: {', '.join(config['dependencies'])}
 * Build Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
 */
"""
        processed_content = module_info + processed_content

        # Minify if enabled
        if self.config["minify_js"]:
            processed_content = await self.minify_javascript(processed_content, module_path)

        # Generate file hash for cache busting
        file_hash = self.generate_file_hash(processed_content)

        # Create output filename
        module_name = Path(module_path).stem
        output_filename = f"{module_name}.{file_hash[:8]}.js"
        output_path = self.js_build_dir / Path(module_path).parent / output_filename

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write processed module
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(processed_content)

        # Generate source map if enabled
        if self.config["generate_sourcemaps"]:
            await self.generate_sourcemap(source_file, output_path, processed_content)

        # Update manifest
        self.asset_manifest[
            f"js/{module_path}"
        ] = f"dist/js/{Path(module_path).parent}/{output_filename}"

        # Update stats
        optimized_size = len(processed_content.encode("utf-8"))
        self.build_stats["total_size_after"] += optimized_size
        self.build_stats["files_processed"] += 1

        logger.info(
            f"✅ {module_path}: {original_size} → {optimized_size} bytes ({((original_size - optimized_size) / original_size * 100):.1f}% reduction)"
        )

    async def minify_javascript(self, content: str, module_path: str) -> str:
        """Minify JavaScript content using best available method"""
        try:
            if TERSER_AVAILABLE:
                # Use Terser for advanced minification
                return await self.minify_with_terser(content)
            elif MINIFICATION_AVAILABLE:
                # Use jsmin as fallback
                return jsmin.jsmin(content)
            else:
                # Basic minification
                return self.basic_js_minify(content)

        except Exception as e:
            logger.warning(f"⚠️  Minification failed for {module_path}: {e}")
            return content

    async def minify_with_terser(self, content: str) -> str:
        """Minify using Terser (advanced ES6+ minifier)"""
        # This would require a Node.js process or Python binding
        # For now, we'll use the basic minifier with ES6 awareness
        return self.advanced_js_minify(content)

    def advanced_js_minify(self, content: str) -> str:
        """Advanced JavaScript minification with ES6 support"""
        # Preserve ES6 module syntax and features
        lines = content.split("\n")
        minified_lines = []

        in_comment_block = False

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Handle comment blocks
            if line.startswith("/*"):
                in_comment_block = True
                if line.endswith("*/"):
                    in_comment_block = False
                continue

            if in_comment_block:
                if line.endswith("*/"):
                    in_comment_block = False
                continue

            # Skip single-line comments (but preserve important ones)
            if line.startswith("//") and not any(
                keyword in line.lower() for keyword in ["@", "license", "copyright", "preserve"]
            ):
                continue

            # Preserve important syntax
            if any(
                keyword in line
                for keyword in [
                    "import",
                    "export",
                    "class",
                    "function",
                    "const",
                    "let",
                    "var",
                    "async",
                    "await",
                ]
            ):
                minified_lines.append(line)
            else:
                # Basic space reduction for other lines
                minified_lines.append(" ".join(line.split()))

        return "\n".join(minified_lines)

    def basic_js_minify(self, content: str) -> str:
        """Basic JavaScript minification"""
        # Remove comments and extra whitespace while preserving ES6 syntax
        lines = content.split("\n")
        processed_lines = []

        for line in lines:
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            # Remove excessive whitespace but preserve structure
            processed_lines.append(" ".join(stripped.split()))

        return "\n".join(processed_lines)

    async def create_module_bundles(self, module_config: dict):
        """Create optimized module bundles"""
        logger.info("📦 Creating module bundles...")

        # Create critical bundle (essential modules for first paint)
        critical_modules = [path for path, config in module_config.items() if config["critical"]]
        await self.create_bundle("critical", critical_modules)

        # Create feature bundles (lazy-loaded modules)
        feature_modules = [
            path for path, config in module_config.items() if config["type"] == "feature"
        ]
        if feature_modules:
            await self.create_bundle("features", feature_modules)

    async def create_bundle(self, bundle_name: str, module_paths: list[str]):
        """Create a module bundle"""
        logger.info(f"📦 Creating {bundle_name} bundle...")

        bundle_content = []

        for module_path in module_paths:
            # Read built module
            built_path = (
                self.js_build_dir / Path(module_path).parent / f"{Path(module_path).stem}.*.js"
            )

            # Find the actual built file (with hash)
            built_files = list(self.js_build_dir.glob(str(built_path).replace("*", "*")))
            if built_files:
                with open(built_files[0], encoding="utf-8") as f:
                    module_content = f.read()
                    bundle_content.append(f"// Module: {module_path}\n{module_content}\n")

        if bundle_content:
            # Create bundle
            bundle_js = "\n".join(bundle_content)
            bundle_hash = self.generate_file_hash(bundle_js)
            bundle_filename = f"{bundle_name}.{bundle_hash[:8]}.bundle.js"
            bundle_path = self.js_build_dir / bundle_filename

            with open(bundle_path, "w", encoding="utf-8") as f:
                f.write(bundle_js)

            # Update manifest
            self.asset_manifest[f"bundles/{bundle_name}.js"] = f"dist/js/{bundle_filename}"

            logger.info(f"✅ Created {bundle_name} bundle: {len(bundle_js)} bytes")
            self.build_stats["modules_bundled"] += len(module_paths)

    async def build_css_assets(self):
        """Build and optimize CSS assets"""
        logger.info("🎨 Building CSS assets...")

        css_files = list(self.source_dir.glob("**/*.css"))

        for css_file in css_files:
            await self.process_css_file(css_file)

    async def process_css_file(self, css_file: Path):
        """Process individual CSS file"""
        relative_path = css_file.relative_to(self.static_dir)
        logger.info(f"🔄 Processing CSS: {relative_path}")

        # Read source
        with open(css_file, encoding="utf-8") as f:
            css_content = f.read()

        original_size = len(css_content.encode("utf-8"))
        self.build_stats["total_size_before"] += original_size

        # Minify CSS if enabled
        if self.config["minify_css"] and MINIFICATION_AVAILABLE:
            css_content = cssmin.cssmin(css_content)

        # Generate file hash
        file_hash = self.generate_file_hash(css_content)

        # Create output filename
        output_filename = f"{css_file.stem}.{file_hash[:8]}.css"
        output_path = self.css_build_dir / output_filename

        # Write processed CSS
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(css_content)

        # Update manifest
        self.asset_manifest[str(relative_path)] = f"dist/css/{output_filename}"

        # Update stats
        optimized_size = len(css_content.encode("utf-8"))
        self.build_stats["total_size_after"] += optimized_size
        self.build_stats["files_processed"] += 1

        logger.info(f"✅ {css_file.name}: {original_size} → {optimized_size} bytes")

    async def optimize_static_assets(self):
        """Optimize other static assets (images, fonts, etc.)"""
        logger.info("🖼️  Optimizing static assets...")

        # Use existing AssetOptimizer for images and other assets
        asset_optimizer = AssetOptimizer(
            source_dir=str(self.static_dir), output_dir=str(self.assets_build_dir)
        )

        results = await asset_optimizer.optimize_all_assets()

        # Merge results
        self.build_stats["files_processed"] += results.get("processed_files", 0)
        self.build_stats["total_size_before"] += results.get("total_size_before", 0)
        self.build_stats["total_size_after"] += results.get("total_size_after", 0)
        self.build_stats["errors"].extend(results.get("errors", []))

        # Update manifest with optimized assets
        if hasattr(asset_optimizer, "asset_manifest"):
            self.asset_manifest.update(asset_optimizer.asset_manifest)

    async def generate_manifest(self):
        """Generate asset manifest for cache busting and asset loading"""
        logger.info("📋 Generating asset manifest...")

        # Add build metadata
        self.asset_manifest["_build_info"] = {
            "build_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "build_timestamp": int(time.time()),
            "files_processed": self.build_stats["files_processed"],
            "modules_bundled": self.build_stats["modules_bundled"],
            "compression_ratio": self.calculate_compression_ratio(),
            "config": self.config,
        }

        # Write manifest
        with open(self.manifest_path, "w") as f:
            json.dump(self.asset_manifest, f, indent=2)

        logger.info(f"✅ Manifest generated with {len(self.asset_manifest)} entries")

    async def create_compressed_assets(self):
        """Create compressed versions of assets"""
        logger.info("🗜️  Creating compressed assets...")

        import gzip

        import brotli

        # Compress all built files
        for build_dir in [self.js_build_dir, self.css_build_dir]:
            for asset_file in build_dir.rglob("*"):
                if asset_file.is_file() and not asset_file.name.endswith((".gz", ".br")):
                    # Create gzip version
                    with open(asset_file, "rb") as f_in:
                        with gzip.open(
                            f"{asset_file}.gz", "wb", compresslevel=self.config["compression_level"]
                        ) as f_out:
                            f_out.write(f_in.read())

                    # Create brotli version if available
                    try:
                        with open(asset_file, "rb") as f_in:
                            compressed = brotli.compress(
                                f_in.read(), quality=self.config["compression_level"]
                            )
                            with open(f"{asset_file}.br", "wb") as f_out:
                                f_out.write(compressed)
                    except ImportError:
                        pass  # Brotli not available

        logger.info("✅ Compressed asset versions created")

    async def generate_sourcemap(self, source_file: Path, output_file: Path, content: str):
        """Generate source maps for debugging"""
        # Basic source map generation
        sourcemap = {
            "version": 3,
            "file": output_file.name,
            "sources": [str(source_file.relative_to(self.source_dir))],
            "mappings": "",  # Would need proper source map generation
            "sourcesContent": [],
        }

        sourcemap_path = output_file.with_suffix(output_file.suffix + ".map")
        with open(sourcemap_path, "w") as f:
            json.dump(sourcemap, f)

    def generate_file_hash(self, content: str) -> str:
        """Generate hash for file content"""
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def calculate_compression_ratio(self) -> float:
        """Calculate overall compression ratio"""
        if self.build_stats["total_size_before"] > 0:
            return (
                self.build_stats["total_size_before"] - self.build_stats["total_size_after"]
            ) / self.build_stats["total_size_before"]
        return 0.0

    async def generate_build_report(self) -> dict[str, Any]:
        """Generate comprehensive build report"""
        duration = self.build_stats["end_time"] - self.build_stats["start_time"]

        return {
            "success": len(self.build_stats["errors"]) == 0,
            "duration": duration,
            "files_processed": self.build_stats["files_processed"],
            "modules_bundled": self.build_stats["modules_bundled"],
            "size_reduction": {
                "before": self.build_stats["total_size_before"],
                "after": self.build_stats["total_size_after"],
                "ratio": self.calculate_compression_ratio(),
                "saved_bytes": self.build_stats["total_size_before"]
                - self.build_stats["total_size_after"],
            },
            "manifest_entries": len(self.asset_manifest) - 1,  # Exclude _build_info
            "errors": self.build_stats["errors"],
            "build_config": self.config,
            "asset_manifest": self.asset_manifest,
        }


async def main():
    """Main build script entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="TQ GenAI Chat Asset Build System")
    parser.add_argument("--config", type=str, help="Build configuration file")
    parser.add_argument("--production", action="store_true", help="Production build mode")
    parser.add_argument("--watch", action="store_true", help="Watch mode for development")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")

    args = parser.parse_args()

    # Load configuration
    config = None
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)

    # Initialize builder
    builder = ModularAssetBuilder(config)

    if args.clean:
        await builder.clean_build()
        print("🧹 Build artifacts cleaned")
        return

    if args.production:
        # Production build
        report = await builder.build_production()

        print("\n🎉 Production build completed!")
        print(f"   Duration: {report['duration']:.2f}s")
        print(f"   Files processed: {report['files_processed']}")
        print(f"   Modules bundled: {report['modules_bundled']}")
        print(f"   Size reduction: {report['size_reduction']['ratio']:.2%}")
        print(f"   Saved: {report['size_reduction']['saved_bytes']:,} bytes")

        if report["errors"]:
            print(f"   ⚠️  {len(report['errors'])} errors occurred")
            for error in report["errors"]:
                print(f"      - {error}")

    elif args.watch:
        print("👀 Watch mode not implemented yet")

    else:
        print("Please specify --production, --watch, or --clean")


if __name__ == "__main__":
    asyncio.run(main())
