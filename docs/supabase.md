# Supabase setup for the Academic Demo

The Academic Demo can store accounts, verification reports, evidence, and scores in a Supabase PostgreSQL database. The application connects through its FastAPI backend.

## Create the connection

1. Open the Supabase project's **Connect** panel and copy a PostgreSQL connection string.
2. If using a pooled connection, choose a pooler option compatible with the app's short-lived requests and migration command.
3. Set the string as `VERIFACT_DATABASE_URL` in the private `backend/.env` file. URL-encode special characters in the database password where required.
4. Keep the connection string on the backend. Do not use a Supabase `service_role` key in the frontend or commit it to the repository.

The repository's [Academic Demo environment example](../.env.academic-demo.example) shows the expected SQLAlchemy URL format. Replace every project and password placeholder before starting the app.

## Apply the schema

From the repository root:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

The Alembic configuration reads `VERIFACT_DATABASE_URL` from the backend environment. Confirm that the command completes successfully before testing account creation or report storage.

## Confirm the connection

Start the backend and check:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
```

Then create an account, submit a test claim, and confirm that its report and evidence appear in the application history. Keep access to the Supabase project and its connection details limited to the people operating the academic demonstration.
