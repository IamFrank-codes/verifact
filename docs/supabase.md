# Supabase database

VeriFact connects to Supabase through its PostgreSQL connection. The
Supabase URL and API keys are not needed by the backend unless Supabase
Auth/Storage is added later; do not put a `service_role` key in this project.

## Configure a new deployment

1. In Supabase, open **Connect** and copy a PostgreSQL connection string.
   Use the transaction pooler for a deployment with many short-lived
   connections. Convert its scheme to `postgresql+psycopg://` if needed.
2. Set `VERIFACT_DATABASE_URL` in the deployment environment. Do not commit
   the password. A template is provided in
   [`.env.supabase.example`](../.env.supabase.example).
3. Run the schema migration from the backend directory:

   ```bash
   alembic upgrade head
   ```

   The Alembic environment reads `VERIFACT_DATABASE_URL`; it is no longer
   hard-coded to SQLite.
4. Start the API and worker with the same environment. When the database URL
   points to PostgreSQL, the application does not call `create_all`; Alembic
   remains the authoritative schema process.

## Copy existing local data

Make a backup of the local database first. The one-time migration helper
requires an empty Supabase schema and refuses to merge into non-empty tables:

```bash
python scripts/migrate_to_supabase.py `
  --source-url sqlite:///./backend/verifact.db `
  --target-url "$env:VERIFACT_DATABASE_URL"
```

On a POSIX shell, use `\` instead of the PowerShell backtick. The helper
applies Alembic migrations before copying rows and preserves all IDs,
timestamps, password hashes, reports, and relationships. It does not copy
database users managed by Supabase Auth because VeriFact currently owns its
own `users` table and session cookies.

After validating `/ready`, point the application at the Supabase URL and keep
the local database backup offline according to your retention policy.
