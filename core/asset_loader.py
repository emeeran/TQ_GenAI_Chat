"""
Asset Loading Helper for TQ GenAI Chat
Manages optimized asset loading with cache busting and fallbacks
"""

import json
import logging
from pathlib import Path

from flask import url_for

logger = logging.getLogger(__name__)


class AssetLoader:
    """
    Manages loading of optimized assets with proper fallbacks
    """

    def __init__(self, app=None, manifest_path: str = "static/dist/manifest.json"):
        self.app = app
        self.manifest_path = Path(manifest_path)
        self.manifest: dict[str, str] = {}
        self.production_mode = False
        self.cache_buster_enabled = True

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        self.production_mode = app.config.get(
            "PRODUCTION_MODE", app.config.get("ENV") == "production"
        )

        # Load asset manifest
        self.load_manifest()

        # Register template functions
        app.jinja_env.globals["asset_url"] = self.asset_url
        app.jinja_env.globals["js_module"] = self.js_module
        app.jinja_env.globals["css_bundle"] = self.css_bundle
        app.jinja_env.globals["critical_js"] = self.critical_js

        logger.info(f"AssetLoader initialized (production: {self.production_mode})")

    def load_manifest(self):
        """Load asset manifest from build process"""
        try:
            if self.manifest_path.exists():
                with open(self.manifest_path) as f:
                    self.manifest = json.load(f)
                logger.info(f"Loaded asset manifest with {len(self.manifest)} entries")
            else:
                logger.warning(f"Asset manifest not found: {self.manifest_path}")
                self.manifest = {}
        except Exception as e:
            logger.error(f"Failed to load asset manifest: {e}")
            self.manifest = {}

    def asset_url(self, asset_path: str, fallback: bool = True) -> str:
        """
        Get URL for asset with production optimization

        Args:
            asset_path: Original asset path (e.g., 'js/app.js')
            fallback: Whether to fallback to original if optimized not found
        """
        if self.production_mode and asset_path in self.manifest:
            # Use optimized asset in production
            optimized_path = self.manifest[asset_path]
            return url_for("static", filename=optimized_path)

        elif fallback:
            # Fallback to original asset
            if self.cache_buster_enabled:
                return self.add_cache_buster(url_for("static", filename=asset_path))
            return url_for("static", filename=asset_path)

        else:
            # Return empty if no fallback and not found
            logger.warning(f"Asset not found in manifest: {asset_path}")
            return ""

    def js_module(self, module_path: str, critical: bool = False) -> str:
        """
        Generate JavaScript module script tag

        Args:
            module_path: Module path (e.g., 'js/app.js')
            critical: Whether this is a critical module for first paint
        """
        asset_url = self.asset_url(module_path)

        if not asset_url:
            return ""

        # Generate module script tag
        attributes = ['type="module"']

        if not critical:
            attributes.append("defer")

        return f'<script {" ".join(attributes)} src="{asset_url}"></script>'

    def critical_js(self) -> str:
        """
        Load critical JavaScript bundle for first paint
        """
        if self.production_mode:
            # Use critical bundle in production
            bundle_url = self.asset_url("bundles/critical.js", fallback=False)
            if bundle_url:
                return f'<script type="module" src="{bundle_url}"></script>'

        # Fallback: Load individual critical modules
        critical_modules = ["js/utils/helpers.js", "js/core/api.js", "js/core/ui.js", "js/app.js"]

        scripts = []
        for module in critical_modules:
            script = self.js_module(module, critical=True)
            if script:
                scripts.append(script)

        return "\n".join(scripts)

    def css_bundle(self, bundle_name: str = "main") -> str:
        """
        Generate CSS link tags for bundle
        """
        css_files = []

        if self.production_mode:
            # Look for CSS bundle
            bundle_key = f"css/{bundle_name}.css"
            if bundle_key in self.manifest:
                css_files.append(self.asset_url(bundle_key))

        if not css_files:
            # Fallback to individual CSS files
            css_patterns = ["styles.css", "css/modular-ui.css"]
            for pattern in css_patterns:
                url = self.asset_url(pattern)
                if url:
                    css_files.append(url)

        # Generate link tags
        links = []
        for css_url in css_files:
            links.append(f'<link rel="stylesheet" href="{css_url}">')

        return "\n".join(links)

    def preload_assets(self, asset_paths: list) -> str:
        """
        Generate preload tags for critical assets
        """
        preload_tags = []

        for asset_path in asset_paths:
            asset_url = self.asset_url(asset_path)
            if not asset_url:
                continue

            # Determine asset type
            if asset_path.endswith(".js"):
                as_type = "script"
                if "module" in asset_path.lower():
                    preload_tags.append(f'<link rel="modulepreload" href="{asset_url}">')
                else:
                    preload_tags.append(f'<link rel="preload" href="{asset_url}" as="{as_type}">')
            elif asset_path.endswith(".css"):
                as_type = "style"
                preload_tags.append(f'<link rel="preload" href="{asset_url}" as="{as_type}">')
            elif asset_path.endswith((".woff", ".woff2", ".ttf")):
                as_type = "font"
                preload_tags.append(
                    f'<link rel="preload" href="{asset_url}" as="{as_type}" crossorigin>'
                )

        return "\n".join(preload_tags)

    def add_cache_buster(self, url: str) -> str:
        """Add cache buster to URL"""
        if not self.cache_buster_enabled:
            return url

        # Use build timestamp or app version as cache buster
        cache_buster = self.get_cache_buster()
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}v={cache_buster}"

    def get_cache_buster(self) -> str:
        """Get cache buster value"""
        # Use build timestamp from manifest if available
        if "_build_info" in self.manifest:
            return str(self.manifest["_build_info"].get("build_timestamp", ""))

        # Fallback to app version or current timestamp
        if self.app:
            return self.app.config.get("VERSION", "1.0.0")

        import time

        return str(int(time.time()))

    def get_asset_info(self, asset_path: str) -> dict:
        """Get detailed information about an asset"""
        info = {
            "original_path": asset_path,
            "optimized_path": self.manifest.get(asset_path),
            "exists_optimized": asset_path in self.manifest,
            "url": self.asset_url(asset_path),
            "production_mode": self.production_mode,
        }

        return info

    def get_build_info(self) -> dict:
        """Get build information from manifest"""
        return self.manifest.get("_build_info", {})

    def reload_manifest(self):
        """Reload asset manifest (useful for development)"""
        self.load_manifest()
        logger.info("Asset manifest reloaded")

    def get_asset_list(self, filter_type: str | None = None) -> dict[str, str]:
        """
        Get list of all assets, optionally filtered by type

        Args:
            filter_type: Filter by file extension (e.g., 'js', 'css')
        """
        assets = {k: v for k, v in self.manifest.items() if not k.startswith("_")}

        if filter_type:
            assets = {k: v for k, v in assets.items() if k.endswith(f".{filter_type}")}

        return assets

    def generate_integrity_hash(self, asset_path: str) -> str | None:
        """Generate SRI integrity hash for asset (if file exists)"""
        try:
            if self.production_mode and asset_path in self.manifest:
                # Use optimized asset
                file_path = Path("static") / self.manifest[asset_path]
            else:
                file_path = Path("static") / asset_path

            if not file_path.exists():
                return None

            import base64
            import hashlib

            with open(file_path, "rb") as f:
                content = f.read()
                hash_value = hashlib.sha384(content).digest()
                return f"sha384-{base64.b64encode(hash_value).decode('utf-8')}"

        except Exception as e:
            logger.warning(f"Failed to generate integrity hash for {asset_path}: {e}")
            return None


# Global instance
asset_loader = AssetLoader()


def init_asset_loader(app, **kwargs):
    """Initialize asset loader with Flask app"""
    asset_loader.init_app(app)
    return asset_loader


# Template helper functions for backward compatibility
def get_asset_url(asset_path: str) -> str:
    """Get asset URL (template function)"""
    return asset_loader.asset_url(asset_path)


def get_js_module_tag(module_path: str, critical: bool = False) -> str:
    """Get JavaScript module tag (template function)"""
    return asset_loader.js_module(module_path, critical)


def get_critical_js() -> str:
    """Get critical JavaScript bundle (template function)"""
    return asset_loader.critical_js()


def get_css_bundle(bundle_name: str = "main") -> str:
    """Get CSS bundle (template function)"""
    return asset_loader.css_bundle(bundle_name)
