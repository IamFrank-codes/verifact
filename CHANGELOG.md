# Changelog

All notable changes to VeriFact are documented here. Entries are grouped by date and describe user-visible changes, architecture work, and validation status.

## 2026-09-12

### Added

- Added a production transition plan covering the move from local development to a live FastAPI deployment backed by Supabase PostgreSQL and external evidence providers. See [`docs/local-to-production-plan.md`](docs/local-to-production-plan.md).
- Added recommendations for Google Fact Check Tools, GDELT, NewsAPI, ClaimBuster, primary-source retrieval, and retrieval-grounded OpenAI assistance.

### Changed

- Moved the login and signup form column to the top of the viewport to reduce unnecessary vertical scrolling.
- Moved the left authentication branding panel upward by reducing its top padding and headline spacing.
- Replaced object-rendered password validation errors with the clear message **“The passwords are not the same.”**
- Added general API validation-error normalization so structured backend errors are rendered as readable text rather than `[object Object]`.

### Validation

- Frontend production build passed.
- Backend test suite passed with 8 tests.
- Git diff checks passed.
- Changes were pushed to the `main` branch.

## 2026-09-10

### Changed

- Standardized the main application, Verify, private report, and public report shells around a 960px maximum content width.
- Removed the Verify page back button.
- Changed verification progress and error feedback to use one status message at a time with a short replacement animation.
- Added `scripts/refresh_stack.sh` to stop the Compose stack, pull repository updates, rebuild, restart, and display service status.

### Database and deployment

- Pulled and integrated the Supabase deployment configuration.
- Applied the VeriFact schema to the active Supabase project through the Supabase MCP.
- Migrated the local SQLite data while preserving IDs and relationships.
- Verified the migrated row counts: 1 user, 2 sources, 1 verification, 1 claim, 2 evidence records, and 1 score record.

### Validation

- Frontend production build passed.
- Backend test suite passed with 8 tests.
- Supabase migration and table inspection passed.
- Changes were pushed to the `main` branch.

## 2026-08-26 to 2026-09-09

### Initial VeriFact MVP

- Added authentication, password reset, claim and article verification, evidence retention, source-policy classification, deterministic scoring, scoreless insufficient-evidence handling, history, and public/private reports.
- Added local fixture mode for deterministic development and demonstration workflows.
- Added hybrid and production configuration modes for external providers.
- Added provider adapters for Google Fact Check Tools, GDELT, and NewsAPI.
- Added optional structured OpenAI evidence assessment constrained to retained evidence IDs.
- Added PostgreSQL/Alembic migration support, Redis/RQ worker support, production Compose configuration, security headers, rate limiting, health checks, readiness checks, and operational documentation.

### Validation

- The backend regression suite covers scored fixture reports, scoreless insufficient-evidence reports, public/private report behavior, and password-reset behavior.
- The frontend TypeScript production build passed.
- Static delivery validation covered the Compose graph and required deployment assets.
