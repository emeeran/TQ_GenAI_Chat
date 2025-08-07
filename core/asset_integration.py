"""
Flask integration for asset optimization pipeline
Integrates asset loader with the main Flask application
"""

import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from core.asset_loader import init_asset_loader

logger = logging.getLogger(__name__)

# Create blueprint for asset management
assets_bp = Blueprint("assets", __name__, url_prefix="/assets")


@assets_bp.route("/build", methods=["POST"])
def build_assets():
    """
    Trigger asset build process
    Requires admin/development permissions
    """
    if not current_app.config.get("DEBUG") and not current_app.config.get(
        "ALLOW_ASSET_BUILDS", False
    ):
        return jsonify({"error": "Asset builds not allowed in production"}), 403

    try:
        from scripts.build_assets import ModularAssetBuilder

        # Get build configuration
        build_config = request.json or {}
        environment = build_config.get("environment", "development")
        force_rebuild = build_config.get("force_rebuild", False)

        # Initialize builder
        builder = ModularAssetBuilder(environment=environment)

        # Run build
        build_info = builder.build_assets(force_rebuild=force_rebuild)

        # Reload asset manifest in app
        current_app.asset_loader.reload_manifest()

        return jsonify({"success": True, "build_info": build_info, "environment": environment})

    except Exception as e:
        logger.error(f"Asset build failed: {e}")
        return jsonify({"error": f"Build failed: {str(e)}"}), 500


@assets_bp.route("/manifest", methods=["GET"])
def get_asset_manifest():
    """Get current asset manifest"""
    try:
        return jsonify(
            {
                "success": True,
                "manifest": current_app.asset_loader.manifest,
                "build_info": current_app.asset_loader.get_build_info(),
                "production_mode": current_app.asset_loader.production_mode,
            }
        )
    except Exception as e:
        logger.error(f"Failed to get asset manifest: {e}")
        return jsonify({"error": str(e)}), 500


@assets_bp.route("/info/<path:asset_path>", methods=["GET"])
def get_asset_info(asset_path):
    """Get information about a specific asset"""
    try:
        asset_info = current_app.asset_loader.get_asset_info(asset_path)
        return jsonify({"success": True, "asset_info": asset_info})
    except Exception as e:
        logger.error(f"Failed to get asset info for {asset_path}: {e}")
        return jsonify({"error": str(e)}), 500


@assets_bp.route("/reload", methods=["POST"])
def reload_manifest():
    """Reload asset manifest (development only)"""
    if not current_app.config.get("DEBUG"):
        return jsonify({"error": "Manifest reload only allowed in debug mode"}), 403

    try:
        current_app.asset_loader.reload_manifest()
        return jsonify(
            {
                "success": True,
                "message": "Asset manifest reloaded",
                "assets_count": len(current_app.asset_loader.manifest),
            }
        )
    except Exception as e:
        logger.error(f"Failed to reload asset manifest: {e}")
        return jsonify({"error": str(e)}), 500


def integrate_asset_optimization(app):
    """
    Integrate asset optimization with Flask app

    This function:
    1. Initializes the asset loader
    2. Registers the assets blueprint
    3. Sets up template functions
    4. Configures production settings
    """

    # Initialize asset loader
    asset_loader = init_asset_loader(app)

    # Store reference in app for easy access
    app.asset_loader = asset_loader

    # Register blueprint (only in debug mode or if explicitly enabled)
    if app.config.get("DEBUG") or app.config.get("ENABLE_ASSET_API", False):
        app.register_blueprint(assets_bp)
        logger.info("Asset management API enabled")

    # Set up asset directories
    setup_asset_directories(app)

    # Configure asset optimization settings
    configure_asset_settings(app)

    # Add template context processor for asset functions
    @app.context_processor
    def inject_asset_functions():
        """Inject asset helper functions into templates"""
        return {
            "asset_url": asset_loader.asset_url,
            "js_module": asset_loader.js_module,
            "css_bundle": asset_loader.css_bundle,
            "critical_js": asset_loader.critical_js,
            "preload_assets": asset_loader.preload_assets,
            "asset_integrity": asset_loader.generate_integrity_hash,
        }

    # Set up development asset watching (if in debug mode)
    if app.config.get("DEBUG") and app.config.get("WATCH_ASSETS", True):
        setup_asset_watching(app, asset_loader)

    logger.info(f"Asset optimization integrated (production: {asset_loader.production_mode})")
    return asset_loader


