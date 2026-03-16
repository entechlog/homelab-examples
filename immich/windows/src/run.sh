#!/bin/sh
# Script runner for Immich management tools

set -e

# Install dependencies quietly
pip install -q -r /scripts/requirements.txt 2>/dev/null

ENV_FILE="/app/.env"
SCRIPT=""

# Parse first argument as command
case "$1" in
    clean-albums)
        SCRIPT="cleanup_albums.py"
        shift
        ;;
    find-duplicates)
        SCRIPT="detect_duplicates.py"
        shift
        ;;
    clean-trash)
        SCRIPT="cleanup_trash.py"
        shift
        ;;
    help|--help|-h|"")
        echo "Immich Management Scripts"
        echo ""
        echo "Usage: docker compose run --rm immich-scripts <command> [options]"
        echo ""
        echo "Commands:"
        echo "  clean-albums       Remove orphan albums (no matching folder)"
        echo "  find-duplicates    Find duplicate photos (same name + size)"
        echo "  clean-trash        Remove or restore trashed assets"
        echo "  help               Show this help message"
        echo ""
        echo "All commands support --help for detailed options."
        echo "All commands run in DRY-RUN mode by default (safe to run)."
        echo ""
        echo "Examples:"
        echo ""
        echo "  # Clean orphan albums"
        echo "  docker compose run --rm immich-scripts clean-albums"
        echo "  docker compose run --rm immich-scripts clean-albums --show-folders"
        echo "  docker compose run --rm immich-scripts clean-albums --delete"
        echo ""
        echo "  # Find duplicate photos"
        echo "  docker compose run --rm immich-scripts find-duplicates"
        echo "  docker compose run --rm immich-scripts find-duplicates --summary"
        echo "  docker compose run --rm immich-scripts find-duplicates --min-size 1MB"
        echo "  docker compose run --rm immich-scripts find-duplicates --delete"
        echo ""
        echo "  # Clean trashed assets"
        echo "  docker compose run --rm immich-scripts clean-trash"
        echo "  docker compose run --rm immich-scripts clean-trash --summary"
        echo "  docker compose run --rm immich-scripts clean-trash --delete                    # Delete ALL"
        echo "  docker compose run --rm immich-scripts clean-trash --path '/photos/...' --delete  # Delete specific folder"
        echo "  docker compose run --rm immich-scripts clean-trash --restore"
        echo ""
        echo "Windows Git Bash: Use MSYS_NO_PATHCONV=1 prefix when using --path with Unix paths"
        echo ""
        exit 0
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        echo "Available commands:"
        echo "  clean-albums       Remove orphan albums"
        echo "  find-duplicates    Find duplicate photos"
        echo "  clean-trash        Remove or restore trashed assets"
        echo ""
        echo "Run 'docker compose run --rm immich-scripts help' for details"
        exit 1
        ;;
esac

# Run the selected script with remaining arguments
exec python "/scripts/$SCRIPT" --env-file "$ENV_FILE" "$@"
