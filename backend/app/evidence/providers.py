from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic, sleep
from typing import Protocol
from datetime import timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
import xml.etree.ElementTree as ET
import httpx
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
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
                    reviewed_claim = ' '.join((item.get('text') or '').split())
                    review_title = ' '.join((review.get('title') or '').split())
                    rating = ' '.join((review.get('textualRating') or 'Fact-check record available.').split())
                    parts = []
                    if reviewed_claim:
                        parts.append(f'Reviewed claim: “{reviewed_claim}”')
                    if review_title:
                        parts.append(f'Review title: “{review_title}”')
                    parts.append(f'Review rating: “{rating}”')
                    output.append(EvidenceItem(review.get('publisher', {}).get('name', 'Fact-check publisher'), url, review.get('reviewDate'), ' '.join(parts), 'contextual', 'A third-party fact-check record was retrieved; its rating applies to the reviewed claim shown in the excerpt and must be matched to the submitted claim before use.', self.name))
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
    def _normalize_seendate(value: str | None) -> str | None:
        if not value:
            return None
        match = re.fullmatch(r'(\d{4})(\d{2})(\d{2})T?(\d{2})(\d{2})(\d{2})Z?', str(value))
        if not match:
            return str(value)
        year, month, day, hour, minute, second = match.groups()
        return f'{year}-{month}-{day}T{hour}:{minute}:{second}Z'

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
                published_at = self._normalize_seendate(item.get('seendate'))
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


