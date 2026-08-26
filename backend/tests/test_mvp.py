import os
os.environ['VERIFACT_DATABASE_URL'] = 'sqlite:///./test_verifact.db'
os.environ['VERIFACT_MODE'] = 'local-fixture'
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

client = TestClient(app)

def setup_module():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)

def auth_client(email='verifier@example.com'):
    response = client.post('/api/v1/auth/register', json={'full_name': 'VeriFact Tester', 'email': email, 'password': 'StrongPass2026', 'confirm_password': 'StrongPass2026'})
    assert response.status_code == 201
    return client

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
