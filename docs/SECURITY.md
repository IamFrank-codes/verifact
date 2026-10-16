# Academic Demo security notes

The Academic Demo is intended for controlled evaluation with non-sensitive, public claims. It sends claim text and retrieved source excerpts to whichever external providers are enabled in the backend environment.

## Protect credentials and data

- Keep `backend/.env` private and restrict its file permissions.
- Never commit, screenshot, or send API keys, database passwords, SMTP passwords, reset tokens, or session cookies.
- Keep provider keys and the Supabase connection string on the backend; never add them to frontend variables or browser code.
- Do not submit confidential, personal, health, financial, or otherwise sensitive text unless you have reviewed and accepted each configured provider's data handling terms.
- Use the least-privileged credentials available and rotate any key that was exposed.

## Application protections

- Passwords are hashed with Argon2.
- Session cookies are HttpOnly and signed by the application.
- Password-reset tokens are stored as hashes, expire, and can be used once.
- Private verification routes check the signed-in user's ownership; public reports require an explicit share action.
- Source classes come from the configured policy, not an AI-generated trust label.
- Scores require evidence eligibility; insufficient evidence remains scoreless.
- URL extraction restricts targets and content size to reduce unsafe fetches.
- Request limits, authentication rate limits, trusted-host checks, narrow CORS origins, and security headers are enabled.
- Provider failures remain visible limitations and are never converted into sources, evidence, or a score.

## Before sharing a report

Review the submitted claim, retained excerpts, source links, and report visibility. Only enable public sharing when the report contains no information you do not intend to publish. A source summary is based on retained provider evidence and can be absent when retrieval or extraction fails.

For setup and provider details, see [the Academic Demo guide](academic-demo.md). For score eligibility, see [Scoring and evidence](SCORING_AND_EVIDENCE.md).
