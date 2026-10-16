# VeriFact Academic Demo

> **VeriFact — Verify. Understand. Trust.**

VeriFact is an evidence-based claim-checking application. It retrieves available source records, applies a configured source policy, uses Groq to interpret retained evidence when configured, and calculates a score only when the evidence meets the application's eligibility rules. A model response by itself is never treated as proof.

## Academic demo setup

The Academic Demo profile uses live external evidence services and processes each verification directly in the API request. The profile and complete setup instructions are in [docs/academic-demo.md](docs/academic-demo.md).

### Requirements

- Python 3.11 or newer
- Node.js 22 or newer
- A Supabase PostgreSQL project, or a local SQLite database for a single-machine demonstration
- A Groq API key for structured evidence analysis
- Internet access for configured live providers
- Optional: a Google Fact Check Tools API key for published ClaimReview records, a NewsAPI key, and SMTP credentials

### Quick start

```bash
cp .env.academic-demo.example backend/.env
chmod 600 backend/.env
```

Edit `backend/.env` with the database connection string and provider credentials. Then start the backend and frontend as described in the [Academic Demo guide](docs/academic-demo.md).

## What VeriFact reports

- Provider results, source links, publication and retrieval details
- Source-policy classifications for known domains
- Evidence-bounded claim assessments and related-news summaries when sufficient source text is available
- A transparent credibility score only when coverage and source-policy criteria are met
- An explicit insufficient-evidence result when the evidence is not strong or broad enough

A missing score is an evidence limitation, not a finding that a claim is true or false. See [Scoring and evidence](docs/SCORING_AND_EVIDENCE.md) for the exact rules.

## Checks

```bash
cd backend
python3 -m pytest -q
cd ../frontend
npm run build
```

The Academic Demo's privacy and credential-handling guidance is in [docs/SECURITY.md](docs/SECURITY.md). Supabase setup is documented in [docs/supabase.md](docs/supabase.md).
