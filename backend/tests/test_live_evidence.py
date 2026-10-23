import json
import os
from types import SimpleNamespace
from unittest.mock import Mock

os.environ['VERIFACT_DATABASE_URL'] = 'sqlite:///./test_verifact.db'
os.environ['VERIFACT_MODE'] = 'local-fixture'

import httpx

from app.ai import structured
from app.evidence import providers
from app.evidence.source_policy import policy
from app.services import verification


def test_google_factcheck_retains_exact_claim_title_and_rating(monkeypatch):
    monkeypatch.setattr(providers, 'get_settings', lambda: SimpleNamespace(google_factcheck_key='test-key'))
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {'claims': [{
        'text': 'COVID-19 vaccines do not reduce hospitalization.',
        'claimReview': [{
            'publisher': {'name': 'Example Fact Checker'},
            'url': 'https://factcheck.example/review',
            'reviewDate': '2026-10-20',
            'title': 'Vaccines reduce hospitalization, contrary to this post',
            'textualRating': 'False',
        }],
    }]}
    monkeypatch.setattr(providers.httpx, 'get', lambda *args, **kwargs: response)

    evidence = providers.GoogleFactCheckProvider().search('COVID-19 vaccines reduce hospitalization.')

    assert len(evidence) == 1
    assert 'Reviewed claim: “COVID-19 vaccines do not reduce hospitalization.”' in evidence[0].excerpt
    assert 'Review title: “Vaccines reduce hospitalization, contrary to this post”' in evidence[0].excerpt
    assert 'Review rating: “False”' in evidence[0].excerpt
    assert 'rating applies to the reviewed claim' in evidence[0].relevance


def test_user_selected_sports_publishers_are_medium_policy_sources():
    for url, expected_domain in [
        ('https://www.bbc.com/sport/football', 'bbc.com'),
        ('https://www.aljazeera.com/sports/football', 'aljazeera.com'),
        ('https://www.reuters.com/sports/soccer/', 'reuters.com'),
        ('https://www.skysports.com/rugby-union', 'skysports.com'),
    ]:
        classified = policy.classify(url)
        assert classified['domain'] == expected_domain
        assert classified['quality_class'] == 'Medium'


def test_bing_sports_search_unwraps_and_domain_validates_results(monkeypatch):
    xml = '''<rss><channel>
      <item><title>Updated Mudryk status - Sky Sports</title>
        <link>https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fwww.skysports.com%2Ffootball%2Fnews%2Fmudryk-update</link>
        <description><![CDATA[The appeal was resolved and the player may return.]]></description>
        <pubDate>Fri, 31 Jul 2026 12:00:00 GMT</pubDate>
      </item>
      <item><title>Chelsea transfer update</title>
        <link>https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fwww.skysports.com%2Ffootball%2Fnews%2Fchelsea-transfer</link>
        <description>Another Chelsea signing was announced.</description>
      </item>
      <item><title>Unapproved domain</title><link>https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fexample.com%2Fstory</link>
        <description>Must not be retained.</description></item>
    </channel></rss>'''
    response = Mock()
    response.raise_for_status = Mock()
    response.content = xml.encode()
    captured = {}

    def fake_get(url, *, params, timeout, headers):
        captured.update(url=url, params=params, timeout=timeout)
        return response

    monkeypatch.setattr(providers.httpx, 'get', fake_get)
    monkeypatch.setattr(providers, 'extract_article', lambda url: {
        'url': url,
        'title': 'Updated Mudryk status',
        'published_at': '2026-07-31',
        'text': 'The full publisher article says the appeal was filed earlier and resolved in July. ' * 20,
    })
    results = providers.BingSportsOutletProvider('skysports.com').search('Mykhailo Mudryk appeal')

    assert captured['url'] == 'https://www.bing.com/news/search'
    assert captured['params']['format'] == 'rss'
    assert 'site:skysports.com' in captured['params']['q']
    assert providers.BingSportsOutletProvider._search_query('Mykhailo Mudryk: Chelsea winger to appeal against four-year ban for doping offence') == 'mykhailo mudryk chelsea doping ban'
    assert captured['timeout'] == 8
    assert len(results) == 1
    assert results[0].url == 'https://www.skysports.com/football/news/mudryk-update'
    assert results[0].name == 'Sky Sports'
    assert results[0].published_at == '2026-07-31'
    assert 'full publisher article says' in results[0].excerpt
    assert results[0].relationship_type == 'contextual'


