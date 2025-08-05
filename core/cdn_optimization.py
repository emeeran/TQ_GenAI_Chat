"""
CDN integration and static asset optimization for TQ GenAI Chat application.
Provides efficient asset delivery, caching, and optimization.
"""

import asyncio
import gzip
import hashlib
import json
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any

import aiofiles
import aiohttp

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import csscompressor
    import jsmin
    MINIFICATION_AVAILABLE = True
except ImportError:
    MINIFICATION_AVAILABLE = False

logger = logging.getLogger(__name__)


class AssetOptimizer:
    """
    Optimizes static assets (CSS, JS, images) for better performance.
    """

    def __init__(self, source_dir: str = "static", output_dir: str = "static/optimized"):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Asset processing configuration
        self.image_quality = 85
        self.enable_webp = True
        self.enable_compression = True
        self.cache_busting = True

        # File hashes for cache busting
        self.file_hashes: dict[str, str] = {}
        self.asset_manifest: dict[str, str] = {}

    async def optimize_all_assets(self) -> dict[str, Any]:
        """Optimize all assets in the source directory."""
        results = {
            "processed_files": 0,
            "total_size_before": 0,
            "total_size_after": 0,
            "compression_ratio": 0.0,
            "errors": []
        }

        try:
            # Process different asset types
            await self._optimize_css_files(results)
            await self._optimize_js_files(results)
            await self._optimize_images(results)
            await self._generate_asset_manifest()

            # Calculate compression ratio
            if results["total_size_before"] > 0:
                results["compression_ratio"] = (
                    results["total_size_before"] - results["total_size_after"]
                ) / results["total_size_before"]

            logger.info(f"Asset optimization completed: {results['compression_ratio']:.2%} reduction")

        except Exception as e:
            logger.error(f"Asset optimization failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _optimize_css_files(self, results: dict):
        """Optimize CSS files."""
        css_files = self.source_dir.glob("**/*.css")

        for css_file in css_files:
            try:
                # Skip already optimized files
                if "optimized" in str(css_file) or "min" in css_file.stem:
                    continue

                original_size = css_file.stat().st_size
                results["total_size_before"] += original_size

                # Read and minify CSS
                async with aiofiles.open(css_file, encoding='utf-8') as f:
                    css_content = await f.read()

                if MINIFICATION_AVAILABLE:
                    minified_css = csscompressor.compress(css_content)
                else:
                    # Basic minification if csscompressor not available
                    minified_css = self._basic_css_minify(css_content)

                # Generate file hash for cache busting
                file_hash = self._generate_file_hash(minified_css)

                # Create output filename
                output_name = f"{css_file.stem}.{file_hash[:8]}.min.css"
                output_path = self.output_dir / output_name

                # Write optimized file
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write(minified_css)

                # Compress with gzip
                if self.enable_compression:
                    await self._create_gzipped_version(output_path, minified_css)

                optimized_size = len(minified_css.encode('utf-8'))
                results["total_size_after"] += optimized_size
                results["processed_files"] += 1

                # Update asset manifest
                relative_path = str(css_file.relative_to(self.source_dir))
                self.asset_manifest[relative_path] = f"optimized/{output_name}"

                logger.info(f"Optimized {css_file.name}: {original_size} → {optimized_size} bytes")

            except Exception as e:
                logger.error(f"Failed to optimize CSS {css_file}: {e}")
                results["errors"].append(f"CSS {css_file.name}: {e}")

    async def _optimize_js_files(self, results: dict):
        """Optimize JavaScript files."""
        js_files = self.source_dir.glob("**/*.js")

        for js_file in js_files:
            try:
                # Skip already optimized files
                if "optimized" in str(js_file) or "min" in js_file.stem:
                    continue

                original_size = js_file.stat().st_size
                results["total_size_before"] += original_size

                # Read and minify JavaScript
                async with aiofiles.open(js_file, encoding='utf-8') as f:
                    js_content = await f.read()

                if MINIFICATION_AVAILABLE:
                    minified_js = jsmin.jsmin(js_content)
                else:
                    # Basic minification if jsmin not available
                    minified_js = self._basic_js_minify(js_content)

                # Generate file hash for cache busting
                file_hash = self._generate_file_hash(minified_js)

                # Create output filename
                output_name = f"{js_file.stem}.{file_hash[:8]}.min.js"
                output_path = self.output_dir / output_name

                # Write optimized file
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write(minified_js)

                # Compress with gzip
                if self.enable_compression:
                    await self._create_gzipped_version(output_path, minified_js)

                optimized_size = len(minified_js.encode('utf-8'))
                results["total_size_after"] += optimized_size
                results["processed_files"] += 1

                # Update asset manifest
                relative_path = str(js_file.relative_to(self.source_dir))
                self.asset_manifest[relative_path] = f"optimized/{output_name}"

                logger.info(f"Optimized {js_file.name}: {original_size} → {optimized_size} bytes")

            except Exception as e:
                logger.error(f"Failed to optimize JS {js_file}: {e}")
                results["errors"].append(f"JS {js_file.name}: {e}")

    async def _optimize_images(self, results: dict):
        """Optimize image files."""
        if not PIL_AVAILABLE:
            logger.warning("PIL not available - skipping image optimization")
            return

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        image_files = []

        for ext in image_extensions:
            image_files.extend(self.source_dir.glob(f"**/*{ext}"))

        for image_file in image_files:
            try:
                # Skip already optimized files
                if "optimized" in str(image_file):
                    continue

                original_size = image_file.stat().st_size
                results["total_size_before"] += original_size

                # Open and optimize image
                with Image.open(image_file) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                        img = background

                    # Generate file hash
                    img_bytes = img.tobytes()
                    file_hash = self._generate_file_hash(img_bytes)

                    # Create optimized versions
                    base_name = image_file.stem

                    # Original format optimization
                    if image_file.suffix.lower() in {'.jpg', '.jpeg'}:
                        output_name = f"{base_name}.{file_hash[:8]}.jpg"
                        output_path = self.output_dir / output_name
                        img.save(output_path, 'JPEG', quality=self.image_quality, optimize=True)
                    else:
                        output_name = f"{base_name}.{file_hash[:8]}.png"
                        output_path = self.output_dir / output_name
                        img.save(output_path, 'PNG', optimize=True)

                    optimized_size = output_path.stat().st_size

                    # Create WebP version if enabled
                    if self.enable_webp:
                        webp_name = f"{base_name}.{file_hash[:8]}.webp"
                        webp_path = self.output_dir / webp_name
                        img.save(webp_path, 'WEBP', quality=self.image_quality)

                        # Use WebP if it's smaller
                        webp_size = webp_path.stat().st_size
                        if webp_size < optimized_size:
                            output_name = webp_name
                            optimized_size = webp_size
                            output_path.unlink()  # Remove the original optimized version

                    results["total_size_after"] += optimized_size
                    results["processed_files"] += 1

                    # Update asset manifest
                    relative_path = str(image_file.relative_to(self.source_dir))
                    self.asset_manifest[relative_path] = f"optimized/{output_name}"

                    logger.info(f"Optimized {image_file.name}: {original_size} → {optimized_size} bytes")

            except Exception as e:
                logger.error(f"Failed to optimize image {image_file}: {e}")
                results["errors"].append(f"Image {image_file.name}: {e}")

    async def _create_gzipped_version(self, file_path: Path, content: str):
        """Create gzipped version of a file."""
        gzip_path = file_path.with_suffix(file_path.suffix + '.gz')

        compressed_content = gzip.compress(content.encode('utf-8'))

        async with aiofiles.open(gzip_path, 'wb') as f:
            await f.write(compressed_content)

    async def _generate_asset_manifest(self):
        """Generate asset manifest for cache busting."""
        manifest_path = self.output_dir / "manifest.json"

        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(self.asset_manifest, indent=2))

        logger.info(f"Generated asset manifest with {len(self.asset_manifest)} entries")

    def _generate_file_hash(self, content: Any) -> str:
        """Generate SHA-256 hash for file content."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def _basic_css_minify(self, css: str) -> str:
        """Basic CSS minification."""
        # Remove comments
        import re
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)

        # Remove whitespace
        css = re.sub(r'\s+', ' ', css)
        css = re.sub(r';\s*}', '}', css)
        css = re.sub(r'{\s*', '{', css)
        css = re.sub(r';\s*', ';', css)

        return css.strip()

    def _basic_js_minify(self, js: str) -> str:
        """Basic JavaScript minification."""
        # Remove comments (simple approach)
        import re
        js = re.sub(r'//.*?\n', '\n', js)
        js = re.sub(r'/\*.*?\*/', '', js, flags=re.DOTALL)

        # Remove excess whitespace
        js = re.sub(r'\n\s*\n', '\n', js)
        js = re.sub(r'\s+', ' ', js)

        return js.strip()


class CDNManager:
    """
    Manages CDN integration for asset delivery and caching.
    """

    def __init__(self, cdn_config: dict = None):
        self.cdn_config = cdn_config or {}
        self.base_url = self.cdn_config.get('base_url', '')
        self.api_key = self.cdn_config.get('api_key', '')
        self.distribution_id = self.cdn_config.get('distribution_id', '')

        # Caching configuration
        self.cache_control_rules = {
            'css': 'public, max-age=31536000',  # 1 year
            'js': 'public, max-age=31536000',   # 1 year
            'images': 'public, max-age=2592000',  # 30 days
            'fonts': 'public, max-age=31536000',  # 1 year
            'html': 'public, max-age=3600',     # 1 hour
        }

        # Session for HTTP requests
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        """Initialize CDN manager."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        logger.info("CDN manager initialized")

    async def stop(self):
        """Cleanup CDN manager."""
        if self.session:
            await self.session.close()
        logger.info("CDN manager stopped")

    async def upload_assets(self, source_dir: str) -> dict[str, Any]:
        """Upload optimized assets to CDN."""
        results = {
            "uploaded_files": 0,
            "failed_uploads": 0,
            "total_size": 0,
            "errors": []
        }

        source_path = Path(source_dir)

        if not source_path.exists():
            logger.error(f"Source directory {source_dir} does not exist")
            return results

        # Upload all files in the directory
        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                try:
                    await self._upload_file(file_path, results)
                except Exception as e:
                    logger.error(f"Failed to upload {file_path}: {e}")
                    results["failed_uploads"] += 1
                    results["errors"].append(f"{file_path.name}: {e}")

        logger.info(f"CDN upload completed: {results['uploaded_files']} files")
        return results

    async def _upload_file(self, file_path: Path, results: dict):
        """Upload a single file to CDN."""
        # This is a generic implementation - specific CDN providers
        # (AWS CloudFront, Cloudflare, etc.) would have their own APIs

        file_size = file_path.stat().st_size
        content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'

        # Determine cache control based on file type
        file_ext = file_path.suffix.lower()
        cache_control = self._get_cache_control(file_ext)

        # Read file content
        async with aiofiles.open(file_path, 'rb') as f:
            file_content = await f.read()

        # Upload to CDN (this would be CDN-specific)
        await self._cdn_upload_request(file_path, file_content, content_type, cache_control)

        results["uploaded_files"] += 1
        results["total_size"] += file_size

        logger.info(f"Uploaded {file_path.name} ({file_size} bytes)")

    async def _cdn_upload_request(self, file_path: Path, content: bytes, content_type: str, cache_control: str):
        """Make the actual CDN upload request."""
        # This is a placeholder - implement specific CDN API calls here
        # For AWS S3/CloudFront:
        # - Use boto3 to upload to S3
        # - Set appropriate headers for caching

        # For Cloudflare:
        # - Use Cloudflare API to upload files
        # - Configure caching rules

        # For Azure CDN:
        # - Use Azure SDK to upload to blob storage
        # - Configure CDN endpoint

        logger.debug(f"CDN upload: {file_path.name} with cache-control: {cache_control}")

        # Simulate upload delay
        await asyncio.sleep(0.1)

    async def invalidate_cache(self, paths: list[str]) -> bool:
        """Invalidate CDN cache for specific paths."""
        try:
            # This would be CDN-specific invalidation
            logger.info(f"Invalidating CDN cache for {len(paths)} paths")

            # Simulate invalidation
            await asyncio.sleep(1)

            return True

        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return False

    def _get_cache_control(self, file_ext: str) -> str:
        """Get appropriate cache control header for file type."""
        if file_ext in {'.css', '.scss'}:
            return self.cache_control_rules['css']
        elif file_ext in {'.js', '.ts'}:
            return self.cache_control_rules['js']
        elif file_ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico'}:
            return self.cache_control_rules['images']
        elif file_ext in {'.woff', '.woff2', '.ttf', '.eot'}:
            return self.cache_control_rules['fonts']
        elif file_ext in {'.html', '.htm'}:
            return self.cache_control_rules['html']
        else:
            return 'public, max-age=86400'  # 1 day default

    def get_asset_url(self, asset_path: str) -> str:
        """Get CDN URL for an asset."""
        if self.base_url:
            return f"{self.base_url.rstrip('/')}/{asset_path.lstrip('/')}"
        return asset_path


