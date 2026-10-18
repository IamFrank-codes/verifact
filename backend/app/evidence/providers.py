from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic, sleep
from typing import Protocol
import re
import httpx
from app.core.config import get_settings
from app.services.extraction import extract_article


@dataclass
class EvidenceItem:
    name: str
    url: str
    published_at: str | None
    excerpt: str
    relationship_type: str
    relevance: str
    provider: str


class EvidenceProvider(Protocol):
    name: str

    def search(self, claim: str) -> list[EvidenceItem]: ...


class GoogleFactCheckProvider:
    name = 'Google Fact Check Tools'

    def search(self, claim: str) -> list[EvidenceItem]:
        key = get_settings().google_factcheck_key
        if not key:
            return []
        response = httpx.get('https://factchecktools.googleapis.com/v1alpha1/claims:search', params={'query': claim, 'key': key}, timeout=10)
        response.raise_for_status()
        output = []
        for item in response.json().get('claims', [])[:5]:
            for review in item.get('claimReview', [])[:2]:
                url = review.get('url')
                if url:
                    output.append(EvidenceItem(review.get('publisher', {}).get('name', 'Fact-check publisher'), url, review.get('reviewDate'), review.get('textualRating', 'Fact-check record available.'), 'contextual', 'A third-party fact-check record was retrieved for comparison.', self.name))
        return output


# GDELT asks clients to issue no more than one request every five seconds.
# The lock and cache are process-local; keep this provider single-process or use
# a shared limiter if deploying multiple backend workers/replicas.
_GDELT_MIN_INTERVAL_SECONDS = 5.25
_GDELT_CACHE_TTL_SECONDS = 300
_gdelt_lock = Lock()
_gdelt_last_request_at = 0.0
_gdelt_cache: dict[str, tuple[float, list[EvidenceItem]]] = {}


class GDELTProvider:
    name = 'GDELT'

    @staticmethod
    def _excerpt(text: str, limit: int = 1200) -> str:
        text = ' '.join(text.split())
        if len(text) <= limit:
            return text
        return text[:limit].rsplit(' ', 1)[0].rstrip() + '…'

    @staticmethod
    def _claim_key(claim: str) -> str:
        return ' '.join(claim.casefold().split())

    @staticmethod
    def _wait_for_slot() -> None:
        global _gdelt_last_request_at
        elapsed = monotonic() - _gdelt_last_request_at
        if elapsed < _GDELT_MIN_INTERVAL_SECONDS:
            sleep(_GDELT_MIN_INTERVAL_SECONDS - elapsed)
        _gdelt_last_request_at = monotonic()

    @staticmethod
    def _retry_delay(response: httpx.Response) -> float:
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return min(max(float(retry_after), _GDELT_MIN_INTERVAL_SECONDS), 60.0)
            except ValueError:
                pass
        match = re.search(r'one every\s+(\d+(?:\.\d+)?)\s+seconds?', response.text, re.IGNORECASE)
        if match:
            return min(max(float(match.group(1)), _GDELT_MIN_INTERVAL_SECONDS), 60.0)
        return _GDELT_MIN_INTERVAL_SECONDS

    def search(self, claim: str) -> list[EvidenceItem]:
        if not get_settings().gdelt_enabled:
            return []
        key = self._claim_key(claim)
        with _gdelt_lock:
            cached = _gdelt_cache.get(key)
            now = monotonic()
            if cached and now - cached[0] < _GDELT_CACHE_TTL_SECONDS:
                return list(cached[1])
            if cached:
                _gdelt_cache.pop(key, None)

            params = {'query': claim, 'mode': 'artlist', 'format': 'json', 'maxrecords': 3, 'timespan': '7d'}
            for attempt in range(2):
                self._wait_for_slot()
                response = httpx.get(
                    'https://api.gdeltproject.org/api/v2/doc/doc',
                    params=params,
                    timeout=10,
                    headers={'User-Agent': 'VeriFact/1.0 (evidence search)'},
                )
                if response.status_code != 429 or attempt == 1:
                    response.raise_for_status()
                    break
                delay = self._retry_delay(response)
                sleep(delay)

            output = []
            for item in response.json().get('articles', [])[:3]:
                url = item.get('url')
                if not url:
                    continue
                headline = (item.get('title') or 'Related news article')[:300]
                excerpt = headline
                name = headline
                published_at = item.get('seendate')
                try:
                    article = extract_article(url)
                    article_text = article.get('text', '').strip()
                    if article_text:
                        excerpt = self._excerpt(article_text)
                    name = (article.get('title') or headline)[:300]
                    published_at = published_at or article.get('published_at')
                except Exception:
                    # Preserve the source link and headline when its publisher blocks extraction.
                    pass
                output.append(EvidenceItem(name, url, published_at, excerpt, 'contextual', 'A related news article was retrieved for comparison; it does not independently establish the claim.', self.name))
            _gdelt_cache[key] = (monotonic(), output)
            return list(output)
class NewsAPIProvider:
    name = 'NewsAPI'

    def search(self, claim: str) -> list[EvidenceItem]:
        key = get_settings().newsapi_key
        if not key:
            return []
        response = httpx.get('https://newsapi.org/v2/everything', params={'q': claim, 'apiKey': key, 'pageSize': 5, 'language': 'en', 'sortBy': 'relevancy'}, timeout=10)
        response.raise_for_status()
        return [EvidenceItem(x.get('source', {}).get('name', 'News source'), x['url'], x.get('publishedAt'), x.get('description') or x.get('title') or 'Relevant article available.', 'contextual', 'A news-search result was retrieved for contextual comparison.', self.name) for x in response.json().get('articles', []) if x.get('url')]


def enabled_external_providers() -> list[EvidenceProvider]:
    settings = get_settings()
    providers: list[EvidenceProvider] = []
    if settings.google_factcheck_key:
        providers.append(GoogleFactCheckProvider())
    if settings.gdelt_enabled:
        providers.append(GDELTProvider())
    if settings.newsapi_key:
        providers.append(NewsAPIProvider())
    return providers
