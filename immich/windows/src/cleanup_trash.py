#!/usr/bin/env python3
"""
Cleanup trashed assets in Immich.

This script helps manage trashed assets, especially useful for external library
assets that can't be deleted via the normal "Empty Trash" UI button.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from utils.immich_api import ImmichAPI


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes is None:
        return "unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string to datetime object."""
    if not dt_str:
        return datetime.now(timezone.utc)
    # Handle various formats
    dt_str = dt_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return datetime.now(timezone.utc)


def get_days_in_trash(asset: Dict) -> int:
    """Calculate how many days an asset has been in trash."""
    # deletedAt is when it was trashed
    deleted_at = asset.get("deletedAt") or asset.get("updatedAt")
    if not deleted_at:
        return 0

    deleted_dt = parse_datetime(deleted_at)
    now = datetime.now(timezone.utc)

    # Make sure both are timezone aware
    if deleted_dt.tzinfo is None:
        deleted_dt = deleted_dt.replace(tzinfo=timezone.utc)

    delta = now - deleted_dt
    return delta.days


def group_by_folder(assets: List[Dict]) -> Dict[str, List[Dict]]:
    """Group assets by their parent folder."""
    groups = {}
    for asset in assets:
        path = asset.get("originalPath", "unknown")
        folder = str(Path(path).parent)
        if folder not in groups:
            groups[folder] = []
        groups[folder].append(asset)
    return groups


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup trashed assets in Immich",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_trash.py                      # Dry run - show trashed assets
  python cleanup_trash.py --summary            # Show summary by folder
  python cleanup_trash.py --min-days 7         # Only assets trashed > 7 days ago
  python cleanup_trash.py --delete             # Force delete all trashed assets
  python cleanup_trash.py --restore            # Restore all from trash
  python cleanup_trash.py --path "/photos/Siva/Old Folder" --delete  # Delete specific folder
        """,
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Permanently delete trashed assets (force delete, bypasses normal trash)",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore assets from trash",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary grouped by folder",
    )
    parser.add_argument(
        "--min-days",
        type=int,
        default=0,
        help="Only include assets trashed at least N days ago",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Filter by path prefix (e.g., /photos/Siva/OldFolder)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of assets to process (0 = all)",
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

    if args.delete and args.restore:
        print("Error: Cannot use both --delete and --restore")
        sys.exit(1)

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
    print("TRASH CLEANUP")
    print("=" * 70)
    print("Fetching trashed assets...")

    assets = api.get_trashed_assets()
    print(f"Total trashed assets: {len(assets)}")

    if not assets:
        print("\nTrash is empty!")
        return

    # Filter by minimum days
    if args.min_days > 0:
        assets = [a for a in assets if get_days_in_trash(a) >= args.min_days]
        print(f"After filtering (>= {args.min_days} days): {len(assets)}")

    # Filter by path prefix
    if args.path:
        path_filter = args.path.rstrip("/")
        assets = [a for a in assets if a.get("originalPath", "").startswith(path_filter)]
        print(f"After path filter ({args.path}): {len(assets)}")

    if not assets:
        print("\nNo assets match the filters!")
        return

    # Apply limit
    if args.limit > 0:
        assets = assets[:args.limit]
        print(f"Limited to: {len(assets)} assets")

    # Calculate total size
    total_size = sum(
        (a.get("exifInfo") or {}).get("fileSizeInByte", 0) or 0
        for a in assets
    )

    print(f"\nAssets to process: {len(assets)}")
    print(f"Total size: {format_size(total_size)}")

    # Group by folder for display
    grouped = group_by_folder(assets)

    if args.summary:
        print("\n" + "=" * 70)
        print("TRASHED ASSETS BY FOLDER")
        print("=" * 70)

        # Sort by count descending
        sorted_groups = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)

        for folder, folder_assets in sorted_groups:
            folder_size = sum(
                (a.get("exifInfo") or {}).get("fileSizeInByte", 0) or 0
                for a in folder_assets
            )
            # Get days range
            days = [get_days_in_trash(a) for a in folder_assets]
            min_days = min(days) if days else 0
            max_days = max(days) if days else 0
            days_str = f"{min_days}-{max_days} days" if min_days != max_days else f"{min_days} days"

            print(f"\n{folder}")
            print(f"  Files: {len(folder_assets)}, Size: {format_size(folder_size)}, In trash: {days_str}")
    else:
        print("\n" + "=" * 70)
        print("TRASHED ASSETS")
        print("=" * 70)

        # Sort by folder then filename
        sorted_assets = sorted(assets, key=lambda a: a.get("originalPath", ""))

        current_folder = None
        for asset in sorted_assets[:50]:  # Limit display to 50
            path = asset.get("originalPath", "unknown")
            folder = str(Path(path).parent)
            filename = Path(path).name

            if folder != current_folder:
                print(f"\n{folder}/")
                current_folder = folder

            size = (asset.get("exifInfo") or {}).get("fileSizeInByte", 0)
            days = get_days_in_trash(asset)
            print(f"  {filename} ({format_size(size)}, {days} days)")

        if len(assets) > 50:
            print(f"\n  ... and {len(assets) - 50} more files")

    print("\n" + "=" * 70)

    # Action
    if not args.delete and not args.restore:
        print("DRY RUN - No changes made")
        print("Use --delete to permanently delete these assets")
        print("Use --restore to restore these assets from trash")
        print("=" * 70)
        return

    action = "permanently DELETE" if args.delete else "RESTORE"
    print(f"\nThis will {action} {len(assets)} assets.")
    response = input("Continue? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        return

    asset_ids = [a["id"] for a in assets]

    if args.delete:
        print("\nDeleting assets (force delete)...")
        results = api.delete_assets(asset_ids, force=True)
        print(f"Successfully deleted: {len(results['success'])}")
        if results["failed"]:
            print(f"Failed to delete: {len(results['failed'])}")
    else:
        print("\nRestoring assets...")
        # Restore in batches
        batch_size = 100
        restored = 0
        failed = 0
        for i in range(0, len(asset_ids), batch_size):
            batch = asset_ids[i:i + batch_size]
            if api.restore_assets(batch):
                restored += len(batch)
            else:
                failed += len(batch)
        print(f"Successfully restored: {restored}")
        if failed:
            print(f"Failed to restore: {failed}")

    print("Done!")


if __name__ == "__main__":
    main()
