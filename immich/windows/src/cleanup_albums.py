#!/usr/bin/env python3
"""
Cleanup orphan albums in Immich.

This script compares albums in Immich with the actual folder structure
and removes albums that no longer have corresponding folders.
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from utils.immich_api import ImmichAPI
from utils.filesystem import get_expected_album_names, get_folder_structure_summary


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup orphan albums in Immich",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_albums.py                    # Dry run - show what would be deleted
  python cleanup_albums.py --delete           # Actually delete orphan albums
  python cleanup_albums.py --show-folders     # Show folder structure
  python cleanup_albums.py --show-albums      # Show all albums in Immich
        """,
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete orphan albums (default is dry-run)",
    )
    parser.add_argument(
        "--show-folders",
        action="store_true",
        help="Show folder structure being scanned",
    )
    parser.add_argument(
        "--show-albums",
        action="store_true",
        help="Show all albums currently in Immich",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to .env file (default: project root .env)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="Immich API URL (default: auto-detect from environment)",
    )

    args = parser.parse_args()

    try:
        config = Config(args.env_file)
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Determine API URL: CLI arg > env var > default localhost
    if args.api_url:
        api_url = args.api_url
    elif os.path.exists("/photos"):
        # Running inside container, use internal URL
        api_url = config.api_url
    else:
        # Running on host, use localhost
        api_url = "http://localhost:2283/api"

    api = ImmichAPI(api_url, config.api_key)

    # Test connection
    try:
        api.get_albums()
    except Exception as e:
        print(f"Failed to connect to Immich API: {e}")
        print(f"Make sure Immich is running and accessible at {args.api_url}")
        sys.exit(1)

    local_paths = config.get_local_root_paths()

    if args.show_folders:
        print("=" * 60)
        print("FOLDER STRUCTURE")
        print("=" * 60)
        print(f"Album Levels: {config.album_levels}")
        print(f"Root Paths: {config.root_paths}")
        print(f"Local Paths: {local_paths}")
        print()
        print(get_folder_structure_summary(local_paths, max_depth=2))
        print()

    if args.show_albums:
        print("=" * 60)
        print("ALBUMS IN IMMICH")
        print("=" * 60)
        albums = api.get_albums()
        for album in sorted(albums, key=lambda x: x["albumName"]):
            asset_count = album.get("assetCount", 0)
            print(f"  - {album['albumName']} ({asset_count} assets)")
        print(f"\nTotal: {len(albums)} albums")
        print()

    # Get expected album names from folder structure
    expected_names = get_expected_album_names(
        local_paths,
        config.album_levels,
        config.get_album_separator(),
    )

    print("=" * 60)
    print("ORPHAN ALBUM DETECTION")
    print("=" * 60)
    print(f"Expected albums from folders: {len(expected_names)}")

    # Get orphan albums
    orphan_albums = api.get_orphan_albums(list(expected_names))

    if not orphan_albums:
        print("No orphan albums found. Everything is in sync!")
        return

    print(f"Orphan albums found: {len(orphan_albums)}")
    print()
    print("Albums to delete:")
    for album in sorted(orphan_albums, key=lambda x: x["albumName"]):
        asset_count = album.get("assetCount", 0)
        print(f"  - {album['albumName']} ({asset_count} assets)")

    if not args.delete:
        print()
        print("=" * 60)
        print("DRY RUN - No albums were deleted")
        print("Run with --delete flag to actually delete orphan albums")
        print("=" * 60)
        return

    # Confirm deletion
    print()
    response = input(f"Delete {len(orphan_albums)} orphan albums? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        return

    # Delete orphan albums
    print()
    print("Deleting orphan albums...")
    album_ids = [a["id"] for a in orphan_albums]
    results = api.delete_albums(album_ids)

    print(f"Successfully deleted: {len(results['success'])} albums")
    if results["failed"]:
        print(f"Failed to delete: {len(results['failed'])} albums")

    print("Done!")


if __name__ == "__main__":
    main()
