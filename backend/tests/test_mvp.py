import os
os.environ['VERIFACT_DATABASE_URL'] = 'sqlite:///./test_verifact.db'
os.environ['VERIFACT_MODE'] = 'local-fixture'
from fastapi.testclient import TestClient
from app.main import app
import app.main as main_module
from app.ai.structured import EvidenceAssessment
from app.evidence.providers import BingSportsOutletProvider, EvidenceItem
from app.services import email as email_service
from app.services import verification as verification_service
from app.db import Base, engine

client = TestClient(app)

def setup_module():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)

def auth_client(email='verifier@example.com'):
    main_module.limiter._storage.reset()
    response = client.post('/api/v1/auth/register', json={'full_name': 'VeriFact Tester', 'email': email, 'password': 'StrongPass2026', 'confirm_password': 'StrongPass2026'})
    assert response.status_code == 201
    return client

def test_signup_auto_login_survives_verification_email_failure(monkeypatch):
    main_module.limiter._storage.reset()
    monkeypatch.setattr(main_module.settings, 'mode', 'academic-demo')
    def fail_email(_email, _token):
        raise RuntimeError('SMTP unavailable')
    monkeypatch.setattr(main_module, 'send_email_verification_email', fail_email)
    response = client.post('/api/v1/auth/register', json={
        'full_name': 'Signup Auto Login',
        'email': 'signup-auto-login@example.com',
        'password': 'StrongPass2026',
        'confirm_password': 'StrongPass2026',
    })
    assert response.status_code == 201
    assert response.json()['verification_email_sent'] is False
    assert 'access_token' in response.cookies
    assert client.get('/api/v1/auth/me').json()['user']['email'] == 'signup-auto-login@example.com'
    monkeypatch.setattr(main_module.settings, 'mode', 'local-fixture')

def test_scored_fixture_report():
    auth_client()
    created = client.post('/api/v1/verifications', json={'input_type': 'claim', 'content': 'COVID vaccines reduce hospitalization.'})
    assert created.status_code == 202
    report = client.post(f"/api/v1/verifications/{created.json()['id']}/run-fixture")
    body = report.json()
    assert body['status'] == 'completed'
    assert body['score'] is not None
    assert body['evidence_status'] == 'Scored — evidence coverage sufficient'
    assert body['claims'][0]['evidence'][0]['source']['quality_class'] == 'High'

def test_insufficient_evidence_is_scoreless():
    created = client.post('/api/v1/verifications', json={'input_type': 'claim', 'content': 'Diamonds are being mined on Neptune.'})
    report = client.post(f"/api/v1/verifications/{created.json()['id']}/run-fixture")
    body = report.json()
    assert body['score'] is None
    assert body['evidence_status'] == 'Insufficient evidence — no overall score'
    assert body['score_details']['eligible'] is False

def test_private_then_public_report():
    created = client.post('/api/v1/verifications', json={'input_type': 'claim', 'content': 'Vitamin C cures COVID-19.'})
    report = client.post(f"/api/v1/verifications/{created.json()['id']}/run-fixture")
    shared = client.post(f"/api/v1/verifications/{report.json()['id']}/share", json={'is_public': True})
    public = client.get(f"/api/v1/reports/{shared.json()['public_id']}")
    assert public.status_code == 200
    assert 'email' not in public.text

def test_password_reset_then_login():
    reset_email = 'reset@example.com'
    response = client.post('/api/v1/auth/register', json={'full_name': 'Reset Tester', 'email': reset_email, 'password': 'StrongPass2026', 'confirm_password': 'StrongPass2026'})
    assert response.status_code == 201
    client.post('/api/v1/auth/logout')
    requested = client.post('/api/v1/auth/forgot-password', json={'email': reset_email})
    assert requested.status_code == 200
    token = requested.json()['development_reset_token']
    reset = client.post('/api/v1/auth/reset-password', json={'token': token, 'password': 'RenewedPass2026', 'confirm_password': 'RenewedPass2026'})
    assert reset.status_code == 200
    login = client.post('/api/v1/auth/login', json={'email': reset_email, 'password': 'RenewedPass2026'})
    assert login.status_code == 200

