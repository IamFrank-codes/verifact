# Scoring and evidence in the Academic Demo

VeriFact separates evidence retrieval, source-policy classification, evidence-bounded interpretation, and score calculation. Groq can assist with interpreting retained evidence, but it does not set source quality or calculate the score.

## When a score is available

A report is score-eligible only when all of these conditions are met:

1. At least **60% of the weighted checkable claims** have a valid evidence assessment supported or contradicted by a cited record. The default threshold is configurable through `VERIFACT_SCORE_COVERAGE_THRESHOLD`.
2. At least one supporting or contradicting evidence item attached to a validly assessed claim comes from a source classified **High** or **Medium** by the source policy. Context-only records, including merely related news or fact-check results, do not satisfy these gates.

If a condition fails, the report stores `score: null`, displays **Insufficient evidence — no overall score**, and gives the specific eligibility reason. VeriFact does not replace a missing score with zero, a midpoint, or model confidence. Coverage is calculated over checkable claims and their importance weights; it is not a measure of how much of the original paragraph was understood.

## Score components

For an eligible report, the deterministic score combines six persisted components, totaling 100 possible points:

| Component | Maximum | How it is calculated |
|---|---:|---|
| Evidence-supported claim assessment | 30 | Importance-weighted mean of the assessment values: Supported 1.00, Mostly Supported 0.78, Mixed or Potentially Misleading 0.48, and Contradicted 0.05. |
| Evidence strength | 20 | Mean source-quality value: High 0.95, Medium 0.72, Low 0.40, Unknown 0.35. |
| Independent corroboration | 15 | Up to 15 points based on distinct evidence domains; full points are reached at two domains. |
| Fact-check evidence | 15 | Up to 15 points for a retained source classified as a Fact-check organization. |
| Recency and freshness | 10 | 10 points if qualifying evidence includes a publication date from 2023 onward; otherwise 5. |
| Article transparency | 10 | 10 points when the submitted article has both a title and publisher; otherwise 6. |

The report exposes eligibility, formula version, coverage, and component values. Bands are **Very High Evidence-Backed Credibility** (90–100), **High** (75–89), **Mixed** (60–74), **Low** (40–59), and **Very Low** (below 40). The score describes the retained evidence under the current policy; it is not a guarantee of absolute truth.

## Current source policy

`backend/app/fixtures/source_policy.json` is the versioned policy file. It maps recognized domains to a source type, quality class, policy weight, and rationale. The backend applies these rules; the model cannot assign or override a source's quality class.

| Domain | Current class | Source type |
|---|---|---|
| `who.int` | High | International organization |
| `cdc.gov` | High | Government agency |
| `nih.gov` | High | Government research institution |
| `factcheck.org` | High | Fact-check organization |
| `reuters.com` | Medium | Established news organization |
| Any unmatched domain | Unknown | Unclassified source |

A domain absent from the policy is **Unknown**. Unknown does not mean false or inherently untrustworthy, but it cannot by itself satisfy the qualifying-source gate. To add a domain, update the policy with a justified classification and rationale, increment its version, and run the Academic Demo tests.

## What the providers and model do

For URL submissions, VeriFact searches with the extracted headline plus the article lead to reduce broad, unrelated matches. Google Fact Check Tools searches previously published ClaimReview records; no match is not a verdict. GDELT and optional NewsAPI help discover news coverage and source links. Groq assesses the claim against the retained evidence packet and may produce a short related-news summary. VeriFact validates referenced evidence IDs and computes any eligible score itself.

If providers return no relevant, retained evidence—or if the retained sources fail the policy gate—the report remains scoreless and explains the limitation rather than inventing citations or a summary.
