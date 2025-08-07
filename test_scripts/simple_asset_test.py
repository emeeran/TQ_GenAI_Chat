#!/usr/bin/env python3
"""
Simple Asset Optimization Test
"""

import json
from pathlib import Path


def test_asset_optimization():
    print("Testing Asset Optimization Integration (Task 2.1.2)")
    print("=" * 60)

    # Check if optimized assets exist
    dist_path = Path("static/dist")
    manifest_path = dist_path / "manifest.json"

    print(f"1. Checking optimized assets directory: {dist_path}")
    print(f"   Exists: {dist_path.exists()}")

    if dist_path.exists():
        assets = list(dist_path.rglob("*"))
        print(f"   Total optimized files: {len([f for f in assets if f.is_file()])}")

    print(f"\n2. Checking asset manifest: {manifest_path}")
    print(f"   Exists: {manifest_path.exists()}")

    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        print(f"   Manifest entries: {len(manifest)}")

        print("\n3. Sample optimized assets:")
        for i, (original, data) in enumerate(manifest.items()):
            if i >= 5:  # Show first 5
                break
            optimized_path = data.get("optimized_path", "N/A")
            compression = data.get("compression_ratio", 0) * 100
            print(f"   {original} -> {optimized_path} ({compression:.1f}% smaller)")

    # Test production vs development URLs
    print("\n4. Testing asset URL generation:")

    def get_asset_url_test(asset_path: str, production_mode: bool) -> str:
        """Test version of get_asset_url"""
        if production_mode and manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
            if asset_path in manifest:
                optimized_path = manifest[asset_path].get("optimized_path", asset_path)
                return f"/static/dist/{optimized_path}"
        return f"/static/{asset_path}"

    test_assets = ["styles.css", "js/app.js", "script.js"]

    print("   Development mode URLs:")
    for asset in test_assets:
        url = get_asset_url_test(asset, False)
        print(f"     {asset} -> {url}")

    print("   Production mode URLs:")
    for asset in test_assets:
        url = get_asset_url_test(asset, True)
        print(f"     {asset} -> {url}")

    # Check gzip compression
    print("\n5. Checking gzip compression:")
    if dist_path.exists():
        gzip_files = list(dist_path.rglob("*.gz"))
        print(f"   Gzipped files: {len(gzip_files)}")
        for gz_file in gzip_files[:3]:  # Show first 3
            original_name = gz_file.name.replace(".gz", "")
            print(f"     {original_name} -> {gz_file.name}")

    print("\n✅ Asset Optimization Integration Test Complete")


if __name__ == "__main__":
    test_asset_optimization()
