"""
Flask Integration for Enhanced Asset Optimization Pipeline

This module provides Flask integration for the asset optimization pipeline,
including template helpers and production asset serving.

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import json
import logging
from pathlib import Path

from flask import Flask, current_app, url_for
from markupsafe import Markup

from build_assets_enhanced import AssetOptimizationPipeline, BuildConfig

logger = logging.getLogger(__name__)


class FlaskAssetManager:
    """Flask integration for asset optimization"""

    def __init__(self, app: Flask = None, config: dict = None):
        self.app = app
        self.pipeline = None
        self.manifest = {}
        self.config = config or {}

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize with Flask app"""
        self.app = app

        # Default configuration
        app.config.setdefault("ASSET_SOURCE_DIR", "static")
        app.config.setdefault("ASSET_OUTPUT_DIR", "static/dist")
        app.config.setdefault("ASSET_URL_PREFIX", "/static/dist")
        app.config.setdefault("ASSET_MINIFY", True)
        app.config.setdefault("ASSET_COMPRESS", True)
        app.config.setdefault("ASSET_SOURCE_MAPS", app.debug)
        app.config.setdefault("ASSET_CACHE_BUSTING", not app.debug)
        app.config.setdefault("ASSET_IMAGE_OPTIMIZATION", True)

        # Create build configuration
        build_config = BuildConfig(
            source_dir=app.config["ASSET_SOURCE_DIR"],
            output_dir=app.config["ASSET_OUTPUT_DIR"],
            enable_minification=app.config["ASSET_MINIFY"],
            enable_compression=app.config["ASSET_COMPRESS"],
            enable_source_maps=app.config["ASSET_SOURCE_MAPS"],
            enable_cache_busting=app.config["ASSET_CACHE_BUSTING"],
            enable_image_optimization=app.config["ASSET_IMAGE_OPTIMIZATION"],
        )

        # Initialize pipeline
        self.pipeline = AssetOptimizationPipeline(build_config)

        # Load manifest
        self._load_manifest()

        # Register template helpers
        self._register_template_helpers()

        # Register CLI commands
        self._register_cli_commands()

    def _load_manifest(self):
        """Load asset manifest"""
        try:
            manifest_path = Path(self.app.config["ASSET_OUTPUT_DIR"]) / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    self.manifest = json.load(f)
            else:
                logger.warning(
                    "Asset manifest not found. Run 'flask assets build' to generate assets."
                )
                self.manifest = {}
        except Exception as e:
            logger.error(f"Failed to load asset manifest: {e}")
            self.manifest = {}

    def _register_template_helpers(self):
        """Register Jinja2 template helpers"""

        @self.app.template_global()
        def asset_url(path: str) -> str:
            """Get optimized asset URL"""
            return self.get_asset_url(path)

        @self.app.template_global()
        def js_asset(path: str, **attrs) -> Markup:
            """Generate script tag for JavaScript asset"""
            url = self.get_asset_url(path)
            attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
            return Markup(f'<script src="{url}"{" " + attrs_str if attrs_str else ""}></script>')

        @self.app.template_global()
        def css_asset(path: str, **attrs) -> Markup:
            """Generate link tag for CSS asset"""
            url = self.get_asset_url(path)
            attrs.setdefault("rel", "stylesheet")
            attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
            return Markup(f'<link href="{url}"{" " + attrs_str if attrs_str else ""}>')

        @self.app.template_global()
        def img_asset(path: str, **attrs) -> Markup:
            """Generate img tag with optimized image and WebP fallback"""
            optimized_url = self.get_asset_url(path)

            # Check for WebP version
            webp_path = path.rsplit(".", 1)[0] + ".webp"
            webp_url = self.get_asset_url(webp_path)

            if webp_url and webp_url != optimized_url:
                # Generate picture element with WebP fallback
                attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
                return Markup(
                    f"""
                <picture>
                    <source srcset="{webp_url}" type="image/webp">
                    <img src="{optimized_url}"{" " + attrs_str if attrs_str else ""}>
                </picture>
                """.strip()
                )
            else:
                # Regular img tag
                attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
                return Markup(f'<img src="{optimized_url}"{" " + attrs_str if attrs_str else ""}>')

        @self.app.template_global()
        def preload_assets(*paths, **kwargs) -> Markup:
            """Generate preload links for critical assets"""
            preload_type = kwargs.get("as", "script")
            links = []

            for path in paths:
                url = self.get_asset_url(path)
                links.append(f'<link rel="preload" href="{url}" as="{preload_type}">')

            return Markup("\n".join(links))

    def _register_cli_commands(self):
        """Register Flask CLI commands"""

        @self.app.cli.command()
        def assets_build():
            """Build optimized assets"""
            import asyncio

            async def build():
                results = await self.pipeline.build_assets()

                # Reload manifest
                self._load_manifest()

                # Print results
                logger.info("Asset build completed!")
                logger.info(
                    f"Processed {results['processed_files']} files in {results['build_time']:.2f}s"
                )
                logger.info(f"JavaScript: {results['javascript']['count']} files")
                logger.info(f"CSS: {results['css']['count']} files")
                logger.info(f"Images: {results['images']['count']} files")
                logger.info(f"Overall compression: {results['compression_ratio']:.1%}")

                if results["errors"]:
                    logger.warning(f"{len(results['errors'])} errors occurred:")
                    for error in results["errors"]:
                        logger.warning(f"  - {error}")

            asyncio.run(build())

        @self.app.cli.command()
        def assets_watch():
            """Watch assets and rebuild on changes"""
            import asyncio

            async def watch():
                logger.info("Starting asset watcher...")
                await self.pipeline.watch_and_rebuild()

            asyncio.run(watch())

        @self.app.cli.command()
        def assets_clean():
            """Clean built assets"""
            import shutil

            output_dir = Path(self.app.config["ASSET_OUTPUT_DIR"])
            if output_dir.exists():
                shutil.rmtree(output_dir)
                logger.info(f"Cleaned asset directory: {output_dir}")
            else:
                logger.info("Asset directory doesn't exist")

        @self.app.cli.command()
        def assets_stats():
            """Show asset statistics"""
            if not self.manifest:
                logger.info("No asset manifest found. Run 'flask assets build' first.")
                return

            stats = self.pipeline.manifest.get_stats()

            logger.info("Asset Statistics:")
            logger.info(f"Total assets: {stats['total_assets']}")
            logger.info(f"Original size: {stats['total_original_size']:,} bytes")
            logger.info(f"Optimized size: {stats['total_optimized_size']:,} bytes")
            logger.info(f"Compression ratio: {stats['total_compression_ratio']:.1%}")

            logger.info("\nAssets by type:")
            for asset_type, count in stats["assets_by_type"].items():
                logger.info(f"  {asset_type}: {count} files")

    def get_asset_url(self, path: str) -> str:
        """Get optimized asset URL with fallback"""
        # Try to get optimized version from manifest
        if path in self.manifest:
            optimized_path = self.manifest[path]["optimized_path"]
            return f"{self.app.config['ASSET_URL_PREFIX']}/{optimized_path}"

        # Fallback to original asset
        return url_for("static", filename=path)

    def get_asset_info(self, path: str) -> dict:
        """Get asset information from manifest"""
        return self.manifest.get(path, {})

    def asset_exists(self, path: str) -> bool:
        """Check if asset exists in manifest"""
        return path in self.manifest


