#!/usr/bin/env python3
"""
Enhanced Asset Optimization Pipeline for TQ GenAI Chat

This module implements Task 2.1.2: Asset Optimization Pipeline
- JavaScript minification and source maps
- CSS optimization and compression
- Image optimization (WebP conversion, compression)
- Asset versioning and cache busting
- Production build system

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import gzip
import hashlib
import json
import logging
import mimetypes
import shutil
import time
from pathlib import Path
from typing import Any

import aiofiles

# Optional dependencies for enhanced optimization
try:
    from PIL import Image, ImageOptim

    PIL_AVAILABLE = True
except ImportError:
    try:
        from PIL import Image

        PIL_AVAILABLE = True
        ImageOptim = None
    except ImportError:
        PIL_AVAILABLE = False
        Image = None
        ImageOptim = None

try:
    import csscompressor

    CSS_COMPRESSOR_AVAILABLE = True
except ImportError:
    CSS_COMPRESSOR_AVAILABLE = False

try:
    import jsmin

    JSMIN_AVAILABLE = True
except ImportError:
    JSMIN_AVAILABLE = False

logger = logging.getLogger(__name__)


class BuildConfig:
    """Configuration for the build process"""

    def __init__(
        self,
        source_dir: str = "static",
        output_dir: str = "static/dist",
        enable_minification: bool = True,
        enable_compression: bool = True,
        enable_source_maps: bool = True,
        enable_cache_busting: bool = True,
        enable_image_optimization: bool = True,
        enable_webp_conversion: bool = True,
        image_quality: int = 85,
        webp_quality: int = 80,
        compression_level: int = 6,
    ):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.enable_minification = enable_minification
        self.enable_compression = enable_compression
        self.enable_source_maps = enable_source_maps
        self.enable_cache_busting = enable_cache_busting
        self.enable_image_optimization = enable_image_optimization
        self.enable_webp_conversion = enable_webp_conversion
        self.image_quality = image_quality
        self.webp_quality = webp_quality
        self.compression_level = compression_level

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)


class AssetManifest:
    """Manages asset manifest for cache busting and version tracking"""

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.manifest: dict[str, dict[str, Any]] = {}
        self.load_manifest()

    def load_manifest(self):
        """Load existing manifest or create new one"""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path) as f:
                    self.manifest = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load manifest: {e}")
                self.manifest = {}
        else:
            self.manifest = {}

    def add_asset(
        self,
        original_path: str,
        optimized_path: str,
        file_hash: str,
        original_size: int,
        optimized_size: int,
        mime_type: str,
    ):
        """Add asset to manifest"""
        self.manifest[original_path] = {
            "optimized_path": optimized_path,
            "hash": file_hash,
            "original_size": original_size,
            "optimized_size": optimized_size,
            "compression_ratio": (original_size - optimized_size) / original_size
            if original_size > 0
            else 0,
            "mime_type": mime_type,
            "last_modified": time.time(),
        }

    def get_asset_url(self, original_path: str) -> str | None:
        """Get optimized asset URL"""
        asset = self.manifest.get(original_path)
        return asset["optimized_path"] if asset else None

    def save_manifest(self):
        """Save manifest to file"""
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def get_stats(self) -> dict[str, Any]:
        """Get build statistics"""
        if not self.manifest:
            return {"total_assets": 0, "total_compression_ratio": 0}

        total_original = sum(asset["original_size"] for asset in self.manifest.values())
        total_optimized = sum(asset["optimized_size"] for asset in self.manifest.values())

        return {
            "total_assets": len(self.manifest),
            "total_original_size": total_original,
            "total_optimized_size": total_optimized,
            "total_compression_ratio": (total_original - total_optimized) / total_original
            if total_original > 0
            else 0,
            "assets_by_type": self._get_assets_by_type(),
        }

    def _get_assets_by_type(self) -> dict[str, int]:
        """Get asset count by type"""
        types = {}
        for asset in self.manifest.values():
            mime_type = asset["mime_type"].split("/")[0]
            types[mime_type] = types.get(mime_type, 0) + 1
        return types


class JavaScriptOptimizer:
    """Optimizes JavaScript files with minification and source maps"""

    def __init__(self, config: BuildConfig):
        self.config = config

    async def optimize_file(self, file_path: Path, output_dir: Path) -> tuple[Path, dict[str, Any]]:
        """Optimize a single JavaScript file"""
        try:
            # Read source file
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                source_content = await f.read()

            original_size = len(source_content.encode("utf-8"))

            # Generate file hash for cache busting
            file_hash = hashlib.sha256(source_content.encode()).hexdigest()[:8]

            # Create output filename
            base_name = file_path.stem
            if self.config.enable_cache_busting:
                output_name = f"{base_name}.{file_hash}.min.js"
            else:
                output_name = f"{base_name}.min.js"

            output_path = output_dir / output_name

            # Minify JavaScript
            if self.config.enable_minification:
                minified_content = await self._minify_javascript(source_content, file_path)
            else:
                minified_content = source_content

            # Write optimized file
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(minified_content)

            optimized_size = len(minified_content.encode("utf-8"))

            # Generate source map if enabled
            source_map_path = None
            if self.config.enable_source_maps:
                source_map_path = await self._generate_source_map(
                    file_path, output_path, source_content, minified_content
                )

            # Create gzipped version if compression enabled
            gzipped_path = None
            if self.config.enable_compression:
                gzipped_path = await self._create_gzipped_version(output_path, minified_content)

            return output_path, {
                "original_size": original_size,
                "optimized_size": optimized_size,
                "file_hash": file_hash,
                "source_map": str(source_map_path) if source_map_path else None,
                "gzipped": str(gzipped_path) if gzipped_path else None,
                "compression_ratio": (original_size - optimized_size) / original_size
                if original_size > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"Failed to optimize JavaScript {file_path}: {e}")
            raise

    async def _minify_javascript(self, content: str, file_path: Path) -> str:
        """Minify JavaScript content"""
        if JSMIN_AVAILABLE:
            try:
                return jsmin.jsmin(content)
            except Exception as e:
                logger.warning(f"jsmin failed for {file_path}, using basic minification: {e}")

        # Basic minification fallback
        return self._basic_js_minify(content)

    def _basic_js_minify(self, content: str) -> str:
        """Basic JavaScript minification"""
        lines = []
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("//"):  # Remove empty lines and comments
                lines.append(line)
        return " ".join(lines)

    async def _generate_source_map(
        self, source_path: Path, output_path: Path, source_content: str, minified_content: str
    ) -> Path | None:
        """Generate source map for debugging"""
        try:
            source_map = {
                "version": 3,
                "file": output_path.name,
                "sources": [str(source_path.relative_to(self.config.source_dir))],
                "sourcesContent": [source_content],
                "names": [],
                "mappings": "",  # Basic source map, could be enhanced with proper mapping
            }

            source_map_path = output_path.with_suffix(".js.map")

            async with aiofiles.open(source_map_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(source_map, indent=2))

            # Add source map reference to minified file
            source_map_comment = f"\n//# sourceMappingURL={source_map_path.name}"
            async with aiofiles.open(output_path, "a", encoding="utf-8") as f:
                await f.write(source_map_comment)

            return source_map_path

        except Exception as e:
            logger.warning(f"Failed to generate source map for {source_path}: {e}")
            return None

    async def _create_gzipped_version(self, file_path: Path, content: str) -> Path | None:
        """Create gzipped version of the file"""
        try:
            gzipped_path = file_path.with_suffix(file_path.suffix + ".gz")

            async with aiofiles.open(gzipped_path, "wb") as f:
                compressed_content = gzip.compress(
                    content.encode("utf-8"), compresslevel=self.config.compression_level
                )
                await f.write(compressed_content)

            return gzipped_path

        except Exception as e:
            logger.warning(f"Failed to create gzipped version of {file_path}: {e}")
            return None


class CSSOptimizer:
    """Optimizes CSS files with minification and compression"""

    def __init__(self, config: BuildConfig):
        self.config = config

    async def optimize_file(self, file_path: Path, output_dir: Path) -> tuple[Path, dict[str, Any]]:
        """Optimize a single CSS file"""
        try:
            # Read source file
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                source_content = await f.read()

            original_size = len(source_content.encode("utf-8"))

            # Generate file hash for cache busting
            file_hash = hashlib.sha256(source_content.encode()).hexdigest()[:8]

            # Create output filename
            base_name = file_path.stem
            if self.config.enable_cache_busting:
                output_name = f"{base_name}.{file_hash}.min.css"
            else:
                output_name = f"{base_name}.min.css"

            output_path = output_dir / output_name

            # Minify CSS
            if self.config.enable_minification:
                minified_content = await self._minify_css(source_content)
            else:
                minified_content = source_content

            # Write optimized file
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(minified_content)

            optimized_size = len(minified_content.encode("utf-8"))

            # Create gzipped version if compression enabled
            gzipped_path = None
            if self.config.enable_compression:
                gzipped_path = await self._create_gzipped_version(output_path, minified_content)

            return output_path, {
                "original_size": original_size,
                "optimized_size": optimized_size,
                "file_hash": file_hash,
                "gzipped": str(gzipped_path) if gzipped_path else None,
                "compression_ratio": (original_size - optimized_size) / original_size
                if original_size > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"Failed to optimize CSS {file_path}: {e}")
            raise

    async def _minify_css(self, content: str) -> str:
        """Minify CSS content"""
        if CSS_COMPRESSOR_AVAILABLE:
            try:
                return csscompressor.compress(content)
            except Exception as e:
                logger.warning(f"csscompressor failed, using basic minification: {e}")

        # Basic CSS minification fallback
        return self._basic_css_minify(content)

    def _basic_css_minify(self, content: str) -> str:
        """Basic CSS minification"""
        # Remove comments
        import re

        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # Remove unnecessary whitespace
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r";\s*}", "}", content)
        content = re.sub(r"{\s*", "{", content)
        content = re.sub(r"}\s*", "}", content)
        content = re.sub(r":\s*", ":", content)
        content = re.sub(r";\s*", ";", content)

        return content.strip()

    async def _create_gzipped_version(self, file_path: Path, content: str) -> Path | None:
        """Create gzipped version of the file"""
        try:
            gzipped_path = file_path.with_suffix(file_path.suffix + ".gz")

            async with aiofiles.open(gzipped_path, "wb") as f:
                compressed_content = gzip.compress(
                    content.encode("utf-8"), compresslevel=self.config.compression_level
                )
                await f.write(compressed_content)

            return gzipped_path

        except Exception as e:
            logger.warning(f"Failed to create gzipped version of {file_path}: {e}")
            return None


class ImageOptimizer:
    """Optimizes images with compression and WebP conversion"""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.supported_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}

    async def optimize_file(
        self, file_path: Path, output_dir: Path
    ) -> tuple[list[Path], dict[str, Any]]:
        """Optimize a single image file"""
        try:
            if not PIL_AVAILABLE:
                logger.warning("PIL not available, skipping image optimization")
                return [], {}

            original_size = file_path.stat().st_size

            # Generate file hash for cache busting
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()[:8]

            outputs = []

            # Open and optimize the image
            with Image.open(file_path) as img:
                # Create optimized version in original format
                if self.config.enable_image_optimization:
                    optimized_path = await self._optimize_image(
                        img, file_path, output_dir, file_hash
                    )
                    if optimized_path:
                        outputs.append(optimized_path)

                # Create WebP version if enabled
                if self.config.enable_webp_conversion:
                    webp_path = await self._create_webp_version(
                        img, file_path, output_dir, file_hash
                    )
                    if webp_path:
                        outputs.append(webp_path)

            # Calculate total optimized size
            total_optimized_size = sum(p.stat().st_size for p in outputs)

            return outputs, {
                "original_size": original_size,
                "optimized_size": total_optimized_size,
                "file_hash": file_hash,
                "formats_created": [p.suffix for p in outputs],
                "compression_ratio": (original_size - total_optimized_size) / original_size
                if original_size > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"Failed to optimize image {file_path}: {e}")
            return [], {}

    async def _optimize_image(
        self, img: Image.Image, file_path: Path, output_dir: Path, file_hash: str
    ) -> Path | None:
        """Create optimized version in original format"""
        try:
            base_name = file_path.stem
            extension = file_path.suffix.lower()

            if self.config.enable_cache_busting:
                output_name = f"{base_name}.{file_hash}{extension}"
            else:
                output_name = f"{base_name}.opt{extension}"

            output_path = output_dir / output_name

            # Optimize based on format
            save_kwargs = {"optimize": True}

            if extension in [".jpg", ".jpeg"]:
                save_kwargs.update({"quality": self.config.image_quality, "progressive": True})
            elif extension == ".png":
                save_kwargs.update({"optimize": True, "compress_level": 6})

            # Save optimized image
            img.save(output_path, **save_kwargs)

            return output_path

        except Exception as e:
            logger.warning(f"Failed to create optimized version of {file_path}: {e}")
            return None

    async def _create_webp_version(
        self, img: Image.Image, file_path: Path, output_dir: Path, file_hash: str
    ) -> Path | None:
        """Create WebP version of the image"""
        try:
            base_name = file_path.stem

            if self.config.enable_cache_busting:
                output_name = f"{base_name}.{file_hash}.webp"
            else:
                output_name = f"{base_name}.webp"

            output_path = output_dir / output_name

            # Save as WebP
            img.save(output_path, "WebP", quality=self.config.webp_quality, optimize=True)

            return output_path

        except Exception as e:
            logger.warning(f"Failed to create WebP version of {file_path}: {e}")
            return None

    def is_supported(self, file_path: Path) -> bool:
        """Check if image format is supported"""
        return file_path.suffix.lower() in self.supported_formats


class AssetOptimizationPipeline:
    """Main asset optimization pipeline"""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.manifest = AssetManifest(config.output_dir / "manifest.json")
        self.js_optimizer = JavaScriptOptimizer(config)
        self.css_optimizer = CSSOptimizer(config)
        self.image_optimizer = ImageOptimizer(config)

        # Create subdirectories
        (config.output_dir / "js").mkdir(exist_ok=True)
        (config.output_dir / "css").mkdir(exist_ok=True)
        (config.output_dir / "images").mkdir(exist_ok=True)

    async def build_assets(self) -> dict[str, Any]:
        """Build all assets"""
        start_time = time.time()
        results = {
            "start_time": start_time,
            "processed_files": 0,
            "errors": [],
            "javascript": {"count": 0, "size_before": 0, "size_after": 0},
            "css": {"count": 0, "size_before": 0, "size_after": 0},
            "images": {"count": 0, "size_before": 0, "size_after": 0},
        }

        try:
            logger.info("Starting asset optimization pipeline...")

            # Process JavaScript files
            await self._process_javascript_files(results)

            # Process CSS files
            await self._process_css_files(results)

            # Process image files
            await self._process_image_files(results)

            # Save manifest
            self.manifest.save_manifest()

            # Calculate totals
            build_time = time.time() - start_time
            results.update(
                {
                    "build_time": build_time,
                    "total_size_before": sum(
                        results[t]["size_before"] for t in ["javascript", "css", "images"]
                    ),
                    "total_size_after": sum(
                        results[t]["size_after"] for t in ["javascript", "css", "images"]
                    ),
                    "manifest_stats": self.manifest.get_stats(),
                }
            )

            # Calculate overall compression ratio
            if results["total_size_before"] > 0:
                results["compression_ratio"] = (
                    results["total_size_before"] - results["total_size_after"]
                ) / results["total_size_before"]
            else:
                results["compression_ratio"] = 0

            logger.info(
                f"Asset optimization completed in {build_time:.2f}s. "
                f"Compression: {results['compression_ratio']:.2%}"
            )

        except Exception as e:
            logger.error(f"Asset optimization pipeline failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _process_javascript_files(self, results: dict[str, Any]):
        """Process all JavaScript files"""
        js_files = list(self.config.source_dir.glob("**/*.js"))

        # Filter out already minified files and build output
        js_files = [
            f
            for f in js_files
            if not any(
                skip in str(f) for skip in ["min.js", "dist/", "optimized/", "node_modules/"]
            )
        ]

        logger.info(f"Processing {len(js_files)} JavaScript files...")

        for js_file in js_files:
            try:
                output_path, optimization_info = await self.js_optimizer.optimize_file(
                    js_file, self.config.output_dir / "js"
                )

                # Update results
                results["javascript"]["count"] += 1
                results["javascript"]["size_before"] += optimization_info["original_size"]
                results["javascript"]["size_after"] += optimization_info["optimized_size"]
                results["processed_files"] += 1

                # Add to manifest
                relative_path = str(js_file.relative_to(self.config.source_dir))
                optimized_relative = str(output_path.relative_to(self.config.output_dir))

                self.manifest.add_asset(
                    relative_path,
                    optimized_relative,
                    optimization_info["file_hash"],
                    optimization_info["original_size"],
                    optimization_info["optimized_size"],
                    "application/javascript",
                )

                logger.debug(
                    f"Optimized {js_file.name}: {optimization_info['compression_ratio']:.1%} reduction"
                )

            except Exception as e:
                logger.error(f"Failed to process JavaScript file {js_file}: {e}")
                results["errors"].append(f"JS {js_file.name}: {str(e)}")

    async def _process_css_files(self, results: dict[str, Any]):
        """Process all CSS files"""
        css_files = list(self.config.source_dir.glob("**/*.css"))

        # Filter out already minified files and build output
        css_files = [
            f
            for f in css_files
            if not any(skip in str(f) for skip in ["min.css", "dist/", "optimized/"])
        ]

        logger.info(f"Processing {len(css_files)} CSS files...")

        for css_file in css_files:
            try:
                output_path, optimization_info = await self.css_optimizer.optimize_file(
                    css_file, self.config.output_dir / "css"
                )

                # Update results
                results["css"]["count"] += 1
                results["css"]["size_before"] += optimization_info["original_size"]
                results["css"]["size_after"] += optimization_info["optimized_size"]
                results["processed_files"] += 1

                # Add to manifest
                relative_path = str(css_file.relative_to(self.config.source_dir))
                optimized_relative = str(output_path.relative_to(self.config.output_dir))

                self.manifest.add_asset(
                    relative_path,
                    optimized_relative,
                    optimization_info["file_hash"],
                    optimization_info["original_size"],
                    optimization_info["optimized_size"],
                    "text/css",
                )

                logger.debug(
                    f"Optimized {css_file.name}: {optimization_info['compression_ratio']:.1%} reduction"
                )

            except Exception as e:
                logger.error(f"Failed to process CSS file {css_file}: {e}")
                results["errors"].append(f"CSS {css_file.name}: {str(e)}")

    async def _process_image_files(self, results: dict[str, Any]):
        """Process all image files"""
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg"]
        image_files = []

        for ext in image_extensions:
            image_files.extend(self.config.source_dir.glob(f"**/*{ext}"))
            image_files.extend(self.config.source_dir.glob(f"**/*{ext.upper()}"))

        # Filter out build output
        image_files = [
            f for f in image_files if not any(skip in str(f) for skip in ["dist/", "optimized/"])
        ]

        logger.info(f"Processing {len(image_files)} image files...")

        for image_file in image_files:
            try:
                if image_file.suffix.lower() == ".svg":
                    # SVG files are handled differently (just copy for now)
                    await self._copy_svg_file(image_file, results)
                elif self.image_optimizer.is_supported(image_file):
                    output_paths, optimization_info = await self.image_optimizer.optimize_file(
                        image_file, self.config.output_dir / "images"
                    )

                    if output_paths:
                        # Update results
                        results["images"]["count"] += 1
                        results["images"]["size_before"] += optimization_info["original_size"]
                        results["images"]["size_after"] += optimization_info["optimized_size"]
                        results["processed_files"] += 1

                        # Add primary output to manifest
                        relative_path = str(image_file.relative_to(self.config.source_dir))
                        optimized_relative = str(
                            output_paths[0].relative_to(self.config.output_dir)
                        )

                        self.manifest.add_asset(
                            relative_path,
                            optimized_relative,
                            optimization_info["file_hash"],
                            optimization_info["original_size"],
                            optimization_info["optimized_size"],
                            mimetypes.guess_type(str(image_file))[0] or "image/unknown",
                        )

                        logger.debug(
                            f"Optimized {image_file.name}: {optimization_info['compression_ratio']:.1%} reduction"
                        )

            except Exception as e:
                logger.error(f"Failed to process image file {image_file}: {e}")
                results["errors"].append(f"Image {image_file.name}: {str(e)}")

    async def _copy_svg_file(self, svg_file: Path, results: dict[str, Any]):
        """Copy SVG file (no optimization for now)"""
        try:
            output_path = self.config.output_dir / "images" / svg_file.name
            shutil.copy2(svg_file, output_path)

            file_size = svg_file.stat().st_size
            results["images"]["count"] += 1
            results["images"]["size_before"] += file_size
            results["images"]["size_after"] += file_size
            results["processed_files"] += 1

            # Add to manifest
            relative_path = str(svg_file.relative_to(self.config.source_dir))
            optimized_relative = str(output_path.relative_to(self.config.output_dir))

            self.manifest.add_asset(
                relative_path,
                optimized_relative,
                "unchanged",
                file_size,
                file_size,
                "image/svg+xml",
            )

        except Exception as e:
            logger.warning(f"Failed to copy SVG file {svg_file}: {e}")

    def get_asset_url(self, original_path: str) -> str | None:
        """Get optimized asset URL for use in templates"""
        return self.manifest.get_asset_url(original_path)

    async def watch_and_rebuild(self, watch_interval: float = 1.0):
        """Watch for file changes and rebuild as needed"""
        logger.info("Starting file watcher for automatic rebuilds...")

        # Store initial file modification times
        file_mtimes = {}

        def get_current_mtimes():
            mtimes = {}
            for file_path in self.config.source_dir.rglob("*"):
                if file_path.is_file():
                    mtimes[str(file_path)] = file_path.stat().st_mtime
            return mtimes

        file_mtimes = get_current_mtimes()

        while True:
            await asyncio.sleep(watch_interval)

            try:
                current_mtimes = get_current_mtimes()

                # Check for changes
                changed_files = []
                for file_path, mtime in current_mtimes.items():
                    if file_path not in file_mtimes or file_mtimes[file_path] != mtime:
                        changed_files.append(file_path)

                # Check for deleted files
                deleted_files = set(file_mtimes.keys()) - set(current_mtimes.keys())

                if changed_files or deleted_files:
                    logger.info(
                        f"Detected changes: {len(changed_files)} modified, {len(deleted_files)} deleted"
                    )
                    await self.build_assets()
                    file_mtimes = current_mtimes

            except Exception as e:
                logger.error(f"Error in file watcher: {e}")


# Command line interface and build scripts
async def main():
    """Main build function"""
    import argparse

    parser = argparse.ArgumentParser(description="Asset Optimization Pipeline")
    parser.add_argument("--source", default="static", help="Source directory")
    parser.add_argument("--output", default="static/dist", help="Output directory")
    parser.add_argument("--watch", action="store_true", help="Watch for changes and rebuild")
    parser.add_argument("--no-minify", action="store_true", help="Disable minification")
    parser.add_argument("--no-compress", action="store_true", help="Disable compression")
    parser.add_argument("--no-source-maps", action="store_true", help="Disable source maps")
    parser.add_argument("--no-cache-busting", action="store_true", help="Disable cache busting")
    parser.add_argument("--no-images", action="store_true", help="Skip image optimization")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create build configuration
    config = BuildConfig(
        source_dir=args.source,
        output_dir=args.output,
        enable_minification=not args.no_minify,
        enable_compression=not args.no_compress,
        enable_source_maps=not args.no_source_maps,
        enable_cache_busting=not args.no_cache_busting,
        enable_image_optimization=not args.no_images,
    )

    # Initialize pipeline
    pipeline = AssetOptimizationPipeline(config)

    # Build assets
    results = await pipeline.build_assets()

    # Print results
    print("\n🎯 Asset Optimization Complete!")
    print(f"📊 Processed {results['processed_files']} files in {results['build_time']:.2f}s")
    print(f"📦 JavaScript: {results['javascript']['count']} files")
    print(f"🎨 CSS: {results['css']['count']} files")
    print(f"🖼️  Images: {results['images']['count']} files")
    print(f"📉 Overall compression: {results['compression_ratio']:.1%}")

    if results["errors"]:
        print(f"⚠️  {len(results['errors'])} errors occurred:")
        for error in results["errors"]:
            print(f"   - {error}")

    # Watch mode
    if args.watch:
        await pipeline.watch_and_rebuild()


if __name__ == "__main__":
    asyncio.run(main())
