# VeriFact Academic Demo changes

This log records user-visible changes relevant to the Academic Demo.

## 2026-10-16

- Added a named `academic-demo` application profile for live evidence retrieval and inline report processing.
- Updated the Academic Demo environment example and Compose configuration to use that profile.
- Consolidated setup, provider, Supabase, security, scoring, and validation guidance around one academic workflow.
- Updated the live-evidence regression tests to exercise the Academic Demo profile.

## 2026-10-15

- Improved live evidence retention, provider status messages, and evidence-bounded related-news summaries.
- Added clearer diagnostics for model and evidence-provider failures.
- Added email-based password reset with a single-use link and a manual code fallback.
- Improved the verification, report, and account-recovery interfaces.

## Core application capabilities

The Academic Demo includes account access, claim verification, source-policy classification, provider provenance, evidence-bounded assessment, deterministic score eligibility, report history, and private or explicitly shared reports. Insufficient evidence remains visibly scoreless.
