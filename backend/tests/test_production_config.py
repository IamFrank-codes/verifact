import pytest
from pydantic import ValidationError
from app.core.config import Settings


def production_kwargs(**overrides):
    values = {
        'environment': 'production',
        'mode': 'production',
        'database_url': 'postgresql+psycopg://verifact:password@db:5432/verifact',
        'redis_url': 'redis://:password@redis:6379/0',
        'secret_key': 'a-production-secret-that-is-longer-than-thirty-two-characters',
        'frontend_origin': 'https://verifact.example',
        'public_base_url': 'https://verifact.example',
        'allowed_hosts': 'verifact.example',
        'secure_cookies': True,
    }
    values.update(overrides)
    return values


def test_production_requires_secure_configuration():
    with pytest.raises(ValidationError):
        Settings(**production_kwargs(secret_key='change-this-for-production'))
    with pytest.raises(ValidationError):
        Settings(**production_kwargs(secure_cookies=False))
    with pytest.raises(ValidationError):
        Settings(**production_kwargs(database_url='sqlite:///./verifact.db'))


def test_valid_production_configuration_is_accepted():
    settings = Settings(**production_kwargs())
    assert settings.is_production is True
    assert settings.cors_origins == ['https://verifact.example']


def test_development_settings_allow_docker_api_hostname():
    settings = Settings(environment='development', mode='local-fixture')
    assert 'verifact-api' in settings.host_list


def test_hybrid_mode_defaults_to_mock_and_requires_explicit_real_api_switch():
    mock_settings = Settings(environment='development', mode='hybrid')
    real_settings = Settings(environment='development', mode='hybrid', local_real_api_mode=True)
    assert mock_settings.live_provider_mode is False
    assert real_settings.live_provider_mode is True