def setup_asset_directories(app):
    """Ensure asset directories exist"""
    static_dir = Path(app.static_folder)

    # Create required directories
    directories = [
        static_dir / "dist",
        static_dir / "bundles",
        static_dir / "js" / "core",
        static_dir / "js" / "utils",
        static_dir / "css",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Asset directories set up in {static_dir}")


def configure_asset_settings(app):
    """Configure asset optimization settings"""

    # Default asset settings
    asset_defaults = {
        "ASSET_MANIFEST_PATH": "static/dist/manifest.json",
        "ASSET_CACHE_BUSTER": True,
        "ASSET_PRODUCTION_MODE": app.config.get("ENV") == "production",
        "ASSET_BUILD_ON_START": False,  # Set to True to build on startup
        "ASSET_COMPRESSION": True,
        "ASSET_MINIFICATION": True,
        "WATCH_ASSETS": app.config.get("DEBUG", False),
    }

    # Apply defaults if not already set
    for key, value in asset_defaults.items():
        if key not in app.config:
            app.config[key] = value

    # Production-specific settings
    if app.config.get("ASSET_PRODUCTION_MODE"):
        app.config.update(
            {
                "ASSET_BUILD_ON_START": True,  # Build on production startup
                "ASSET_CACHE_BUSTER": True,
                "SEND_FILE_MAX_AGE_DEFAULT": 31536000,  # 1 year cache for static assets
                "WATCH_ASSETS": False,
            }
        )

    logger.debug("Asset optimization settings configured")


def setup_asset_watching(app, asset_loader):
    """Set up file watching for development (if watchdog is available)"""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class AssetChangeHandler(FileSystemEventHandler):
            def __init__(self, asset_loader):
                self.asset_loader = asset_loader
                self.last_reload = 0

            def on_modified(self, event):
                if event.is_directory:
                    return

                # Only watch relevant asset files
                if not any(event.src_path.endswith(ext) for ext in [".js", ".css", ".json"]):
                    return

                # Prevent rapid reloads
                import time

                now = time.time()
                if now - self.last_reload < 1:  # 1 second debounce
                    return

                logger.debug(f"Asset file changed: {event.src_path}")
                self.asset_loader.reload_manifest()
                self.last_reload = now

        # Set up file watcher
        observer = Observer()
        handler = AssetChangeHandler(asset_loader)

        # Watch static directories
        static_dir = Path(app.static_folder)
        watch_paths = [static_dir / "js", static_dir / "css", static_dir / "dist"]

        for path in watch_paths:
            if path.exists():
                observer.schedule(handler, str(path), recursive=True)

        observer.start()
        logger.info("Asset file watching enabled for development")

        # Store observer reference to prevent garbage collection
        app._asset_observer = observer

    except ImportError:
        logger.debug("Watchdog not available, asset watching disabled")


def trigger_production_build(app):
    """
    Trigger production asset build on application startup
    Used in production environments
    """
    if not app.config.get("ASSET_BUILD_ON_START"):
        return

    try:
        from scripts.build_assets import ModularAssetBuilder

        logger.info("Starting production asset build...")

        builder = ModularAssetBuilder(environment="production")
        build_info = builder.build_assets(force_rebuild=True)

        # Reload manifest
        app.asset_loader.reload_manifest()

        logger.info(
            f"Production assets built successfully: {len(build_info.get('assets', {}))} files"
        )

    except Exception as e:
        logger.error(f"Production asset build failed: {e}")
        # Don't fail app startup, just log the error


# Helper function for backward compatibility
def init_assets(app):
    """Initialize asset optimization (backward compatibility)"""
    return integrate_asset_optimization(app)


# Context processor for template functions
def get_asset_context():
    """Get asset template context"""
    try:
        asset_loader = current_app.asset_loader
        return {
            "asset_url": asset_loader.asset_url,
            "js_module": asset_loader.js_module,
            "css_bundle": asset_loader.css_bundle,
            "critical_js": asset_loader.critical_js,
            "preload_assets": asset_loader.preload_assets,
        }
    except Exception as e:
        logger.warning(f"Failed to get asset context: {e}")
        return {}