def test_forgot_password_sends_email_and_reset_token_is_single_use(monkeypatch):
    email = 'email-reset@example.com'
    auth_client(email)
    sent = []
    monkeypatch.setattr(main_module.settings, 'mode', 'production')
    monkeypatch.setattr(main_module, 'send_password_reset_email', lambda recipient, token: sent.append((recipient, token)))

    requested = client.post('/api/v1/auth/forgot-password', json={'email': email})
    assert requested.status_code == 200
    assert requested.json()['message'] == 'If an account exists for that email, VeriFact has sent reset instructions.'
    assert 'development_reset_token' not in requested.json()
    assert len(sent) == 1
    assert sent[0][0] == email

    token = sent[0][1]
    reset = client.post('/api/v1/auth/reset-password', json={'token': token, 'password': 'ChangedPass2026', 'confirm_password': 'ChangedPass2026'})
    assert reset.status_code == 200
    login = client.post('/api/v1/auth/login', json={'email': email, 'password': 'ChangedPass2026'})
    assert login.status_code == 200
    reused = client.post('/api/v1/auth/reset-password', json={'token': token, 'password': 'AnotherPass2026', 'confirm_password': 'AnotherPass2026'})
    assert reused.status_code == 400

def test_reset_email_contains_link_and_manual_code(monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, '_send_email', lambda recipient, subject, body: sent.append((recipient, subject, body)))
    email_service.send_password_reset_email('person@example.com', 'one-time-reset-code')
    recipient, subject, body = sent[0]
    assert recipient == 'person@example.com'
    assert subject == 'Reset your VeriFact password'
    assert '/reset?token=one-time-reset-code' in body
    assert 'one-time-reset-code' in body


def test_live_verification_explains_when_no_sources_are_found(monkeypatch):
    auth_client('no-source@example.com')
    for settings in (main_module.settings, verification_service.settings):
        monkeypatch.setattr(settings, 'mode', 'academic-demo')
        monkeypatch.setattr(settings, 'inline_processing', True)

    class EmptyProvider:
        name = 'Test news provider'

        def search(self, claim):
            return []

    monkeypatch.setattr(verification_service, 'enabled_external_providers', lambda: [EmptyProvider()])
    monkeypatch.setattr(verification_service, 'is_enabled', lambda: True)
    monkeypatch.setattr(verification_service, 'analyze_evidence', lambda *args: (_ for _ in ()).throw(AssertionError('Analysis must be skipped when no evidence exists.')))

    response = client.post('/api/v1/verifications', json={'input_type': 'claim', 'content': 'A claim with no matching source records.'})
    assert response.status_code == 202
    report = response.json()['report']
    assert report['claims'][0]['evidence'] == []
    assert report['summary'].startswith('Related news summary unavailable: no source records were retrieved.')
    analysis_run = next(item for item in report['provider_runs'] if item['provider'] == 'OpenAI-compatible evidence analysis')
    assert analysis_run['status'] == 'unavailable'
    assert analysis_run['message'] == 'No source evidence was retrieved; analysis and news summary were skipped.'


def test_live_report_includes_retained_source_and_model_news_summary(monkeypatch):
    auth_client('news-summary@example.com')
    for settings in (main_module.settings, verification_service.settings):
        monkeypatch.setattr(settings, 'mode', 'academic-demo')
        monkeypatch.setattr(settings, 'inline_processing', True)

    class OneSourceProvider:
        name = 'Test news provider'

        def search(self, claim):
            return [EvidenceItem('Example News: article title', 'https://news.example/article', '2026-10-15', 'Article excerpt with directly relevant reporting.', 'contextual', 'Test source match.', self.name)]

    assessment = EvidenceAssessment(
        verdict='Insufficient Evidence',
        explanation='This single source is not enough to assess the claim.',
        news_summary='The retrieved source reports relevant context but does not establish the claim on its own.',
        supporting_ids=[],
        contradicting_ids=[],
        contextual_ids=[],
        freshness_note='The source was published recently.',
    )
    monkeypatch.setattr(verification_service, 'enabled_external_providers', lambda: [OneSourceProvider()])
    monkeypatch.setattr(verification_service, 'is_enabled', lambda: True)
    monkeypatch.setattr(verification_service, 'analyze_evidence', lambda *args: assessment)

    response = client.post('/api/v1/verifications', json={'input_type': 'claim', 'content': 'A claim supported by one related article.'})
    assert response.status_code == 202
    report = response.json()['report']
    assert report['summary'].startswith('Related news summary:\nThe retrieved source reports relevant context')
    assert report['claims'][0]['evidence'][0]['source']['url'] == 'https://news.example/article'
    assert report['claims'][0]['evidence'][0]['excerpt'] == 'Article excerpt with directly relevant reporting.'


