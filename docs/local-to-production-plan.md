# VeriFact Local-to-Production Plan

## Executive decision

VeriFact should move to production by keeping **FastAPI as the application and orchestration API**, using **Supabase PostgreSQL as the hosted database**, and calling OpenAI and evidence providers only from the backend. Supabase Edge Functions are not required for the first live deployment.

The production system should preserve VeriFact’s central rule: external APIs retrieve evidence, OpenAI may assist with evidence-bounded interpretation, and VeriFact—not a provider or model—calculates the deterministic score. A missing provider result must remain an evidence limitation rather than become an automatic true, false, or low-confidence label.

## Target architecture

```text
Browser frontend
      |
      v
FastAPI application API
  |       |        |         |
  |       |        |         +-- OpenAI: structured evidence assistance
  |       |        +------------ Google Fact Check: prior ClaimReview records
  |       +--------------------- GDELT: optional news discovery and timelines
  +----------------------------- Supabase PostgreSQL
```

The backend remains responsible for authentication, authorization, request validation, claim extraction, provider adapters, evidence normalization, source-policy classification, scoring, public/private reports, rate limits, and audit logging. The frontend should never contain database credentials or external provider keys.

## What changes from local development

| Area | Local development | Live production target |
|---|---|---|
| Frontend | Vite development server | Static production build served behind HTTPS |
| Application API | FastAPI on localhost | FastAPI on a managed or private server with HTTPS access through a reverse proxy |
| Database | SQLite fixture database | Supabase PostgreSQL using `VERIFACT_DATABASE_URL` |
| Verification evidence | Deterministic local fixtures | Direct primary-source retrieval plus provider adapters |
| AI assistance | Optional and usually disabled | Optional OpenAI structured analysis over retained evidence only |
| Authentication | VeriFact-owned users and signed cookies | Keep this initially; evaluate Supabase Auth later as a separate migration |
| Jobs | Inline/local fixture execution | Start inline for low traffic, then add Redis/RQ when latency or volume requires a queue |
| Secrets | Local `.env` files | Host or secret-manager environment variables; never commit credentials |
| Email | Mailpit or local development behavior | SMTP provider with verified sender and reset-email delivery |
| Operations | Local logs and manual checks | Health/readiness monitoring, backups, alerts, rate limits, and smoke tests |

## Phased implementation plan

### Phase 0 — Establish a reproducible baseline

The repository already contains local fixture, hybrid, and production modes, Supabase configuration, Alembic migrations, provider adapters, OpenAI configuration, and production Compose assets. Before adding live provider credentials, create a deployment branch or release tag from a commit that passes the frontend build, backend tests, static delivery validation, and the existing production configuration checks.

Record the exact versions of Python, Node.js, PostgreSQL compatibility, provider SDK or HTTP contracts, and the selected hosting environment. Create an offline backup of `backend/verifact.db` even though the current data has already been copied to Supabase.

### Phase 1 — Make Supabase the application database

Set `VERIFACT_DATABASE_URL` to the Supabase PostgreSQL connection string on the backend host. Run Alembic migrations from the backend release rather than relying on application startup table creation. Keep the connection string server-side.

The Supabase project currently contains the VeriFact schema and the migrated local records. Before live traffic, verify `/health`, `/ready`, login, report history, public-report access, and a new verification against the Supabase-backed backend.

Supabase currently reports Row Level Security disabled on the application tables. Because the current architecture uses FastAPI as the only database access path, do not expose the database through the browser. Before using Supabase client libraries directly, design and test RLS policies for the application’s ownership model. Do not enable RLS without policies because that would block intended access.

### Phase 2 — Keep authentication in FastAPI

Retain the existing VeriFact authentication for the first deployment. It already owns the `users` table, password hashing, signed session cookies, password reset tokens, and authorization checks.

Supabase Auth can be evaluated later, but it would require changing frontend sign-in and signup flows, validating Supabase JWTs in FastAPI, deciding how Supabase user IDs map to VeriFact records, redesigning password reset behavior, and writing RLS policies. It is not necessary for the initial live launch.

### Phase 3 — Introduce live evidence retrieval

Use a provider-neutral evidence ledger. Every retrieved record should preserve the provider, original URL, canonical URL, publisher, publication date, retrieval timestamp, excerpt or permitted snippet, claim relationship, query context, and source-policy classification. Deduplicate syndicated articles and distinguish a provider returning no result from evidence that contradicts a claim.

The recommended provider order is:

