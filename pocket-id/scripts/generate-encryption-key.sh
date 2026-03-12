#!/usr/bin/env bash
set -euo pipefail

# Generates an encryption key and writes it into .env

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"

if ! [ -f "$ENV_FILE" ]; then
  echo "Error: .env not found. Run 'cp .env.example .env' first."
  exit 1
fi

# Check if ENCRYPTION_KEY already has a value
CURRENT=$(grep '^ENCRYPTION_KEY=' "$ENV_FILE" | cut -d'=' -f2-)
if [ -n "$CURRENT" ]; then
  echo "ENCRYPTION_KEY is already set in .env — skipping."
  exit 0
fi

KEY=$(openssl rand -base64 32)
sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${KEY}|" "$ENV_FILE"
echo "ENCRYPTION_KEY written to .env"
