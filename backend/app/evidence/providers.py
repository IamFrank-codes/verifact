from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
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


class GDELTProvider:
    name = 'GDELT'

    @staticmethod
    def _excerpt(text: str, limit: int = 1200) -> str:
        text = ' '.join(text.split())
        if len(text) <= limit:
            return text
        return text[:limit].rsplit(' ', 1)[0].rstrip() + '…'

    def search(self, claim: str) -> list[EvidenceItem]:
        if not get_settings().gdelt_enabled:
            return []
        response = httpx.get(
            'https://api.gdeltproject.org/api/v2/doc/doc',
            params={'query': claim, 'mode': 'artlist', 'format': 'json', 'maxrecords': 3, 'timespan': '7d'},
            timeout=10,
        )
        response.raise_for_status()
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
            output.append(EvidenceItem(
                name,
                url,
                published_at,
                excerpt,
                'contextual',
                'A recent article matching the claim search was retrieved; the excerpt may be headline-only if the publisher page was inaccessible.',
                self.name,
            ))
        return output


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
