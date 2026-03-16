# Immich on Windows

Immich deployment on Windows with Docker Desktop, external library support, and automatic album creation.

## Overview

This setup includes:
- **Immich Server** - Self-hosted photo management
- **Folder Album Creator** - Automatically creates albums from folder structure
- **Management Scripts** - Utilities for albums, duplicates, and trash cleanup

## Quick Start

### 1. Prerequisites

- Docker Desktop for Windows
- External photo library organized in folders

### 2. Configuration

```bash
# Copy the template and fill in your values
cp .env.template .env

# Edit .env with your settings
# - Set EXTERNAL_LIB_LOCATION to your photos path
# - Set DB_PASSWORD to a secure password
# - Generate an API key in Immich and set IMMICH_FOLDER_ALBUM_CREATOR_API_KEY
```

### 3. Start Services

```bash
docker compose up -d
```

### 4. Access Immich

Open http://localhost:2283 in your browser.

## Management Scripts

### Run via Docker (Recommended)

No Python installation required - runs inside a container.

```bash
# Show available commands
docker compose run --rm immich-scripts help
```

All commands run in **dry-run mode by default** - safe to run without making changes.

### clean-albums - Remove Orphan Albums

Removes albums that no longer have corresponding folders in your external library.

```bash
# Dry run - see what would be deleted
docker compose run --rm immich-scripts clean-albums

# Show folder structure and albums
docker compose run --rm immich-scripts clean-albums --show-folders --show-albums

# Actually delete orphan albums
docker compose run --rm immich-scripts clean-albums --delete
```

### find-duplicates - Find Duplicate Photos

Finds exact duplicates (same filename + same file size) in different locations.

```bash
# Dry run - show duplicates
docker compose run --rm immich-scripts find-duplicates

# Show summary only
docker compose run --rm immich-scripts find-duplicates --summary

# Only show files >= 1MB
docker compose run --rm immich-scripts find-duplicates --min-size 1MB

# Limit to top 20 duplicate groups
docker compose run --rm immich-scripts find-duplicates --limit 20

# Move duplicates to trash (keeps one copy)
docker compose run --rm immich-scripts find-duplicates --delete

# Permanently delete duplicates (cannot recover)
docker compose run --rm immich-scripts find-duplicates --force-delete
```

### clean-trash - Manage Trashed Assets

Manages trashed and offline assets, especially useful for external library assets that can't be deleted via the normal Immich UI "Empty Trash" button.

```bash
# Dry run - show trashed assets
docker compose run --rm immich-scripts clean-trash

# Show summary grouped by folder
docker compose run --rm immich-scripts clean-trash --summary

# Filter by days in trash
docker compose run --rm immich-scripts clean-trash --min-days 7

# Filter by path (see Windows note below)
docker compose run --rm immich-scripts clean-trash --path "/photos/Siva/OldFolder"

# Permanently delete ALL trashed assets
docker compose run --rm immich-scripts clean-trash --delete

# Permanently delete specific folder from trash
docker compose run --rm immich-scripts clean-trash --path "/photos/Siva/OldFolder" --delete

# Restore assets from trash
docker compose run --rm immich-scripts clean-trash --restore
```

**Windows Git Bash Note:** When using `--path` with Unix-style paths, prefix the command with `MSYS_NO_PATHCONV=1` to prevent path conversion:
```bash
MSYS_NO_PATHCONV=1 docker compose run --rm immich-scripts clean-trash --path "/photos/Siva/OldFolder" --delete
```
This is not needed when running from PowerShell or CMD.

**Note:** Since the external library is mounted read-only, scripts only modify Immich's database. Physical files remain on disk.

### Run locally with Python

```bash
cd src
pip install -r requirements.txt
python cleanup_albums.py --help
python detect_duplicates.py --help
python cleanup_trash.py --help
```

### What is an "orphan album"?

An orphan album is an album in Immich that no longer has a corresponding folder in your external library. This can happen when you:
- Rename a folder
- Delete a folder
- Change the folder structure

The cleanup script:
1. Scans your external library folders
2. Generates expected album names based on `ALBUM_LEVELS`
3. Compares with existing albums in Immich
4. Identifies albums that don't match any folder
5. Optionally deletes those orphan albums

## Docker Services

| Service | Description | Port |
|---------|-------------|------|
| immich-server | Main Immich application | 2283 |
| immich-machine-learning | ML for face/object recognition | - |
| immich-folder-album-creator | Auto album creation | - |
| redis | Cache | - |
| database | PostgreSQL | - |

## Common Tasks

### Restart all services
```bash
docker compose down && docker compose up -d
```

### Restart album creator (after config changes)
```bash
docker compose up -d --force-recreate immich-folder-album-creator
```

### View album creator logs
```bash
docker logs immich_folder_album_creator --tail 50
```

### Trigger immediate album scan
```bash
docker restart immich_folder_album_creator
```

## Troubleshooting

### Albums not being created
1. Check that the API key is valid
2. Verify ROOT_PATH matches your folder structure
3. Check logs: `docker logs immich_folder_album_creator`

### Photos going to trash after folder rename
This is expected behavior. Immich tracks files by path. When you rename a folder:
1. Old paths appear as "missing" → moved to trash
2. New paths are treated as new files

**Workaround:** After renaming, run a library scan and use the cleanup script to remove orphan albums.

### Album creator can't connect
The album creator might start before Immich server is ready. Simply restart it:
```bash
docker restart immich_folder_album_creator
```

## References

### Official Documentation
- [Immich Documentation](https://docs.immich.app/)
- [Immich Installation Guide](https://docs.immich.app/install/docker-compose)
- [Immich Environment Variables](https://docs.immich.app/install/environment-variables)
- [Immich External Libraries](https://docs.immich.app/features/libraries/)

### Related Projects
- [Immich GitHub Repository](https://github.com/immich-app/immich)
- [Immich Folder Album Creator](https://github.com/Salvoxia/immich-folder-album-creator)

### Community Resources
- [Immich Discord](https://discord.gg/D8JsnBEuKb)
- [Immich Reddit](https://www.reddit.com/r/immich/)
