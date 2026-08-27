# Diagram validation record

## Class diagram

The rendered class diagram includes the exact implemented class names for the SQLAlchemy domain models: `User`, `PasswordResetToken`, `Article`, `Verification`, `Claim`, `Evidence`, `Source`, `VerificationScore`, and `ProviderRun`. It also includes the implemented configuration and service classes/protocols: `Settings`, `SourcePolicy`, `EvidenceItem`, `EvidenceProvider`, `GoogleFactCheckProvider`, `GDELTProvider`, `NewsAPIProvider`, and `EvidenceAssessment`.

The relationship cardinalities match the model relationships and foreign keys: a `User` owns `Verification` records and reset tokens; a `Verification` links to zero or one `Article`, multiple `Claim` and `ProviderRun` records, and zero or one `VerificationScore`; `Claim` records own `Evidence`; and each `Evidence` record references a `Source`.

## Architecture diagram

The rendered architecture diagram shows the implemented React/Vite/Nginx client routes, FastAPI API components, RQ worker, PostgreSQL-or-local-SQLite persistence, Redis queue, fixture and source-policy assets, provider adapters, structured OpenAI-compatible analysis, SMTP email path, and Caddy production edge. It explicitly distinguishes local mock fixtures from hybrid local real-provider mode and production mode.

Both diagram images rendered successfully and remain readable at full resolution. Mermaid sources are retained beside their PNG renders for maintainable source-controlled documentation.