class AssetManager:
    """
    Main asset management system combining optimization and CDN delivery.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        self.optimizer = AssetOptimizer(
            source_dir=self.config.get('source_dir', 'static'),
            output_dir=self.config.get('output_dir', 'static/optimized')
        )

        self.cdn_manager = CDNManager(self.config.get('cdn', {}))

        # Asset manifest for URL resolution
        self.manifest: dict[str, str] = {}
        self.manifest_loaded = False

    async def start(self):
        """Initialize asset manager."""
        await self.cdn_manager.start()
        await self._load_manifest()
        logger.info("Asset manager started")

    async def stop(self):
        """Cleanup asset manager."""
        await self.cdn_manager.stop()
        logger.info("Asset manager stopped")

    async def build_and_deploy(self) -> dict[str, Any]:
        """Complete asset build and deployment pipeline."""
        results = {
            "optimization": {},
            "upload": {},
            "total_time": 0,
            "success": False
        }

        start_time = time.time()

        try:
            # Step 1: Optimize assets
            logger.info("Starting asset optimization...")
            optimization_results = await self.optimizer.optimize_all_assets()
            results["optimization"] = optimization_results

            # Step 2: Upload to CDN
            if self.cdn_manager.base_url:
                logger.info("Uploading assets to CDN...")
                upload_results = await self.cdn_manager.upload_assets(
                    self.optimizer.output_dir
                )
                results["upload"] = upload_results
            else:
                logger.info("No CDN configured, skipping upload")
                results["upload"] = {"message": "CDN not configured"}

            # Step 3: Reload manifest
            await self._load_manifest()

            results["success"] = True
            results["total_time"] = time.time() - start_time

            logger.info(f"Asset build and deploy completed in {results['total_time']:.2f}s")

        except Exception as e:
            logger.error(f"Asset build and deploy failed: {e}")
            results["error"] = str(e)
            results["total_time"] = time.time() - start_time

        return results

    async def _load_manifest(self):
        """Load asset manifest for URL resolution."""
        manifest_path = self.optimizer.output_dir / "manifest.json"

        if manifest_path.exists():
            try:
                async with aiofiles.open(manifest_path) as f:
                    content = await f.read()
                    self.manifest = json.loads(content)
                    self.manifest_loaded = True
                    logger.info(f"Loaded asset manifest with {len(self.manifest)} entries")
            except Exception as e:
                logger.error(f"Failed to load asset manifest: {e}")
                self.manifest = {}
        else:
            logger.warning("Asset manifest not found")

    def get_asset_url(self, asset_path: str) -> str:
        """Get optimized URL for an asset with CDN support."""
        # Check if we have an optimized version
        if self.manifest_loaded and asset_path in self.manifest:
            optimized_path = self.manifest[asset_path]
            return self.cdn_manager.get_asset_url(optimized_path)

        # Fall back to original asset
        return self.cdn_manager.get_asset_url(asset_path)

    def get_preload_links(self, critical_assets: list[str]) -> list[str]:
        """Generate preload link tags for critical assets."""
        preload_links = []

        for asset_path in critical_assets:
            asset_url = self.get_asset_url(asset_path)

            # Determine resource type
            if asset_path.endswith('.css'):
                rel_type = 'preload'
                as_type = 'style'
            elif asset_path.endswith('.js'):
                rel_type = 'preload'
                as_type = 'script'
            elif any(asset_path.endswith(ext) for ext in ['.woff', '.woff2', '.ttf']):
                rel_type = 'preload'
                as_type = 'font'
                crossorigin = ' crossorigin'
            else:
                continue  # Skip unknown types

            crossorigin = ' crossorigin' if as_type == 'font' else ''
            preload_links.append(
                f'<link rel="{rel_type}" as="{as_type}" href="{asset_url}"{crossorigin}>'
            )

        return preload_links

    def get_resource_hints(self) -> list[str]:
        """Generate resource hints for better performance."""
        hints = []

        # DNS prefetch for CDN
        if self.cdn_manager.base_url:
            cdn_domain = self.cdn_manager.base_url.split('/')[2]
            hints.append(f'<link rel="dns-prefetch" href="//{cdn_domain}">')
            hints.append(f'<link rel="preconnect" href="//{cdn_domain}" crossorigin>')

        return hints


# Flask integration helper
class FlaskAssetHelper:
    """Helper for integrating asset management with Flask."""

    def __init__(self, app=None, asset_manager: AssetManager = None):
        self.app = app
        self.asset_manager = asset_manager

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize Flask app with asset helper."""
        app.jinja_env.globals['asset_url'] = self.asset_url
        app.jinja_env.globals['preload_assets'] = self.preload_assets
        app.jinja_env.globals['resource_hints'] = self.resource_hints

    def asset_url(self, asset_path: str) -> str:
        """Template function to get asset URL."""
        if self.asset_manager:
            return self.asset_manager.get_asset_url(asset_path)
        return asset_path

    def preload_assets(self, *asset_paths: str) -> str:
        """Template function to generate preload links."""
        if self.asset_manager:
            links = self.asset_manager.get_preload_links(list(asset_paths))
            return '\n'.join(links)
        return ''

    def resource_hints(self) -> str:
        """Template function to generate resource hints."""
        if self.asset_manager:
            hints = self.asset_manager.get_resource_hints()
            return '\n'.join(hints)
        return ''


# Global asset manager instance
_asset_manager = None

def get_asset_manager(config: dict = None) -> AssetManager:
    """Get or create the global asset manager instance."""
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = AssetManager(config)
    return _asset_manager


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Example configuration
        config = {
            'source_dir': 'static',
            'output_dir': 'static/optimized',
            'cdn': {
                'base_url': 'https://cdn.example.com',
                'api_key': 'your-cdn-api-key',
                'distribution_id': 'your-distribution-id'
            }
        }

        # Create and start asset manager
        asset_manager = get_asset_manager(config)
        await asset_manager.start()

        # Build and deploy assets
        await asset_manager.build_and_deploy()

        # Get optimized URLs
        asset_manager.get_asset_url('styles.css')
        asset_manager.get_asset_url('script.js')


        await asset_manager.stop()

    asyncio.run(main())
