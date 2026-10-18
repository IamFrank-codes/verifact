# VeriFact Academic Demo

This guide covers the single supported demonstration profile: a local VeriFact interface and API that retrieve evidence from configured live services and store reports in a database. The API processes verification inline and returns the completed report when provider work finishes.

## Requirements

- Python 3.11 or newer
- Node.js 22 or newer
- Git
- A Supabase PostgreSQL project for a shared academic database, or SQLite for a single-machine trial
- A Groq API key for structured evidence analysis
- Internet access from the backend for enabled external providers
- Optional: a Google Fact Check Tools API key for published fact-check retrieval and a NewsAPI key for additional news discovery
- Optional: SMTP credentials if testing account-verification and password-reset email delivery
- Docker Engine with the Compose plugin only if using the included container launcher

Keep provider credentials and the database password in the backend environment file. Never place them in frontend variables or commit a populated environment file.

## 1. Create the private environment file

From the repository root:

```bash
cp .env.academic-demo.example backend/.env
chmod 600 backend/.env
```

Edit `backend/.env` and replace the placeholders. The profile settings should remain:

```dotenv
VERIFACT_ENVIRONMENT=development
VERIFACT_MODE=academic-demo
VERIFACT_INLINE_PROCESSING=true
```

Use a unique `VERIFACT_SECRET_KEY` for your local account data. Set `VERIFACT_DATABASE_URL` to the Supabase PostgreSQL connection string or, for a single-machine trial, a SQLite URL such as `sqlite:///./verifact.db`.

## 2. Configure the evidence and analysis services

### Groq structured evidence analysis

Keep the existing environment variable names and set the Groq-compatible endpoint and model:

```dotenv
VERIFACT_OPENAI_API_KEY=YOUR_GROQ_API_KEY
VERIFACT_OPENAI_BASE_URL=https://api.groq.com/openai/v1
VERIFACT_OPENAI_MODEL=openai/gpt-oss-20b
```

The model receives the claim and retained evidence packet. It may produce an evidence-bounded assessment and related-news summary; it does not choose source quality or calculate VeriFact's score.

### Google Fact Check Tools

Create a Google Fact Check Tools API key and set:

```dotenv
VERIFACT_GOOGLE_FACTCHECK_KEY=YOUR_GOOGLE_FACTCHECK_API_KEY
```

This provider searches previously published fact-check records. A search with no matching record is not a verdict.

### GDELT and optional news discovery

The template enables GDELT by default. GDELT does not require an API key and asks clients to limit requests to one every five seconds. VeriFact paces GDELT calls and caches successful results for five minutes, but GDELT may still throttle a shared server IP during high traffic. If that continues, use another configured provider or contact GDELT about the limit.

NewsAPI is optional. Set `VERIFACT_NEWSAPI_KEY` only if you have a key and have reviewed the provider's current plan limits and terms.

### Email, if needed

SMTP is only needed to test real account-verification and password-reset delivery. Configure the `VERIFACT_SMTP_*` settings in `backend/.env`; do not use a personal email password.

## 3. Prepare the database

For Supabase, use the PostgreSQL connection string from the project's **Connect** panel. Keep the password URL-encoded where required. The application connects directly through its backend; do not place a Supabase `service_role` key in this project.

Apply the current schema from the backend directory:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

On Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

If using SQLite for a single-machine trial, the application creates its local schema during startup; the Alembic command is for the Supabase PostgreSQL database.

## 4. Start the Academic Demo

### Run directly on your computer

Start the API from the activated backend virtual environment:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm ci
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1
```

Open [http://localhost:5173](http://localhost:5173). The API health and interactive API documentation are available at [http://localhost:8000/health](http://localhost:8000/health) and [http://localhost:8000/docs](http://localhost:8000/docs).

### Use the included Compose launcher

After creating `backend/.env`, start the same Academic Demo profile with:

```bash
./scripts/academic_demo.sh start
```

On Windows PowerShell:

```powershell
.\scripts\academic_demo.ps1 -Action start
```

The launcher also supports `stop`, `restart`, `status`, and `logs`. The interface is at `http://localhost:5173` and the API is at `http://localhost:8000`.

## 5. Confirm the live path

1. Confirm `/health` returns `status: ok` and `mode: academic-demo`.
2. Sign in and submit a clear, single factual claim.
3. Open the completed report and inspect **Provider runs** for each provider's status and message.
4. Open the evidence details and check that retained records have relevant excerpts, canonical source links, provider attribution, and source-policy classifications.
5. Check the related-news summary when source text is available. It is intentionally not fabricated when retrieval returns no usable evidence.
6. Check whether a score is shown. A score is conditional on the coverage and source-policy thresholds described in [Scoring and evidence](SCORING_AND_EVIDENCE.md).

A provider returning no results, timing out, or returning unusable records can leave a report scoreless. This is an explicit evidence limitation; it should not be interpreted as proof that a claim is true or false.

## Privacy and safe use

Submitted claim text and retrieved excerpts may be sent to the enabled external providers, including Google, GDELT, NewsAPI, and Groq. Use public, non-sensitive claims for the demonstration. Keep credentials private, and review each provider's data handling and usage terms before submitting material you do not own or are not authorized to share.

For more detail, see [Security notes](SECURITY.md), [Scoring and evidence](SCORING_AND_EVIDENCE.md), and [Supabase setup](supabase.md).
