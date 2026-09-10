#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/3] Stopping Docker Compose services..."
docker compose down

echo "[2/3] Pulling the latest repository changes..."
git pull --ff-only

echo "[3/3] Rebuilding and starting Docker Compose services..."
# --build belongs to `docker compose up`; this rebuilds images and starts the stack.
docker compose up --build -d

echo "Refresh complete. Current services:"
docker compose ps
