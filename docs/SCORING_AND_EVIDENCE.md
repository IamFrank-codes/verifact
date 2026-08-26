# VeriFact evidence and scoring policy

VeriFact does not ask a language model to declare whether a claim is true. A report contains retained source records, policy-derived classifications, an evidence-bounded assessment, and—only when configured conditions are met—a deterministic score.

## Score eligibility

A report is score-eligible only when at least 60% of the weighted checkable claims have a non-insufficient evidence assessment and the retained evidence includes the configured minimum source-policy coverage. If either condition fails, the API persists `score: null` and displays **Insufficient evidence — no overall score**. No fallback score such as 0, 50, or a model confidence is used.

## Formula

Eligible reports calculate the following persisted components: evidence-supported claim assessment (30), evidence strength (20), independent corroboration (15), fact-check evidence (15), recency/freshness (10), and article transparency (10). Categories are explanatory labels conditioned on evidence coverage and policy version; they do not establish absolute truth.

## Source policy

`backend/app/fixtures/source_policy.json` is a versioned configuration file. It maps explicit domains to source type, quality class, weight, and rationale. Unmatched sources are **Unknown**, not automatically low or high quality. The model can receive policy-derived facts but cannot choose or override classifications.

## Local fixtures

Local fixture records are marked **Local demonstration data**. They exercise source provenance, scoring eligibility, contradiction, sharing, and scoreless uncertainty without presenting synthetic results as current real-world verification.
