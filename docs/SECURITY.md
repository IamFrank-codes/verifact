# VeriFact security checklist

VeriFact is designed to present evidence assessments, not declarations of truth. Production operators remain responsible for hosting, credential handling, provider contracts, access governance, and incident response.

## Implemented application controls

| Area | Implemented control |
|---|---|
| Passwords | Argon2 password hashing through Passlib. |
| Sessions | Signed, HttpOnly session cookie; production configuration requires `Secure=true`. |
| Password reset | Random token hashed before persistence, expires after 30 minutes, and is single-use. The response is non-enumerating. |
| Local vs production reset | Local fixture mode may expose a development token. Production uses SMTP delivery and never includes a reset token in the browser response. |
| Authorization | Private verification routes filter by signed-in owner. Public routes require both a public identifier and explicit public visibility. |
| Source policy | Source classes come from a configured policy, not an AI-generated trust label. |
| Scoring integrity | Scores require evidence eligibility; insufficient evidence remains scoreless. |
| URL extraction | The extractor blocks local/private targets, restricts public HTTP(S) URLs, limits content size, and fails closed on unsuitable pages. |
| Request safety | API request size limits, rate limits on auth routes, trusted-host checks, narrow CORS origins, compression, and response security headers are enabled. |
| Provider failures | Provider failures are logged/recorded as limitations and are never converted into evidence, proof, fixture data, or a score. |

## Required production configuration

Before public deployment, configure the following through `.env.production` on the host and never commit it:

- A unique `VERIFACT_SECRET_KEY` with at least 32 characters.
- HTTPS `VERIFACT_FRONTEND_ORIGIN` and `VERIFACT_PUBLIC_BASE_URL` values for the real domain.
- An explicit `VERIFACT_ALLOWED_HOSTS` list and `VERIFACT_SECURE_COOKIES=true`.
- PostgreSQL and Redis credentials, protected Docker volumes or managed equivalents, and off-host backups.
- SMTP credentials and a verified production sender address.
- Only the evidence-provider credentials you are authorized to use.

## Pre-launch checks

> Production is not ready merely because the containers start. Complete the user journey over HTTPS, including registration, login, real password-reset email delivery, a worker-processed verification, evidence-limitation behavior, public/private report isolation, backup creation, and a restore drill.

The detailed operator procedure is in [deployment.md](deployment.md). Review proxy/firewall rules, provider retention terms, privacy notice, account deletion policy, and log retention before public launch.
