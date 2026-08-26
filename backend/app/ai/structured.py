import json
from typing import Literal
import httpx
from pydantic import BaseModel, Field, ValidationError
from app.core.config import get_settings

settings = get_settings()

Verdict = Literal[
    'Supported by Available Evidence',
    'Mostly Supported',
    'Mixed or Potentially Misleading',
    'Contradicted by Available Evidence',
    'Insufficient Evidence',
]

class EvidenceAssessment(BaseModel):
    verdict: Verdict
    explanation: str = Field(min_length=1, max_length=1600)
    supporting_ids: list[str]
    contradicting_ids: list[str]
    contextual_ids: list[str]
    freshness_note: str = Field(min_length=1, max_length=600)


def is_enabled() -> bool:
    return bool(settings.openai_api_key)


def _endpoint() -> str:
    base = (settings.openai_base_url or 'https://api.openai.com/v1').rstrip('/')
    if not base.endswith('/v1'):
        base += '/v1'
    return base + '/chat/completions'


def analyze_evidence(claim_text: str, evidence_packet: list[dict]) -> EvidenceAssessment | None:
    """Assess only source records supplied by VeriFact; never permits model-created citations."""
    if not is_enabled() or not evidence_packet:
        return None
    schema = {
        'type': 'object',
        'properties': {
            'verdict': {'type': 'string', 'enum': ['Supported by Available Evidence', 'Mostly Supported', 'Mixed or Potentially Misleading', 'Contradicted by Available Evidence', 'Insufficient Evidence']},
            'explanation': {'type': 'string'},
            'supporting_ids': {'type': 'array', 'items': {'type': 'string'}},
            'contradicting_ids': {'type': 'array', 'items': {'type': 'string'}},
            'contextual_ids': {'type': 'array', 'items': {'type': 'string'}},
            'freshness_note': {'type': 'string'},
        },
        'required': ['verdict', 'explanation', 'supporting_ids', 'contradicting_ids', 'contextual_ids', 'freshness_note'],
        'additionalProperties': False,
    }
    instructions = (
        'You are the evidence-analysis component of VeriFact. Assess the claim only against the supplied evidence packet. '
        'Do not use background knowledge. Do not create evidence, quotations, links, source-quality labels, or IDs. '
        'Use Insufficient Evidence if the packet cannot establish a bounded assessment. '
        'A verdict is an evidence assessment, never a declaration of absolute truth. '
        'Return only the requested JSON schema.'
    )
    payload = {
        'model': settings.openai_model,
        'messages': [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': json.dumps({'claim': claim_text, 'evidence_packet': evidence_packet}, ensure_ascii=False)},
        ],
        'temperature': 0,
        'response_format': {'type': 'json_schema', 'json_schema': {'name': 'verifact_evidence_assessment', 'strict': True, 'schema': schema}},
    }
    try:
        response = httpx.post(_endpoint(), json=payload, headers={'Authorization': f'Bearer {settings.openai_api_key}', 'Content-Type': 'application/json'}, timeout=35)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        assessment = EvidenceAssessment.model_validate_json(content)
    except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError):
        return None
    allowed_ids = {str(item['id']) for item in evidence_packet}
    returned_ids = set(assessment.supporting_ids + assessment.contradicting_ids + assessment.contextual_ids)
    if not returned_ids.issubset(allowed_ids):
        return None
    if assessment.verdict != 'Insufficient Evidence' and not returned_ids:
        return None
    return assessment
