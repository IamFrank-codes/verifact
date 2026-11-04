from __future__ import annotations

from html import escape
from io import BytesIO
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether


def _safe_text(value, limit: int | None = None) -> str:
    """Normalize potentially untrusted database text for ReportLab's paragraph parser."""
    text = '' if value is None else str(value)
    if limit is not None and len(text) > limit:
        text = text[:limit] + '…'
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '�', text)
    # ReportLab's built-in fonts are Latin-1; replace unsupported glyphs rather than fail.
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    return escape(text, quote=True).replace('\n', '<br/>')


def render_verification_pdf(verification) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch,
                            topMargin=0.65 * inch, bottomMargin=0.65 * inch,
                            title='VeriFact Verification Report', author='VeriFact')
    base = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=base['Title'], fontName='Helvetica-Bold', fontSize=19, leading=23, textColor=colors.HexColor('#17324d'), alignment=TA_LEFT, spaceAfter=12)
    section_style = ParagraphStyle('Section', parent=base['Heading2'], fontSize=12, leading=15, textColor=colors.HexColor('#17324d'), spaceBefore=10, spaceAfter=5)
    body_style = ParagraphStyle('SafeBody', parent=base['BodyText'], fontName='Helvetica', fontSize=9, leading=12, wordWrap='CJK', splitLongWords=1, spaceAfter=5)
    small_style = ParagraphStyle('Small', parent=body_style, fontSize=8, leading=10, textColor=colors.HexColor('#4b5563'))
    story = [Paragraph('VeriFact Verification Report', title_style)]
    story.append(Paragraph(f'<b>Input type:</b> {_safe_text(verification.input_type)}', body_style))
    story.append(Paragraph(f'<b>Submitted content:</b><br/>{_safe_text(verification.original_input, 12000)}', body_style))
    story.append(Paragraph(f'<b>Evidence status:</b> {_safe_text(verification.evidence_status or "Not available")}', body_style))
    score = 'No overall score' if verification.score is None else f'{verification.score:g}' + (f' ({_safe_text(verification.score_band)})' if verification.score_band else '')
    story.append(Paragraph(f'<b>Score:</b> {_safe_text(score)}', body_style))
    story.append(Paragraph('<b>Summary</b>', section_style))
    story.append(Paragraph(_safe_text(verification.summary or 'No summary available.'), body_style))
    story.append(Paragraph('<b>Claim assessments</b>', section_style))
    claims = sorted(verification.claims or [], key=lambda claim: claim.sequence)
    if not claims:
        story.append(Paragraph('No claim assessments are available.', body_style))
    for claim in claims:
        parts = [Paragraph(f'<b>Claim {claim.sequence}:</b> {_safe_text(claim.text)}', body_style)]
        parts.append(Paragraph(f'<b>Assessment:</b> {_safe_text(claim.verdict or "Not assessed")}', body_style))
        if claim.explanation:
            parts.append(Paragraph(f'<b>Explanation:</b> {_safe_text(claim.explanation)}', body_style))
        story.append(KeepTogether(parts))
    story.append(Paragraph('<b>Retained evidence</b>', section_style))
    evidence_items = [(claim, item) for claim in claims for item in (claim.evidence or [])]
    if not evidence_items:
        story.append(Paragraph('No evidence records were retained.', body_style))
    for claim, evidence in evidence_items:
        source = evidence.source
        fields = [
            f'<b>Claim {claim.sequence} · {_safe_text(evidence.relationship_type or "Evidence")}</b>',
            f'<b>Source:</b> {_safe_text(source.name if source else "Unknown source")}',
            f'<b>URL:</b> {_safe_text(source.canonical_url if source else "Unavailable", 2000)}',
            f'<b>Source class:</b> {_safe_text(source.quality_class if source else "Unknown")}',
            f'<b>Publication date:</b> {_safe_text(evidence.published_at or "Not provided")}',
            f'<b>Excerpt:</b> {_safe_text(evidence.excerpt, 6000)}',
            f'<b>Relevance:</b> {_safe_text(evidence.relevance, 2000)}',
        ]
        story.append(KeepTogether([Paragraph(field, body_style) for field in fields]))
    story.extend([Spacer(1, 9), Paragraph('Score disclaimer', section_style), Paragraph(
        'Any score is conditional on the evidence retrieved, retained, and eligible under VeriFact policy at the time of this report; it is not a guarantee of truth. A score may be omitted when evidence coverage or policy eligibility is insufficient.', small_style)])
    doc.build(story)
    result = buffer.getvalue()
    if not result.startswith(b'%PDF'):
        raise RuntimeError('ReportLab did not produce a valid PDF document.')
    return result