class BingSportsOutletProvider:
    """Search one user-selected sports outlet through Bing News RSS, not its entire web domain."""
    retrieval_name = 'Bing News RSS'
    name = 'Bing News RSS'
    outlets = {
        'bbc.com': 'BBC Sport',
        'aljazeera.com': 'Al Jazeera Sports',
        'reuters.com': 'Reuters Sports',
        'skysports.com': 'Sky Sports',
    }
    stop_words = {'the', 'and', 'for', 'with', 'from', 'against', 'after', 'before', 'into', 'onto', 'over', 'under', 'to', 'of', 'in', 'on', 'at', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'has', 'have', 'had', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'do', 'does', 'did', 'their', 'his', 'her', 'its', 'who', 'what', 'when', 'where', 'why', 'how'}
    sports_terms = ('doping', 'ban', 'appeal', 'injury', 'transfer', 'suspension', 'cleared', 'return', 'goal', 'goals', 'scored', 'score', 'won', 'win', 'beat', 'defeated', 'loss', 'final', 'title', 'champion', 'champions', 'league', 'cup', 'rugby', 'football', 'soccer', 'tennis', 'race', 'medal', 'record', 'signed', 'coach', 'manager', 'match', 'tournament', 'olympic')
    sports_topic_markers = {'sport', 'sports', 'football', 'soccer', 'rugby', 'tennis', 'cricket', 'basketball', 'baseball', 'hockey', 'volleyball', 'golf', 'boxing', 'mma', 'ufc', 'cycling', 'swimming', 'athletics', 'wrestling', 'badminton', 'f1', 'formula1', 'fifa', 'uefa', 'olympic', 'olympics', 'messi', 'ronaldo', 'ballon', 'nba', 'nfl', 'mlb', 'nhl', 'wimbledon', 'nascar'}

    @classmethod
    def is_sports_related(cls, text: str) -> bool:
        words = re.findall(r'[a-z0-9]+', text.casefold())
        if set(words) & cls.sports_topic_markers:
            return True
        normalized = ' '.join(words)
        return any(phrase in normalized for phrase in ('world cup', 'champions league', 'premier league', 'ballon d or', 'formula one', 'grand slam'))

    def __init__(self, domain: str):
        if domain not in self.outlets:
            raise ValueError('Unsupported sports publisher domain.')
        self.domain = domain
        self.name = f'Bing News RSS ({self.outlets[domain]})'

    @classmethod
    def _search_query(cls, claim: str) -> str:
        words = re.findall(r'[A-Za-z0-9]+', claim)
        useful = []
        for word in words:
            normalized = word.casefold()
            if len(normalized) >= 3 and normalized not in cls.stop_words and normalized not in useful:
                useful.append(normalized)
        subject = useful[:3]
        topic = [term for term in cls.sports_terms if term in useful and term not in subject][:2]
        return ' '.join(subject + topic) or ' '.join(words[:12])

    @staticmethod
    def _text(element: ET.Element | None) -> str:
        if element is None or element.text is None:
            return ''
        return ' '.join(re.sub(r'<[^>]+>', ' ', unescape(element.text)).split())

    @staticmethod
    def _published(value: str) -> str | None:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _excerpt(text: str, limit: int = 1200) -> str:
        text = ' '.join(text.split())
        return text if len(text) <= limit else text[:limit].rsplit(' ', 1)[0].rstrip() + '…'

    def _publisher_url(self, link: str) -> str | None:
        parsed = urlparse(link)
        candidate = parse_qs(parsed.query).get('url', [None])[0] if parsed.hostname in {'bing.com', 'www.bing.com'} else link
        if not candidate:
            return None
        target = urlparse(candidate)
        host = (target.hostname or '').lower().removeprefix('www.')
        if target.scheme not in {'http', 'https'} or not (host == self.domain or host.endswith('.' + self.domain)):
            return None
        if target.username or target.password or not target.path:
            return None
        return urlunparse(('https', target.netloc, target.path, target.params, target.query, ''))

    def search(self, claim: str) -> list[EvidenceItem]:
        query = f'{self._search_query(claim)} site:{self.domain}'
        response = httpx.get(
            'https://www.bing.com/news/search',
            params={'q': query, 'format': 'rss'},
            timeout=8,
            headers={'User-Agent': 'VeriFact/1.0 (sports evidence search)'},
        )
        response.raise_for_status()
        if len(response.content) > 1_000_000:
            raise ValueError('Sports news RSS response exceeded the processing limit.')
        root = ET.fromstring(response.content)
        output = []
        query_terms = set(self._search_query(claim).split())
        for node in root.findall('./channel/item')[:10]:
            title = self._text(node.find('title'))
            description = self._text(node.find('description'))
            url = self._publisher_url(self._text(node.find('link')))
            if not url or not title:
                continue
            result_terms = set(re.findall(r'[a-z0-9]+', f'{title} {description}'.casefold()))
            if len(query_terms & result_terms) < min(2, len(query_terms)):
                continue
            excerpt = f'{title}. {description}'.strip() if description else title
            published_at = self._published(self._text(node.find('pubDate')))
            try:
                article = extract_article(url)
                final_url = self._publisher_url(article.get('url') or url)
                article_text = (article.get('text') or '').strip()
                if final_url and article_text:
                    url = final_url
                    excerpt = self._excerpt(article_text)
                    published_at = article.get('published_at') or published_at
            except Exception:
                # Keep the validated publisher link and RSS snippet if article text is blocked.
                pass
            output.append(EvidenceItem(
                self.outlets[self.domain],
                url,
                published_at,
                excerpt[:1200],
                'contextual',
                'A domain-restricted sports-news result was retrieved. Confirm that its headline and excerpt directly address the submitted claim before using it as support or contradiction.',
                self.retrieval_name,
            ))
            break
        return output


def enabled_external_providers() -> list[EvidenceProvider]:
    settings = get_settings()
    providers: list[EvidenceProvider] = []
    if settings.google_factcheck_key:
        providers.append(GoogleFactCheckProvider())
    if settings.gdelt_enabled:
        providers.append(GDELTProvider())
    if settings.newsapi_key:
        providers.append(NewsAPIProvider())
    if settings.sports_source_search_enabled:
        providers.extend(BingSportsOutletProvider(domain) for domain in BingSportsOutletProvider.outlets)
    return providers
