"""Filesystem utilities for scanning album folders."""

import os
from pathlib import Path
from typing import List, Set


def get_expected_album_names(
    root_paths: List[str],
    album_levels: int = 1,
    separator: str = " ",
) -> Set[str]:
    """
    Scan filesystem and generate expected album names based on folder structure.

    Args:
        root_paths: List of root paths to scan (local filesystem paths)
        album_levels: Number of folder levels to use for album name
        separator: Separator between folder levels in album name

    Returns:
        Set of expected album names
    """
    album_names = set()

    for root_path in root_paths:
        root = Path(root_path)
        if not root.exists():
            print(f"Warning: Root path does not exist: {root_path}")
            continue

        if album_levels == 1:
            # Just the immediate subdirectories
            for item in root.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    album_names.add(item.name)
        else:
            # Multiple levels - need to walk the tree
            _collect_album_names(root, album_levels, separator, [], album_names)

    return album_names


def _collect_album_names(
    current_path: Path,
    levels_remaining: int,
    separator: str,
    current_parts: List[str],
    result: Set[str],
) -> None:
    """
    Recursively collect album names from folder structure.

    Args:
        current_path: Current directory being scanned
        levels_remaining: How many more levels to descend
        separator: Separator for joining folder names
        current_parts: Accumulated folder name parts
        result: Set to add album names to
    """
    if levels_remaining == 0:
        if current_parts:
            result.add(separator.join(current_parts))
        return

    for item in current_path.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            new_parts = current_parts + [item.name]
            if levels_remaining == 1:
                # This is the last level, add the album name
                result.add(separator.join(new_parts))
            else:
                # Continue descending
                _collect_album_names(
                    item, levels_remaining - 1, separator, new_parts, result
                )


def get_folder_structure_summary(root_paths: List[str], max_depth: int = 2) -> str:
    """
    Get a summary of the folder structure for display.

    Args:
        root_paths: List of root paths to scan
        max_depth: Maximum depth to display

    Returns:
        Formatted string showing folder structure
    """
    lines = []
    for root_path in root_paths:
        root = Path(root_path)
        if not root.exists():
            lines.append(f"{root_path} (not found)")
            continue

        lines.append(f"{root_path}/")
        _add_tree_lines(root, lines, "", max_depth, 0)

    return "\n".join(lines)


def _add_tree_lines(
    path: Path,
    lines: List[str],
    prefix: str,
    max_depth: int,
    current_depth: int,
) -> None:
    """Add tree visualization lines for a directory."""
    if current_depth >= max_depth:
        return

    items = sorted([i for i in path.iterdir() if i.is_dir() and not i.name.startswith(".")])
    for i, item in enumerate(items[:10]):  # Limit to 10 items per level
        is_last = i == len(items[:10]) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{item.name}/")

        if current_depth < max_depth - 1:
            extension = "    " if is_last else "│   "
            _add_tree_lines(item, lines, prefix + extension, max_depth, current_depth + 1)

    if len(items) > 10:
        lines.append(f"{prefix}    ... and {len(items) - 10} more")