def test_bing_sports_searches_are_one_aggregate_retrieval_record(monkeypatch):
    auth_client('bing-aggregate@example.com')
    for settings in (main_module.settings, verification_service.settings):
        monkeypatch.setattr(settings, 'mode', 'academic-demo')
        monkeypatch.setattr(settings, 'inline_processing', True)

    outlets = [BingSportsOutletProvider(domain) for domain in BingSportsOutletProvider.outlets]

    def fake_search(query, provider):
        if provider.domain == 'aljazeera.com':
            raise RuntimeError('outlet unavailable')
        if provider.domain == 'bbc.com':
            return [EvidenceItem('BBC Sport', 'https://www.bbc.com/sport/football/claim', '2026-10-18', 'BBC reports on the event.', 'contextual', 'Direct sports coverage.', provider.retrieval_name)]
        if provider.domain == 'reuters.com':
            return [EvidenceItem('Reuters Sports', 'https://www.reuters.com/sports/claim', '2026-10-19', 'Reuters reports on the event.', 'contextual', 'Direct sports coverage.', provider.retrieval_name)]
        return []

    for provider in outlets:
        monkeypatch.setattr(provider, 'search', lambda query, p=provider: fake_search(query, p))
    monkeypatch.setattr(verification_service, 'enabled_external_providers', lambda: outlets)
    monkeypatch.setattr(verification_service, 'is_enabled', lambda: True)
    monkeypatch.setattr(verification_service, 'analyze_evidence', lambda _text, packet: EvidenceAssessment(
        verdict='Mostly Supported',
        explanation='The retained sports articles support the test claim.',
        news_summary='Two selected sports publishers report on the event.',
        supporting_ids=[item['id'] for item in packet],
        contradicting_ids=[],
        contextual_ids=[],
        freshness_note='The records are recent.',
    ))

    response = client.post('/api/v1/verifications', json={'input_type': 'claim', 'content': 'A sports result covered by multiple publishers.'})
    assert response.status_code == 202
    report = response.json()['report']
    bing_runs = [item for item in report['provider_runs'] if item['provider'] == 'Bing News RSS']
    assert len(bing_runs) == 1
    assert bing_runs[0]['status'] == 'partial'
    assert bing_runs[0]['message'] == 'Searched 4 selected sports outlets; 2 record(s) returned. 1 outlet search(es) unavailable.'
    assert {item['source']['name'] for item in report['claims'][0]['evidence']} == {'BBC Sport', 'Reuters Sports'}
    assert {item['provider'] for item in report['claims'][0]['evidence']} == {'Bing News RSS'}


def test_url_submission_searches_with_extracted_article_title(monkeypatch):
    main_module.limiter._storage.reset()
    auth_client('url-search@example.com')
    for settings in (main_module.settings, verification_service.settings):
        monkeypatch.setattr(settings, 'mode', 'local-fixture')
        monkeypatch.setattr(settings, 'inline_processing', True)
    extracted = {
        'url': 'https://news.example/housing-plan',
        'title': 'City council approves a new affordable housing plan',
        'author': 'Staff Reporter',
        'publisher': 'Example News',
        'published_at': '2026-10-17',
        'text': ('The city council approved a new affordable housing plan on Tuesday. ' * 20),
    }
    monkeypatch.setattr(verification_service, 'extract_article', lambda _url: extracted)
    searched = []
    class TestNewsProvider:
        name = 'Test news provider'
        def search(self, query):
            searched.append(query)
            return [EvidenceItem('Example News', 'https://sources.example/housing-plan', '2026-10-17', 'The council approved the housing plan by a majority vote.', 'contextual', 'The report covers the same plan as the submitted article.', self.name)]
    monkeypatch.setattr(verification_service, 'enabled_external_providers', lambda: [TestNewsProvider()])
    monkeypatch.setattr(verification_service, 'is_enabled', lambda: True)
    def fake_assessment(claim_text, packet):
        assert len(claim_text) > 240
        return EvidenceAssessment(
            verdict='Mostly Supported',
            explanation='The retained record supports the central reported event.',
            news_summary='The retrieved source reports a vote on the plan.',
            supporting_ids=[packet[0]['id']],
            contradicting_ids=[],
            contextual_ids=[],
            freshness_note='The source is recent.',
        )
    monkeypatch.setattr(verification_service, 'analyze_evidence', fake_assessment)

    created = client.post('/api/v1/verifications', json={'input_type': 'url', 'content': 'https://news.example/housing-plan'})
    assert created.status_code == 202
    report_response = client.post(f"/api/v1/verifications/{created.json()['id']}/run-fixture")
    assert report_response.status_code == 200
    report = report_response.json()
    assert searched == ['City council approves a new affordable housing plan']
    assert report['article']['title'] == extracted['title']
    assert report['claims'][0]['evidence'][0]['provider'] == 'Test news provider'
    assert report['claims'][0]['evidence'][0]['relationship_type'] == 'supporting'
    assert report['provider_runs'][0]['message'] == '1 record(s) returned for the article search.'
