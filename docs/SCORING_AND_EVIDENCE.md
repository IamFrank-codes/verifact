# Scoring and evidence in the Academic Demo

VeriFact separates evidence retrieval, source-policy classification, evidence-bounded interpretation, and score calculation. Groq can assist with interpreting retained evidence, but it does not set source quality or calculate the score.

## When a score is available

A report is score-eligible only when all of these conditions are met:

1. At least **60% of the weighted checkable claims** have a valid evidence assessment. The default threshold is configurable through `VERIFACT_SCORE_COVERAGE_THRESHOLD`.
2. At least one retained evidence item attached to a validly assessed claim comes from a source classified **High** or **Medium** by the source policy.

If a condition fails, the report stores `score: null` and displays **Insufficient evidence — no overall score**. VeriFact does not replace a missing score with zero, a midpoint, or model confidence. Coverage is calculated over checkable claims and their importance weights; it is not a measure of how much of the original paragraph was understood.

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
| `bbc.com` | Medium | User-selected sports news organization |
| `aljazeera.com` | Medium | User-selected sports news organization |
| `skysports.com` | Medium | User-selected sports news organization |
| Any unmatched domain | Unknown | Unclassified source |

A domain absent from the policy is **Unknown**. Unknown does not mean false or inherently untrustworthy, but it cannot by itself satisfy the qualifying-source gate. To add a domain, update the policy with a justified classification and rationale, increment its version, and run the Academic Demo tests.

The sports publishers are user-selected references for sports testing, not a topic restriction. VeriFact remains available for other topics. A source-domain match contributes Medium source quality; it does not guarantee that a specific article directly supports a claim. Absence of a claim from any selected publisher is not evidence that the claim is false.

To test these outlets as search sources, set `VERIFACT_SPORTS_SOURCE_SEARCH_ENABLED=true`. VeriFact then runs bounded Bing News RSS searches with a separate `site:` restriction for each selected domain, unwraps Bing's redirect link, and discards results whose final URL is outside that publisher's allowed domain. The saved evidence URL points to the publisher, not Bing. The report groups these searches into one Bing News RSS retrieval entry; individual evidence records still name their publisher. This optional path supplements Google Fact Check Tools, GDELT, and NewsAPI; it does not replace general-topic searches. Search results can be incomplete or blocked by the index, so zero results means “not found by this search,” not “false.”

## What the providers and model do

Google Fact Check Tools searches previously published ClaimReview records; no match is not a verdict. GDELT and optional NewsAPI help discover news coverage and source links. Groq assesses the claim against the retained evidence packet and may produce a short related-news summary. VeriFact validates referenced evidence IDs and computes any eligible score itself.

Google Fact Check evidence retains the exact reviewed claim, review title, and rating together. The rating applies only to the reviewed claim. If its proposition does not match the submitted claim, it must be treated as contextual, not as evidence for or against the submitted claim.

For time-sensitive sports results, the assessor is instructed to use publication dates and separate historical events from later changes in status. An appeal being resolved later, for example, does not undo the fact that the appeal was filed earlier.

If providers return no relevant, retained evidence—or if the retained sources fail the policy gate—the report remains scoreless and explains the limitation rather than inventing citations or a summary.