| Priority | Provider or source class | Production role | Decision |
|---:|---|---|---|
| 1 | Direct primary sources | Government, regulator, court, filing, research, dataset, official statement, or original publisher document | **Required backbone.** Fetch and evaluate the original document rather than treating a search result as proof. |
| 2 | Google Fact Check Tools Claim Search | Previously published ClaimReview records, publisher verdicts, dates, and review links | **Pilot first.** Strong fit for prior fact-check retrieval, but a no-match is not a truth judgment. Use a restricted API key, caching, throttling, and quota/billing verification. [1] |
| 3 | GDELT DOC 2.0 | Broad multilingual news discovery, related coverage, and timeline context | **Optional secondary enrichment.** Use as a lead generator, not as a verdict source. Apply caching, backoff, and low request rates because a numeric quota or SLA was not found in the reviewed documentation. [2] |
| 4 | NewsAPI | Paid news discovery and historical/current publisher leads | **Conditional optional provider.** Do not use the Developer plan in production. Review the paid plan, quota, overage, copyright, and licensing terms before integration. [3] |
| 5 | ClaimBuster | Claim check-worthiness ranking and candidate fact-check matching | **Deferred.** Require a credentialed operational pilot because current documentation does not establish production limits, pricing, availability, coverage, or SLA. [4] |

### Phase 4 — Add OpenAI as bounded assistance

OpenAI should receive only a normalized claim and the retained evidence packet. The model should return structured output containing a bounded assessment, explanation, freshness note, and IDs of evidence records used. The backend must reject IDs that were not in the supplied packet.

OpenAI should assist with claim extraction, query paraphrases, evidence passage selection, contradiction flags, and reviewer-draft summaries. It must not invent citations, create source-quality labels, infer a verdict from no search results, or calculate the final score. Store the model name, prompt or policy version, request timestamp, response status, and reviewer edits for auditability.

The final score remains deterministic. VeriFact should continue to persist `score: null` when evidence coverage or source-policy requirements are not satisfied.

### Phase 5 — Decide on Redis after observing production latency

Redis is not required for the smallest initial deployment if verification work can run inline and traffic is low. In that configuration, FastAPI calls the providers and OpenAI during the request and writes the completed report to Supabase.

The current production configuration requires Redis because it uses RQ for background verification jobs. To launch without Redis, add an explicit inline job mode that bypasses `enqueue_verification`, runs the verification in the API process, and treats Redis as optional in readiness checks. Do not silently overload the API with long-running jobs; set strict provider timeouts and document the limitation.

Add Redis/RQ when requests become slow, provider calls need retries, traffic becomes concurrent, or more than one API instance must share work. At that point, retain the current job model: FastAPI creates the verification, Redis queues it, a worker performs provider and OpenAI calls, and the worker persists the report to Supabase.

### Phase 6 — Production hardening and launch

Configure HTTPS origins, secure cookies, a unique secret key, allowed hosts, SMTP, Supabase PostgreSQL, provider keys, request limits, rate limits, logging, and backups. Run database migrations before starting application containers. Keep provider keys and the Supabase connection string out of the frontend and repository.

Run a staged launch with internal accounts first. Verify signup, login, reset email delivery, claim submission, article submission, provider failure handling, insufficient evidence, scoring, report history, public sharing, and deletion. Confirm that provider outages produce visible limitations and never fixture evidence in production mode.

After launch, monitor latency by provider, error rates, quota consumption, cache hit rate, evidence coverage, scoreless-report rate, model-parse failures, and user-visible report failures. Review high-impact or conflicting reports before publishing them broadly.

## Recommended first production configuration

The first live configuration should use FastAPI, Supabase PostgreSQL, Google Fact Check Claim Search, direct primary-source retrieval, and optional OpenAI assistance. Enable GDELT only as a bounded discovery enrichment after a small operational test. Add NewsAPI only if measured coverage needs justify its paid plan and licensing review. Defer ClaimBuster until a live credentialed pilot succeeds.

For a small project, run without Redis initially only if the backend is changed to support explicit inline execution. Otherwise, deploy the existing production topology with Redis and the worker because the current production validator expects it.

## Acceptance criteria

| Gate | Acceptance condition |
|---|---|
| Database | Alembic reaches head on Supabase; application CRUD and relationships work; backup and restore procedure is documented. |
| Security | HTTPS is active; secure cookies are enabled; provider and database secrets are server-only; rate limits and request limits are active. |
| Evidence | Every report retains provider provenance, canonical links, retrieval dates, source-policy context, and claim relationships. |
| AI | OpenAI cannot introduce unrecognized evidence IDs or citations; model failures degrade to a documented evidence limitation. |
| Scoring | Scores are deterministic and persisted only when the evidence eligibility threshold is met; insufficient evidence remains scoreless. |
| Reliability | Provider timeouts, retries, cache behavior, and outage fallbacks are tested. |
| Operations | `/health`, `/ready`, logs, alerts, backups, smoke tests, and rollback steps are verified on the actual host. |
| Product | Public and private report behavior, account recovery, and mobile/desktop layouts are tested before public launch. |

## References

[1]: https://developers.google.com/fact-check/tools/api "Google Fact Check Tools API documentation"

[2]: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ "GDELT DOC 2.0 API"

[3]: https://newsapi.org/pricing "NewsAPI pricing and plan restrictions"

[4]: https://idir.uta.edu/claimbuster/api/ "ClaimBuster API documentation"
