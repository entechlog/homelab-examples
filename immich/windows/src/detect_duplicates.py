#!/usr/bin/env python3
"""
Detect duplicate photos in Immich based on filename and file size.

This script finds exact duplicates (same filename + same size) that exist
in different locations, which often indicates accidental copies or backups.
"""

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from utils.immich_api import ImmichAPI


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def find_duplicates(
    assets: List[Dict],
) -> Dict[Tuple[str, int], List[Dict]]:
    """
    Group assets by (filename, size) to find duplicates.

    Args:
        assets: List of asset dictionaries from Immich API

    Returns:
        Dictionary mapping (filename, size) to list of duplicate assets
    """
    groups = defaultdict(list)

    for asset in assets:
        filename = asset.get("originalFileName", "")
        # exifInfo contains the file size
        exif = asset.get("exifInfo") or {}
        size = exif.get("fileSizeInByte", 0)

        if filename and size:
            key = (filename, size)
            groups[key].append(asset)

    # Filter to only groups with duplicates
    return {k: v for k, v in groups.items() if len(v) > 1}


def select_asset_to_keep(assets: List[Dict], root_paths: List[str]) -> Dict:
    """
    Select which asset to keep from a group of duplicates.

    Priority:
    1. Assets in configured root paths (external library)
    2. Assets with earliest creation date
    3. First asset in list

    Args:
        assets: List of duplicate assets
        root_paths: Configured root paths for external library

    Returns:
        The asset to keep
    """
    # Prefer assets in root paths
    for asset in assets:
        path = asset.get("originalPath", "")
        for root in root_paths:
            if path.startswith(root):
                return asset

    # Fall back to earliest creation date
    sorted_assets = sorted(
        assets,
        key=lambda a: a.get("fileCreatedAt", "") or a.get("createdAt", ""),
    )
    return sorted_assets[0]


def get_parent_folder(path: str, levels: int = 2) -> str:
    """Get parent folder(s) from path for display."""
    parts = Path(path).parts
    if len(parts) > levels:
        return "/".join(parts[-(levels + 1) : -1])
    return str(Path(path).parent)


def main():
    parser = argparse.ArgumentParser(
        description="Detect duplicate photos in Immich (same filename + size)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python detect_duplicates.py                    # Dry run - show duplicates
  python detect_duplicates.py --delete           # Move duplicates to trash
  python detect_duplicates.py --summary          # Show summary only
  python detect_duplicates.py --min-size 1MB     # Only files >= 1MB
        """,
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Move duplicate assets to trash (keeps one copy per group)",
    )
    parser.add_argument(
        "--force-delete",
        action="store_true",
        help="Permanently delete duplicates (cannot be recovered)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary only, don't list individual files",
    )
    parser.add_argument(
        "--min-size",
        type=str,
        default="0",
        help="Minimum file size to consider (e.g., 1MB, 500KB)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of duplicate groups to show (0 = all)",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to .env file",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="Immich API URL (default: auto-detect)",
    )

    args = parser.parse_args()

    # Parse minimum size
    min_size = parse_size(args.min_size)

    try:
        config = Config(args.env_file)
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Determine API URL
    if args.api_url:
        api_url = args.api_url
    elif os.path.exists("/photos"):
        api_url = config.api_url
    else:
        api_url = "http://localhost:2283/api"

    api = ImmichAPI(api_url, config.api_key)

    # Test connection
    try:
        api.get_albums()
    except Exception as e:
        print(f"Failed to connect to Immich API: {e}")
        sys.exit(1)

    print("=" * 70)
    print("DUPLICATE DETECTION")
    print("=" * 70)
    print("Fetching all assets from Immich (with file sizes)...")

    assets = api.get_all_assets(with_exif=True)
    print(f"Total assets: {len(assets)}")

    # Find duplicates
    print("Analyzing for duplicates (same filename + same size)...")
    duplicates = find_duplicates(assets)

    # Filter by minimum size
    if min_size > 0:
        duplicates = {
            k: v for k, v in duplicates.items() if k[1] >= min_size
        }

    if not duplicates:
        print("\nNo duplicates found!")
        return

    # Calculate statistics
    total_groups = len(duplicates)
    total_duplicates = sum(len(v) - 1 for v in duplicates.values())
    total_wasted = sum((len(v) - 1) * k[1] for k, v in duplicates.items())

    print(f"\nDuplicate groups found: {total_groups}")
    print(f"Total duplicate files: {total_duplicates}")
    print(f"Potential space savings: {format_size(total_wasted)}")

    if args.summary:
        print("\n(Use without --summary to see details)")
        return

    # Sort by wasted space (largest first)
    sorted_groups = sorted(
        duplicates.items(),
        key=lambda x: (len(x[1]) - 1) * x[0][1],
        reverse=True,
    )

    if args.limit > 0:
        sorted_groups = sorted_groups[: args.limit]

    print("\n" + "=" * 70)
    print("DUPLICATE GROUPS (sorted by wasted space)")
    print("=" * 70)

    assets_to_delete = []
    root_paths = config.root_paths

    for (filename, size), group in sorted_groups:
        wasted = (len(group) - 1) * size
        print(f"\n{filename} ({format_size(size)}) - {len(group)} copies, wastes {format_size(wasted)}")

        # Select which to keep
        keep_asset = select_asset_to_keep(group, root_paths)

        for asset in group:
            path = asset.get("originalPath", "unknown")
            folder = get_parent_folder(path)
            asset_id = asset.get("id", "")

            if asset["id"] == keep_asset["id"]:
                print(f"  [KEEP]   {folder}/{filename}")
            else:
                print(f"  [DELETE] {folder}/{filename}")
                assets_to_delete.append(asset)

    print("\n" + "=" * 70)

    if not assets_to_delete:
        print("No duplicates to delete.")
        return

    print(f"Assets to delete: {len(assets_to_delete)}")
    print(f"Space to recover: {format_size(total_wasted)}")

    if not args.delete and not args.force_delete:
        print("\nDRY RUN - No files were deleted")
        print("Run with --delete to move duplicates to trash")
        print("Run with --force-delete to permanently delete")
        print("=" * 70)
        return

    # Confirm deletion
    action = "permanently DELETE" if args.force_delete else "move to TRASH"
    print(f"\nThis will {action} {len(assets_to_delete)} duplicate assets.")
    response = input("Continue? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        return

    # Delete duplicates
    print("\nDeleting duplicates...")
    asset_ids = [a["id"] for a in assets_to_delete]
    results = api.delete_assets(asset_ids, force=args.force_delete)

    print(f"Successfully deleted: {len(results['success'])}")
    if results["failed"]:
        print(f"Failed to delete: {len(results['failed'])}")

    print("Done!")


def parse_size(size_str: str) -> int:
    """Parse human-readable size string to bytes."""
    size_str = size_str.strip().upper()
    if not size_str or size_str == "0":
        return 0

    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            try:
                return int(float(size_str[: -len(unit)]) * multiplier)
            except ValueError:
                return 0

    try:
        return int(size_str)
    except ValueError:
        return 0


if __name__ == "__main__":
    main()
