#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up .env files from .env.example templates..."

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [ -f "$src" ] && [ ! -f "$dst" ]; then
    cp "$src" "$dst"
    echo "  Created $dst"
  fi
}

copy_if_missing "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
copy_if_missing "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
copy_if_missing "$ROOT_DIR/frontend/.env.example" "$ROOT_DIR/frontend/.env"
copy_if_missing "$ROOT_DIR/widget/.env.example" "$ROOT_DIR/widget/.env"

echo "Done. Edit each .env file to set your configuration."
