#!/usr/bin/env sh
set -eu

DUMP_FILE="${1:?Usage: ops/restore-postgres.sh backups/verifact-YYYYMMDDTHHMMSSZ.dump}"
: "${POSTGRES_DB:=verifact}"
: "${POSTGRES_USER:=verifact}"

if [ ! -f "$DUMP_FILE" ]; then
  echo "Backup file not found: $DUMP_FILE" >&2
  exit 1
fi

echo 'WARNING: restore overwrites the current VeriFact database. Create and verify a fresh backup first.'
printf 'Type RESTORE to continue: '
read answer
[ "$answer" = 'RESTORE' ] || { echo 'Restore cancelled.'; exit 1; }

docker compose -f docker-compose.prod.yml --env-file .env.production exec -T verifact-db \
  dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T verifact-db \
  createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T verifact-db \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges < "$DUMP_FILE"
echo 'Restore complete. Run migrations and smoke tests before reopening the service.'
