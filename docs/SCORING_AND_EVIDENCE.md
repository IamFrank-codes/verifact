# Scoring and evidence in the Academic Demo

VeriFact separates evidence retrieval, source-policy classification, evidence-bounded interpretation, and score calculation. Groq can assist with interpreting retained evidence, but it does not set source quality or calculate the score.

## URL/article claim workflow

For a URL submission, VeriFact extracts the article title and body, then asks the configured structured model to select one concise, checkable factual claim that is central to the article and directly aligned with its headline. It preserves the headline’s qualifications and uses the body to clarify rather than replace the headline’s proposition. The selected claim is stored in the report, shown with its extraction rationale, and used as the evidence-provider search query. The article URL itself is metadata, not evidence for the claim.

If no single checkable headline-aligned claim can be selected, VeriFact records the article and claim-selection rationale but skips evidence search; the claim is marked uncheckable and receives no score. If structured claim extraction is unavailable but a headline exists, the headline is used as a provisional search claim and labelled as a fallback. Evidence assessment and score calculation then use the same evidence packet validation, source policy, coverage threshold, and score formula as other submissions. URL input can therefore receive a score when its extracted claim is validly assessed and the score eligibility criteria are met; it is not guaranteed a score merely because the article is accessible.

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
| `reuters.com/sports/**` | High | User-selected Reuters Sports reference |
| Other `reuters.com` paths | Medium | Established news organization |
| `apnews.com/sports/**` | High | User-selected Associated Press Sports reference |
| `espn.com` | High | User-selected ESPN sports reference |
| `bbc.com` | Medium | User-selected sports news organization |
| `aljazeera.com` | Medium | User-selected sports news organization |
| `skysports.com` | High | User-selected Sky Sports reference |
| `theathletic.com` | High | User-selected The Athletic sports reference |
| `supersport.com` | High | User-selected SuperSport reference |
| `theguardian.com/sport/**` | High | User-selected Guardian Sport reference |
| `cbssports.com` | High | User-selected CBS Sports reference |
| `olympics.com` | High | Official Olympic information and results |
| Any unmatched domain | Unknown | Unclassified source |

A domain/path absent from the policy is **Unknown** unless a broader domain rule applies. Unknown does not mean false or inherently untrustworthy, but it cannot by itself satisfy the qualifying-source gate. Policy version 1.2.0 maps the user-provided “Very high” and “High” reliability labels to VeriFact's supported **High** class; the scoring engine does not distinguish those as separate classes. Reuters and Guardian sports rules are path-scoped so non-sports pages do not inherit the sports classification. These are configured publisher-level policy references, not an independent audit of publisher quality or a guarantee that an individual article supports a claim.

The configured sports references include the sports coverage supplied by the system owner: Reuters Sports (football, F1, tennis, cricket, Olympics), AP Sports (football, basketball, tennis, Olympics), ESPN (football, NBA, NFL, F1, tennis), Sky Sports (football, F1, boxing, cricket), The Athletic (football, basketball, NFL, other sports), SuperSport (football, rugby, cricket, athletics), The Guardian Sport (football, tennis, cricket, rugby), CBS Sports (NFL, NBA, football, golf), and Olympics.com (Olympic sports and official results). VeriFact remains available for other topics. A source-policy match does not guarantee that a specific article directly supports a claim. Absence of a claim from any selected publisher is not evidence that the claim is false.

The source-policy additions classify matching results returned by enabled providers; they do **not** automatically add new search providers. In `academic-demo` mode, the current Bing News RSS sports-search adapters remain limited to BBC, Al Jazeera, Reuters, and Sky Sports. Clear sports claims automatically search those outlets, even when `VERIFACT_SPORTS_SOURCE_SEARCH_ENABLED` is false. Set it to `true` to search those selected outlets for every claim, or to enable them in other live modes. Searches use a separate `site:` restriction for each configured outlet, unwrap Bing's redirect link, and discard results whose final URL is outside the allowed domain. The saved evidence URL points to the publisher, not Bing. The report groups these searches into one Bing News RSS retrieval entry; individual evidence records still name their publisher. This path supplements Google Fact Check Tools, GDELT, and NewsAPI; it does not replace general-topic searches. Search results can be incomplete or blocked by the index, so zero results means “not found by this search,” not “false.”

## What the providers and model do

Google Fact Check Tools searches previously published ClaimReview records; no match is not a verdict. GDELT and optional NewsAPI help discover news coverage and source links. Groq assesses the claim against the retained evidence packet and may produce a short related-news summary. VeriFact validates referenced evidence IDs and computes any eligible score itself.

Google Fact Check evidence retains the exact reviewed claim, review title, and rating together. The rating applies only to the reviewed claim. If its proposition does not match the submitted claim, it must be treated as contextual, not as evidence for or against the submitted claim.

For time-sensitive sports results, the assessor is instructed to use publication dates and separate historical events from later changes in status. An appeal being resolved later, for example, does not undo the fact that the appeal was filed earlier.

If providers return no relevant, retained evidence—or if the retained sources fail the policy gate—the report remains scoreless and explains the limitation rather than inventing citations or a summary.