def test_selected_sports_search_is_opt_in(monkeypatch):
    settings = SimpleNamespace(google_factcheck_key=None, gdelt_enabled=False, newsapi_key=None, sports_source_search_enabled=True)
    monkeypatch.setattr(providers, 'get_settings', lambda: settings)

    selected = providers.enabled_external_providers()

    assert [p.domain for p in selected] == ['bbc.com', 'aljazeera.com', 'reuters.com', 'skysports.com']
    settings.sports_source_search_enabled = False
    assert providers.enabled_external_providers() == []


def test_gdelt_retains_source_link_and_bounded_article_text(monkeypatch):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        'articles': [
            {'url': 'https://news.example/story', 'title': 'A related headline', 'domain': 'news.example', 'seendate': '20261015120000'},
            {'url': 'https://news.example/headline-only', 'title': 'Another related headline', 'domain': 'news.example'},
        ]
    }
    request = Mock()
    request.raise_for_status = Mock()
    request.json.return_value = response.json.return_value
    calls = {}

    def fake_get(url, *, params, timeout, headers):
        calls.update(url=url, params=params, timeout=timeout, headers=headers)
        return request

    def fake_extract(url):
        if url.endswith('headline-only'):
            raise RuntimeError('publisher blocks article extraction')
        return {'title': 'A related headline', 'publisher': 'Example News', 'text': 'Article body with useful context. ' * 100, 'published_at': '2026-10-15'}

    providers._gdelt_cache.clear()
    providers._gdelt_last_request_at = 0.0
    monkeypatch.setattr(providers, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(providers, 'get_settings', lambda: SimpleNamespace(gdelt_enabled=True))
    monkeypatch.setattr(providers.httpx, 'get', fake_get)
    monkeypatch.setattr(providers, 'extract_article', fake_extract)

    results = providers.GDELTProvider().search('a fact-check claim')

    assert calls['params']['timespan'] == '7d'
    assert calls['params']['maxrecords'] == 3
    assert len(results) == 2
    assert results[0].url == 'https://news.example/story'
    assert results[0].name == 'A related headline'
    assert results[0].published_at == '2026-10-15T12:00:00Z'
    assert results[0].excerpt.startswith('Article body with useful context.')
    assert len(results[0].excerpt) <= 1201
    assert results[1].url == 'https://news.example/headline-only'
    assert results[1].excerpt == 'Another related headline'



def test_gdelt_caches_repeated_claim_searches(monkeypatch):
    providers._gdelt_cache.clear()
    providers._gdelt_last_request_at = 0.0
    monkeypatch.setattr(providers, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(providers, 'get_settings', lambda: SimpleNamespace(gdelt_enabled=True))
    response = Mock(status_code=200)
    response.raise_for_status = Mock()
    response.json.return_value = {'articles': [{'url': 'https://news.example/cached', 'title': 'Cached news'}]}
    calls = []
    def fake_get(url, *, params, timeout, headers):
        calls.append(params['query'])
        return response
    monkeypatch.setattr(providers.httpx, 'get', fake_get)
    monkeypatch.setattr(providers, 'extract_article', lambda _url: (_ for _ in ()).throw(RuntimeError('blocked')))

    provider = providers.GDELTProvider()
    first = provider.search('A repeated claim')
    second = provider.search('  a REPEATED   claim  ')

    assert len(first) == len(second) == 1
    assert calls == ['A repeated claim']


def test_gdelt_retries_once_after_rate_limit(monkeypatch):
    providers._gdelt_cache.clear()
    providers._gdelt_last_request_at = 0.0
    delays = []
    clock = [100.0]
    def advance(seconds):
        delays.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(providers, 'sleep', advance)
    monkeypatch.setattr(providers, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(providers, 'get_settings', lambda: SimpleNamespace(gdelt_enabled=True))
    limited = Mock(status_code=429, headers={}, text='Please limit requests to one every 5 seconds.')
    limited.raise_for_status = Mock()
    success = Mock(status_code=200)
    success.raise_for_status = Mock()
    success.json.return_value = {'articles': []}
    responses = iter([limited, success])
    calls = []
    def fake_get(url, *, params, timeout, headers):
        calls.append(url)
        return next(responses)
    monkeypatch.setattr(providers.httpx, 'get', fake_get)

    assert providers.GDELTProvider().search('a rate limited claim') == []
    assert len(calls) == 2
    assert delays == [5.25]

def test_provider_error_message_explains_rate_limit_without_leaking_request_url():
    request = httpx.Request('GET', 'https://api.example/search?apiKey=secret')
    response = httpx.Response(429, request=request)
    error = httpx.HTTPStatusError('rate limited', request=request, response=response)

    message = verification.provider_failure_message('GDELT', error)

    assert 'HTTP 429' in message
    assert 'rate-limited' in message
    assert 'secret' not in message
    assert 'apiKey' not in message


def test_structured_assessment_requires_and_returns_source_bounded_news_summary(monkeypatch):
    monkeypatch.setattr(structured.settings, 'openai_api_key', 'test-key')
    expected = {
        'verdict': 'Mostly Supported',
        'explanation': 'The retained article excerpt supports the central claim, with limits.',
        'news_summary': 'The retrieved article reports evidence relevant to the claim, but the report remains limited to this source.',
        'supporting_ids': ['evidence-1'],
        'contradicting_ids': [],
        'contextual_ids': [],
        'freshness_note': 'The article was recently indexed.',
    }
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {'choices': [{'message': {'content': json.dumps(expected)}}]}
    captured = {}

    def fake_post(url, *, json, headers, timeout):
        captured.update(url=url, payload=json, headers=headers, timeout=timeout)
        return response

    monkeypatch.setattr(structured.httpx, 'post', fake_post)
    assessment = structured.analyze_evidence('A factual claim', [{'id': 'evidence-1', 'excerpt': 'An article excerpt.'}])

    assert assessment is not None
    assert assessment.news_summary == expected['news_summary']
    schema = captured['payload']['response_format']['json_schema']['schema']
    assert 'news_summary' in schema['required']
    assert 'news_summary' in schema['properties']
    assert '2-5 sentences' in captured['payload']['messages'][0]['content']
    assert 'rating applies only to the Reviewed claim' in captured['payload']['messages'][0]['content']
    assert 'opposite' in captured['payload']['messages'][0]['content']
    assert 'distinguish a historical event from its later outcome or current status' in captured['payload']['messages'][0]['content']


def test_structured_model_rate_limit_has_safe_diagnostic(monkeypatch):
    monkeypatch.setattr(structured.settings, 'openai_api_key', 'test-key')
    request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
    response = httpx.Response(429, request=request)
    response_error = httpx.HTTPStatusError('rate limited', request=request, response=response)
    mocked_response = Mock()
    mocked_response.raise_for_status.side_effect = response_error
    monkeypatch.setattr(structured.httpx, 'post', lambda *args, **kwargs: mocked_response)

    try:
        structured.analyze_evidence('A factual claim', [{'id': 'evidence-1', 'excerpt': 'An article excerpt.'}])
    except structured.EvidenceAnalysisError as exc:
        message = str(exc)
    else:
        raise AssertionError('Expected a safe model-provider error')

    assert 'HTTP 429' in message
    assert 'quota' in message
    assert 'test-key' not in message


def test_analysis_provider_label_identifies_groq(monkeypatch):
    monkeypatch.setattr(verification.settings, 'openai_base_url', 'https://api.groq.com/openai/v1')

    assert verification.analysis_provider_name() == 'Groq structured evidence analysis'


def test_gdelt_seendate_is_normalized_for_frontend():
    assert providers.GDELTProvider._normalize_seendate('20261015T120000Z') == '2026-10-15T12:00:00Z'
    assert providers.GDELTProvider._normalize_seendate('20261015120000') == '2026-10-15T12:00:00Z'
    assert providers.GDELTProvider._normalize_seendate(None) is None
