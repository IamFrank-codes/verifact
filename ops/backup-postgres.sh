#!/usr/bin/env sh
set -eu

: "${BACKUP_DIR:=./backups}"
: "${POSTGRES_DB:=verifact}"
: "${POSTGRES_USER:=verifact}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

# Run from the production host. The resulting custom-format dump supports selective restore.
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T verifact-db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$BACKUP_DIR/verifact-$STAMP.dump"
sha256sum "$BACKUP_DIR/verifact-$STAMP.dump" > "$BACKUP_DIR/verifact-$STAMP.dump.sha256"
echo "Created $BACKUP_DIR/verifact-$STAMP.dump"
