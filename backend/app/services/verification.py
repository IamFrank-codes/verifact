from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from app.models import Article, Claim, Evidence, ProviderRun, Source, Verification, VerificationScore
from app.core.config import get_settings
from app.evidence.source_policy import policy
from app.evidence.providers import enabled_external_providers, EvidenceItem
from app.fixtures.deterministic import find_fixture, generic_claim
from app.services.extraction import extract_article, ExtractionError
from app.ai.structured import analyze_evidence, is_enabled

settings = get_settings()
VERDICT_VALUES = {'Supported by Available Evidence': 1.0, 'Mostly Supported': 0.78, 'Mixed or Potentially Misleading': 0.48, 'Contradicted by Available Evidence': 0.05}
QUALITY_VALUES = {'High': 0.95, 'Medium': 0.72, 'Low': 0.4, 'Unknown': 0.35}

def set_stage(db: Session, verification: Verification, stage: str, status: str = 'processing'):
    verification.stage, verification.status = stage, status
    db.commit()

def make_source(db: Session, item: EvidenceItem) -> Source:
    existing = db.query(Source).filter(Source.canonical_url == item.url).first()
    if existing:
        return existing
    classification = policy.classify(item.url)
    source = Source(canonical_url=item.url, name=item.name, domain=classification['domain'], source_type=classification['source_type'], quality_class=classification['quality_class'], policy_version=classification['policy_version'], policy_rule=classification['rule'], policy_rationale=classification['rationale'])
    db.add(source); db.flush()
    return source

def create_evidence(db: Session, claim: Claim, item: EvidenceItem, fixture: bool):
    source = make_source(db, item)
    db.add(Evidence(claim_id=claim.id, source_id=source.id, relationship_type=item.relationship_type, excerpt=item.excerpt, relevance=item.relevance, published_at=item.published_at, provider=item.provider, fixture=fixture))

def score_verification(db: Session, verification: Verification):
    claims = verification.claims
    checkable = [c for c in claims if c.checkable]
    valid = [c for c in checkable if c.verdict in VERDICT_VALUES]
    total_weight = sum(c.importance for c in checkable)
    coverage = (sum(c.importance for c in valid) / total_weight) if total_weight else 0.0
    quality_evidence = [e for c in valid for e in c.evidence]
    eligible = bool(checkable and valid and coverage >= settings.score_coverage_threshold and any(e.source.quality_class in {'High', 'Medium'} for e in quality_evidence))
    if not eligible:
        reason = 'No checkable factual claims were identified.' if not checkable else f'Only {coverage:.0%} of weighted checkable claims had a valid evidence assessment; VeriFact requires {settings.score_coverage_threshold:.0%} plus qualifying source-policy coverage before scoring.'
        verification.score = None; verification.score_band = None; verification.coverage_pct = round(coverage * 100, 1)
        verification.evidence_status = 'No checkable factual claims' if not checkable else 'Insufficient evidence — no overall score'
        db.add(VerificationScore(verification_id=verification.id, eligible=False, eligibility_reason=reason, components={'coverage_pct': round(coverage * 100, 1), 'threshold_pct': round(settings.score_coverage_threshold * 100, 1)}))
        return
    accuracy = 30 * sum(VERDICT_VALUES[c.verdict] * c.importance for c in valid) / sum(c.importance for c in valid)
    strength = 20 * sum(QUALITY_VALUES[e.source.quality_class] for e in quality_evidence) / len(quality_evidence)
    independent = min(15, 15 * len({e.source.domain for e in quality_evidence}) / 2)
    fact_check = min(15, 15 * sum(1 for e in quality_evidence if e.source.source_type == 'Fact-check organization') / 1)
    recency = 10 if any(e.published_at and e.published_at >= '2023' for e in quality_evidence) else 5
    transparency = 10 if verification.article and verification.article.title and verification.article.publisher else 6
    components = {'evidence_supported_claim_assessment': round(accuracy, 1), 'evidence_strength': round(strength, 1), 'independent_corroboration': round(independent, 1), 'fact_check_evidence': round(fact_check, 1), 'recency_and_freshness': round(recency, 1), 'article_transparency': round(transparency, 1)}
    score = round(sum(components.values()))
    band = 'Very High Evidence-Backed Credibility' if score >= 90 else 'High Evidence-Backed Credibility' if score >= 75 else 'Mixed Evidence-Backed Credibility' if score >= 60 else 'Low Evidence-Backed Credibility' if score >= 40 else 'Very Low Evidence-Backed Credibility'
    verification.score, verification.score_band, verification.coverage_pct = score, band, round(coverage * 100, 1)
    verification.evidence_status = 'Scored — evidence coverage sufficient'
    db.add(VerificationScore(verification_id=verification.id, eligible=True, eligibility_reason=f'{coverage:.0%} weighted claim coverage met the {settings.score_coverage_threshold:.0%} policy threshold with qualifying source-policy evidence.', components=components))

