# Academic Demo validation

## Automated validation — 2026-10-16

The Academic Demo static configuration validator passed. It confirmed the academic Compose profile, inline processing, frontend API proxy, environment example, and required guide files. The backend test suite completed with **18 passing tests**. The frontend TypeScript build completed successfully. `git diff --check` also passed.

The backend test run emitted dependency deprecation warnings; no test failed. These automated checks validate code paths and configuration structure, not the availability of external services.

## Live acceptance checks

Run these checks with the private provider credentials configured in `backend/.env`:

1. Confirm the API responds at `/health` and `/ready`.
2. Submit a new, public factual claim through the interface.
3. Inspect provider statuses and messages in the completed report.
4. Confirm retained evidence has relevant excerpts, canonical source links, provider attribution, and source-policy classifications.
5. Confirm the related-news summary is grounded in retained evidence.
6. Confirm an eligible report shows its score components and an ineligible report remains scoreless.
7. Confirm provider outages and empty results are explained without invented sources or summaries.
8. If email is enabled, test account verification and password reset using a dedicated test account.

No live provider request was made as part of the documentation/profile update, so these results do not certify the credentials, quotas, or current reachability of external services. Provider outcomes depend on network availability, enabled services, the submitted claim, and source-policy coverage.

## Source-policy update validation — 2026-10-30

After adding the configured sports-publisher source-policy rules and URL path scoping, the complete backend pytest suite passed: **31 passed**. The focused regression tests covered all nine requested publishers and confirmed that Reuters general-news pages and non-sports Guardian paths do not inherit the sports classification. The run used local tests and mocked integrations; no live news-provider, model-provider, or SMTP request was made. The frontend build and production migration workflow were not re-run for this policy-only update.
