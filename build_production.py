#!/usr/bin/env python3
"""
Production Build Script for TQ GenAI Chat Asset Optimization

This script builds optimized assets for production deployment.
Integrates with the enhanced asset optimization pipeline.

Usage:
    python build_production.py [--clean] [--watch] [--stats]

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import argparse
import asyncio
import logging
import shutil
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from build_assets_enhanced import AssetOptimizationPipeline, BuildConfig


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("build.log")],
    )


async def build_production_assets(
    source_dir: str = "static",
    output_dir: str = "static/dist",
    clean: bool = False,
    verbose: bool = False,
):
    """Build production assets"""

    logger = logging.getLogger(__name__)

    if clean:
        logger.info(f"Cleaning output directory: {output_dir}")
        output_path = Path(output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

    # Production build configuration
    config = BuildConfig(
        source_dir=source_dir,
        output_dir=output_dir,
        enable_minification=True,
        enable_compression=True,
        enable_source_maps=False,  # Disabled for production
        enable_cache_busting=True,
        enable_image_optimization=True,
        enable_webp_conversion=True,
        image_quality=80,  # Optimized for web
        webp_quality=75,  # Good balance of quality/size
        compression_level=9,  # Maximum compression
    )

    # Initialize pipeline
    pipeline = AssetOptimizationPipeline(config)

    # Build assets
    logger.info("🚀 Starting production asset build...")
    start_time = time.time()

    results = await pipeline.build_assets()

    build_time = time.time() - start_time

    # Report results
    logger.info("🎯 Production build completed!")
    logger.info(f"📊 Build time: {build_time:.2f}s")
    logger.info(f"📦 Processed {results['processed_files']} files")
    logger.info(f"🔧 JavaScript: {results['javascript']['count']} files")
    logger.info(f"🎨 CSS: {results['css']['count']} files")
    logger.info(f"🖼️  Images: {results['images']['count']} files")
    logger.info(f"📉 Compression ratio: {results['compression_ratio']:.1%}")

    # Size analysis
    total_before = results["total_size_before"]
    total_after = results["total_size_after"]

    logger.info(f"📏 Original size: {total_before:,} bytes ({total_before / 1024:.1f} KB)")
    logger.info(f"📦 Optimized size: {total_after:,} bytes ({total_after / 1024:.1f} KB)")
    logger.info(f"💾 Size reduction: {total_before - total_after:,} bytes")

    if results["errors"]:
        logger.warning(f"⚠️  {len(results['errors'])} errors occurred:")
        for error in results["errors"]:
            logger.warning(f"   - {error}")

    # Manifest stats
    manifest_stats = results["manifest_stats"]
    logger.info(f"📋 Manifest: {manifest_stats['total_assets']} assets")

    if verbose:
        logger.info("📊 Assets by type:")
        for asset_type, count in manifest_stats["assets_by_type"].items():
            logger.info(f"   {asset_type}: {count} files")

    return results


async def watch_assets(source_dir: str = "static", output_dir: str = "static/dist"):
    """Watch for asset changes and rebuild"""
    logger = logging.getLogger(__name__)

    config = BuildConfig(
        source_dir=source_dir,
        output_dir=output_dir,
        enable_minification=True,
        enable_compression=True,
        enable_source_maps=True,  # Enabled for development
        enable_cache_busting=False,  # Disabled for faster development
        enable_image_optimization=True,
        enable_webp_conversion=True,
    )

    pipeline = AssetOptimizationPipeline(config)

    logger.info("👀 Starting asset watcher for development...")
    await pipeline.watch_and_rebuild()


def print_stats(output_dir: str = "static/dist"):
    """Print asset statistics"""
    manifest_path = Path(output_dir) / "manifest.json"

    if not manifest_path.exists():
        print("❌ No manifest found. Run build first.")
        return

    import json

    with open(manifest_path) as f:
        manifest = json.load(f)

    if not manifest:
        print("📭 No assets in manifest")
        return

    # Calculate totals
    total_original = sum(asset["original_size"] for asset in manifest.values())
    total_optimized = sum(asset["optimized_size"] for asset in manifest.values())
    compression_ratio = (
        (total_original - total_optimized) / total_original if total_original > 0 else 0
    )

    # Group by type
    types = {}
    for asset in manifest.values():
        mime_type = asset["mime_type"].split("/")[0]
        if mime_type not in types:
            types[mime_type] = {"count": 0, "original": 0, "optimized": 0}
        types[mime_type]["count"] += 1
        types[mime_type]["original"] += asset["original_size"]
        types[mime_type]["optimized"] += asset["optimized_size"]

    print("\n📊 Asset Statistics")
    print("=" * 50)
    print(f"Total assets: {len(manifest)}")
    print(f"Original size: {total_original:,} bytes ({total_original / 1024:.1f} KB)")
    print(f"Optimized size: {total_optimized:,} bytes ({total_optimized / 1024:.1f} KB)")
    print(f"Compression: {compression_ratio:.1%}")
    print(f"Savings: {total_original - total_optimized:,} bytes")

    print("\n📂 By Asset Type:")
    print("-" * 30)
    for asset_type, stats in types.items():
        type_compression = (
            (stats["original"] - stats["optimized"]) / stats["original"]
            if stats["original"] > 0
            else 0
        )
        print(f"{asset_type}: {stats['count']} files, {type_compression:.1%} compression")

    print("\n📋 Asset Details:")
    print("-" * 30)
    for original_path, asset in manifest.items():
        compression = asset["compression_ratio"]
        print(f"{original_path}: {compression:.1%} reduction")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Production Asset Build Script")
    parser.add_argument("--source", default="static", help="Source directory")
    parser.add_argument("--output", default="static/dist", help="Output directory")
    parser.add_argument("--clean", action="store_true", help="Clean output directory before build")
    parser.add_argument("--watch", action="store_true", help="Watch for changes and rebuild")
    parser.add_argument("--stats", action="store_true", help="Show asset statistics")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        if args.stats:
            print_stats(args.output)
        elif args.watch:
            await watch_assets(args.source, args.output)
        else:
            await build_production_assets(args.source, args.output, args.clean, args.verbose)

    except KeyboardInterrupt:
        print("\n👋 Build interrupted by user")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Build failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
