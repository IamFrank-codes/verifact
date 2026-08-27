# VeriFact production readiness status

**Status:** Production hardening prepared; public deployment intentionally deferred pending a hosting account, domain/DNS, SMTP provider, and production secrets.

## Completed in the repository

| Control or artifact | Status | Validation |
|---|---|---|
| Separate `local-fixture`, `hybrid`, and `production` modes | Complete | Production configuration rejects insecure/non-production mode settings. |
| PostgreSQL/Redis/worker production Compose topology | Complete | Static deployment validator confirms all required services. |
| HTTPS reverse proxy configuration | Complete | Caddy configuration is included; live certificate issuance awaits domain DNS. |
| Production environment template | Complete | `.env.production.example` contains names/descriptions only, with no credentials. |
| Server-side OpenAI/provider configuration | Complete | Keys remain environment-only and provider failures remain limitations. |
| Deterministic evidence score eligibility | Preserved | Backend tests verify scoreless insufficient-evidence behavior. |
| SMTP password-reset path | Complete | Production logic never exposes a reset token; live delivery awaits SMTP credentials. |
| Secure headers, host checks, CORS, request limits, rate limits | Complete | Application startup and backend tests pass. |
| Redis-backed production job queue | Complete | Queue and standalone worker configuration included; live queue test awaits production Redis. |
| Migration, backup, restore, rollback procedures | Complete | Scripts and guide included; restore drill awaits production database. |
| CI workflow | Complete | GitHub Actions workflow includes backend tests, frontend build, container builds, and migration smoke setup. |

## Validation results completed locally

```text
Backend tests: 6 passed
Frontend production build: passed
Development and production delivery configuration: passed static validation
```

## Production smoke-test status

The script `scripts/production_smoke.sh` is ready but **has not been run against a public system**, because no hosting provider, public domain, HTTPS certificate, SMTP service, or production provider credentials have been configured. This is the correct state: a smoke test cannot honestly claim success before a real HTTPS deployment exists.

Once those inputs exist, run:

```bash
VERIFACT_BASE_URL=https://YOUR_DOMAIN ./scripts/production_smoke.sh
```

Then manually confirm real reset-email delivery, worker processing, real evidence retrieval, eligible scoring, scoreless limitations, history isolation, and public/private report behavior. Record the results in this file before launch.
