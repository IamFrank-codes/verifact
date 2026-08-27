# VeriFact

> **VeriFact — Verify. Understand. Trust.**

VeriFact is an evidence-based news and claim verification MVP. It separates retrieved evidence, source-policy classification, evidence-bounded interpretation, and deterministic scoring. It never treats an AI response alone as proof. When evidence coverage does not meet the configured threshold, the report is explicitly **scoreless**.

## What works in the local MVP

The default `local-fixture` mode requires no external credentials. It includes authentication, non-enumerating password-reset behavior, text/URL/claim submission, source-policy classification, fixture evidence, supported/contradicted/insufficient-evidence reports, transparent score eligibility, history, private/public reports, a responsive React interface, API docs, and Docker services.

Use these fixture phrases in the UI:

| Input | Expected result |
| --- | --- |
| `COVID vaccines reduce hospitalization.` | Evidence-backed report with a score and two policy-classified public-health records. |
| `Vitamin C cures COVID-19.` | Evidence-backed contradiction report with a score; this is not a declaration of absolute truth. |
| `Diamonds are being mined on Neptune.` | **Insufficient evidence — no overall score.** |

Fixture records are marked as **local demonstration data**, not live fact checks.

## Local quick start

### Option A: Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173) for VeriFact, [http://localhost:8000/docs](http://localhost:8000/docs) for the API documentation, and [http://localhost:8025](http://localhost:8025) for the local mailbox interface. The development configuration uses PostgreSQL, Redis, Mailpit, the FastAPI service, the worker, and the Vite client.

### Option B: Lightweight local development

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
VERIFACT_MODE=local-fixture uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The local API uses SQLite by default. The UI invokes a fixture-run helper only in local mode, so a separate worker is not required for the lightweight path.

## Core API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/auth/register` | Create a VeriFact account and session. |
| `POST /api/v1/auth/login` | Start a session. |
| `POST /api/v1/auth/forgot-password` | Return neutral reset confirmation; exposes a token only in local fixture mode. |
| `POST /api/v1/auth/reset-password` | Consume a single-use password-reset token. |
| `POST /api/v1/verifications` | Queue a text, URL, or claim verification. |
| `GET /api/v1/verifications/{id}` | Read a private report owned by the signed-in user. |
| `POST /api/v1/verifications/{id}/share` | Toggle owner-controlled public report visibility. |
| `GET /api/v1/reports/{public_id}` | Read a public report with no private user information. |

The detailed OpenAPI reference runs at `/docs` when the backend starts.

## Enabling external services

Set `VERIFACT_MODE=hybrid` or `VERIFACT_MODE=production` and configure only the credentials you have for Google Fact Check Tools, NewsAPI-compatible search, GDELT, and an OpenAI-compatible endpoint. All provider keys stay on the server. The adapter interface degrades safely: an unavailable provider is recorded as unavailable and cannot be treated as evidence that a claim is false, true, or unsupported.

Read [docs/SCORING_AND_EVIDENCE.md](docs/SCORING_AND_EVIDENCE.md) and [docs/SECURITY.md](docs/SECURITY.md) before production use. A public deployment needs HTTPS, non-default secrets, a dedicated database/backup policy, a real transactional email provider, rate limiting at the proxy/application layer, monitoring, and a policy review process.

## Tests

```bash
cd backend
pytest -q
cd ../frontend
npm run build
```

The backend suite verifies the core requirement that insufficient evidence produces a `null` score, source quality comes from a configured policy, and shared reports omit account data.

## Production readiness

VeriFact now includes a provider-neutral production Compose stack with HTTPS reverse proxy, PostgreSQL, Redis-backed verification jobs, a separate worker, Alembic migrations, structured health/readiness endpoints, rate limits, request limits, secure headers, SMTP-based password reset delivery, backup/restore scripts, and a production smoke-test script.

> **Production mode never uses fixture evidence.** It requires HTTPS origins, PostgreSQL, Redis, secure cookies, and a non-default secret. If live providers are unavailable, the report must show an evidence limitation rather than demo data or an arbitrary score.

Read [docs/deployment.md](docs/deployment.md) before configuring a public host. Copy `.env.production.example` to `.env.production` only on the production host, configure a domain/DNS and credentials there, then follow the backup → build → migration → deploy → readiness → smoke-test sequence. The public deployment itself is intentionally deferred until a hosting account, domain, SMTP provider, and any desired evidence-provider credentials are available.
