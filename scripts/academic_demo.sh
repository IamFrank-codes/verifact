#!/usr/bin/env bash
set -Eeuo pipefail

ACTION="${1:-start}"
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
COMPOSE=(docker compose -f docker-compose.academic.yml --env-file backend/.env)

command -v docker >/dev/null 2>&1 || { echo 'Docker was not found. Install Docker and try again.' >&2; exit 1; }
test -f backend/.env || { echo 'Missing backend/.env. Copy backend/.env.example and add your private credentials.' >&2; exit 1; }

case "$ACTION" in
  start)
    "${COMPOSE[@]}" config >/dev/null
    "${COMPOSE[@]}" up --build -d
    echo 'VeriFact is available at http://localhost:5173'
    echo 'API health: http://localhost:8000/health'
    ;;
  stop)
    "${COMPOSE[@]}" down
    ;;
  restart)
    "${COMPOSE[@]}" down
    "${COMPOSE[@]}" up --build -d
    ;;
  status)
    "${COMPOSE[@]}" ps
    ;;
  logs)
    "${COMPOSE[@]}" logs -f --tail=100 verifact-api
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}" >&2
    exit 2
    ;;
esac
