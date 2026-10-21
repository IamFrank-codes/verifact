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
    news_summary: str = Field(min_length=1, max_length=1200)
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

class EvidenceAnalysisError(Exception):
    """Safe, user-facing diagnosis for an analysis response that cannot be used."""

def analyze_evidence(claim_text: str, evidence_packet: list[dict]) -> EvidenceAssessment | None:
    """Assess only source records supplied by VeriFact; never permits model-created citations."""
    if not is_enabled() or not evidence_packet:
        return None
    schema = {
        'type': 'object',
        'properties': {
            'verdict': {'type': 'string', 'enum': ['Supported by Available Evidence', 'Mostly Supported', 'Mixed or Potentially Misleading', 'Contradicted by Available Evidence', 'Insufficient Evidence']},
            'explanation': {'type': 'string'},
            'news_summary': {'type': 'string'},
            'supporting_ids': {'type': 'array', 'items': {'type': 'string'}},
            'contradicting_ids': {'type': 'array', 'items': {'type': 'string'}},
            'contextual_ids': {'type': 'array', 'items': {'type': 'string'}},
            'freshness_note': {'type': 'string'},
        },
        'required': ['verdict', 'explanation', 'news_summary', 'supporting_ids', 'contradicting_ids', 'contextual_ids', 'freshness_note'],
        'additionalProperties': False,
    }
    instructions = (
        'You are the evidence-analysis component of VeriFact. Assess the claim only against the supplied evidence packet. '
        'Do not use background knowledge. Do not create evidence, quotations, links, source-quality labels, or IDs. '
        'For fact-check records, the excerpt may include a Reviewed claim, Review title, and Review rating. The rating applies only to the Reviewed claim, not automatically to the user claim being assessed. Compare their subjects, polarity, qualifiers, and meaning. If the reviewed proposition is different, opposite, or not clear enough to match, classify that record as contextual and do not use its rating to support or contradict the user claim. A fact-check title may explain which side the rating addresses. '
        'Write news_summary as 2-5 sentences summarizing only what the supplied excerpts report. If the excerpts are too thin to support two sentences, state that limitation rather than padding or inventing details. If an excerpt contains only a headline, say the summary is headline-only. Mention material disagreement between sources. '
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
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            message = f'The configured model provider rejected the API key (HTTP {status_code}); check the backend key and endpoint configuration.'
        elif status_code == 429:
            message = 'The configured model provider rate-limited the request (HTTP 429); check the account quota and retry later.'
        elif status_code in {400, 404}:
            message = f'The configured model provider rejected the request (HTTP {status_code}); check the model ID and strict JSON-schema support.'
        else:
            message = f'The configured model provider returned HTTP {status_code}; no assessment or summary was accepted.'
        raise EvidenceAnalysisError(message) from None
    except httpx.TimeoutException:
        raise EvidenceAnalysisError('The configured model provider timed out; no assessment or summary was accepted.') from None
    except httpx.RequestError:
        raise EvidenceAnalysisError('The configured model provider could not be reached; no assessment or summary was accepted.') from None
    except (KeyError, TypeError, ValueError, ValidationError):
        raise EvidenceAnalysisError('The model response was not valid for VeriFact’s structured schema; no assessment or summary was accepted.') from None
    allowed_ids = {str(item['id']) for item in evidence_packet}
    returned_ids = set(assessment.supporting_ids + assessment.contradicting_ids + assessment.contextual_ids)
    if not returned_ids.issubset(allowed_ids):
        raise EvidenceAnalysisError('The model cited evidence IDs outside the retained source packet; the assessment was rejected.')
    if assessment.verdict != 'Insufficient Evidence' and not returned_ids:
        raise EvidenceAnalysisError('The model returned a verdict without citing retained evidence; the assessment was rejected.')
    return assessment
