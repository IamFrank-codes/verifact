# Academic Demo diagram validation

## Domain class diagram

The diagram covers the account and report entities used by the Academic Demo: `User`, `PasswordResetToken`, `Article`, `Verification`, `Claim`, `Evidence`, `Source`, `VerificationScore`, and `ProviderRun`. It also shows the source policy, evidence-provider interface, configured evidence providers, and structured evidence assessment.

The relationship cardinalities match the application model: a user owns verifications and reset tokens; a verification may reference an article, contains claims and provider runs, and may have a score record; claims own evidence records; and each evidence record references a source.

## Academic Demo architecture diagram

The diagram follows the academic path: browser to Vite frontend to FastAPI; the API runs verification inline, calls configured evidence providers and Groq, and persists results to the configured application database. SMTP is shown only as an optional email integration.

The Mermaid source files are the maintainable source of truth for both rendered PNG diagrams. Regenerate the images using the commands in [README.md](README.md) after editing a diagram.