def run_verification(db: Session, verification_id: str):
    verification = db.query(Verification).options(joinedload(Verification.claims).joinedload(Claim.evidence).joinedload(Evidence.source), joinedload(Verification.article)).filter(Verification.id == verification_id).first()
    if not verification or verification.status not in {'queued', 'processing'}:
        return
    try:
        set_stage(db, verification, 'Processing input')
        content = verification.original_input
        if verification.input_type == 'url':
            set_stage(db, verification, 'Extracting article')
            if settings.mode == 'local-fixture' and 'fixture' in content.lower():
                article_data = {'url': content, 'title': 'VeriFact local fixture article', 'author': 'VeriFact Fixture Desk', 'publisher': 'VeriFact Fixture Archive', 'published_at': '2024-09-10', 'text': content}
            else:
                article_data = extract_article(content)
            article = Article(url=article_data['url'], title=article_data.get('title'), author=article_data.get('author'), publisher=article_data.get('publisher'), published_at=article_data.get('published_at'), extracted_text=article_data['text'], extraction_status='complete')
            db.add(article); db.flush(); verification.article_id = article.id; verification.article = article; content = article_data['text']; db.commit()
        set_stage(db, verification, 'Identifying factual claims')
        fixture = find_fixture(content) if settings.mode in {'local-fixture', 'hybrid'} else None
        result = fixture or generic_claim(content)
        claim = Claim(verification_id=verification.id, sequence=1, text=result['claim'], verdict=result['verdict'], explanation=result['explanation'], evidence_coverage='2 retained evidence records' if result['evidence'] else 'No retained evidence records', freshness_note='Evidence dates are displayed on each record. Local fixtures are demonstration data.')
        db.add(claim); db.flush(); db.commit()
        set_stage(db, verification, 'Retrieving and comparing evidence')
        items = list(result['evidence'])
        for provider in enabled_external_providers() if settings.mode != 'local-fixture' else []:
            try:
                found = provider.search(claim.text); items.extend(found); db.add(ProviderRun(verification_id=verification.id, provider=provider.name, status='success', message=f'{len(found)} record(s) returned.'))
            except Exception as exc:
                db.add(ProviderRun(verification_id=verification.id, provider=provider.name, status='unavailable', message=str(exc)[:500]))
        for item in items:
            create_evidence(db, claim, item, fixture=bool(result['evidence'] and item.provider == 'VeriFact local fixture'))
        db.commit()
        if settings.mode != 'local-fixture' and is_enabled():
            verification = db.query(Verification).options(joinedload(Verification.claims).joinedload(Claim.evidence).joinedload(Evidence.source)).filter(Verification.id == verification_id).first()
            analyzed_claim = verification.claims[0]
            packet = [{'id': evidence.id, 'source': evidence.source.name, 'url': evidence.source.canonical_url, 'source_type': evidence.source.source_type, 'quality_class': evidence.source.quality_class, 'published_at': evidence.published_at, 'excerpt': evidence.excerpt} for evidence in analyzed_claim.evidence]
            assessment = analyze_evidence(analyzed_claim.text, packet)
            if assessment:
                analyzed_claim.verdict = assessment.verdict
                analyzed_claim.explanation = assessment.explanation
                analyzed_claim.freshness_note = assessment.freshness_note
                referenced = set(assessment.supporting_ids + assessment.contradicting_ids + assessment.contextual_ids)
                analyzed_claim.evidence_coverage = f'{len(referenced)} model-referenced record(s) from {len(packet)} retained evidence record(s).'
                for evidence in analyzed_claim.evidence:
                    if evidence.id in assessment.supporting_ids:
                        evidence.relationship_type = 'supporting'
                    elif evidence.id in assessment.contradicting_ids:
                        evidence.relationship_type = 'contradicting'
                    else:
                        evidence.relationship_type = 'contextual'
                db.add(ProviderRun(verification_id=verification.id, provider='OpenAI-compatible evidence analysis', status='success', message='Structured analysis accepted with validated retained-evidence IDs.'))
            else:
                analyzed_claim.verdict = 'Insufficient Evidence'
                analyzed_claim.explanation = 'VeriFact retained evidence but could not obtain a valid structured analysis that cited only those records. No conclusion or score was produced.'
                analyzed_claim.evidence_coverage = f'{len(packet)} retained evidence record(s); structured analysis unavailable or invalid.'
                db.add(ProviderRun(verification_id=verification.id, provider='OpenAI-compatible evidence analysis', status='unavailable', message='No valid evidence-ID-bounded structured response was accepted.'))
            db.commit()
        set_stage(db, verification, 'Assessing evidence coverage')
        verification = db.query(Verification).options(joinedload(Verification.claims).joinedload(Claim.evidence).joinedload(Evidence.source), joinedload(Verification.article)).filter(Verification.id == verification_id).first()
        score_verification(db, verification)
        if verification.score is None:
            verification.summary = 'VeriFact found insufficient retained evidence to produce an overall score. This is not a finding that the submitted claim is true or false.'
        else:
            verification.summary = f'VeriFact produced an evidence-dependent score from {verification.coverage_pct:.0f}% weighted claim coverage. Review the cited records and policy context before drawing conclusions.'
        verification.stage, verification.status, verification.completed_at = 'Report ready', 'completed', datetime.now(timezone.utc)
        db.commit()
    except ExtractionError as exc:
        verification.status, verification.stage, verification.error_message, verification.evidence_status = 'failed', 'Article extraction needs input', str(exc), 'Processing incomplete'; db.commit()
    except Exception as exc:
        verification.status, verification.stage, verification.error_message, verification.evidence_status = 'failed', 'Verification incomplete', 'VeriFact could not complete this verification. Please retry or paste article text.', 'Processing incomplete'; db.commit()