# Template context processor for asset information
def inject_asset_context():
    """Inject asset context into templates"""
    if hasattr(current_app, "asset_manager"):
        return {"asset_stats": current_app.asset_manager.pipeline.manifest.get_stats()}
    return {}


# Example usage patterns for templates
TEMPLATE_EXAMPLES = """
<!-- Template Examples for Asset Optimization -->

<!-- JavaScript assets with cache busting -->
{{ js_asset('js/app.js') }}
{{ js_asset('js/modules/chat.js', defer=True) }}

<!-- CSS assets with cache busting -->
{{ css_asset('css/main.css') }}
{{ css_asset('css/theme.css', media='screen') }}

<!-- Optimized images with WebP fallback -->
{{ img_asset('images/logo.png', alt='Logo', class='logo') }}

<!-- Preload critical assets -->
{{ preload_assets('css/critical.css', 'js/app.js', as='style') }}

<!-- Manual asset URL resolution -->
<link rel="icon" href="{{ asset_url('images/favicon.ico') }}">

<!-- Conditional loading based on asset existence -->
{% if asset_manager.asset_exists('js/analytics.js') %}
    {{ js_asset('js/analytics.js', async=True) }}
{% endif %}

<!-- Picture element with multiple formats -->
{{ img_asset('images/hero.jpg', alt='Hero Image', class='hero-bg') }}

<!-- Asset information in templates -->
{% if asset_stats.total_assets > 0 %}
    <!-- Assets optimized: {{ asset_stats.total_compression_ratio|round(1) }}% reduction -->
{% endif %}
"""


def register_asset_manager(app: Flask, **config):
    """Convenience function to register asset manager"""
    asset_manager = FlaskAssetManager(app, config)

    # Store reference on app for easy access
    app.asset_manager = asset_manager

    # Register context processor
    app.context_processor(inject_asset_context)

    return asset_manager
