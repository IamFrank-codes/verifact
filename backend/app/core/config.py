from functools import lru_cache
from typing import Literal
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'VeriFact'
    environment: Literal['development', 'test', 'production'] = 'development'
    mode: Literal['local-fixture', 'hybrid', 'production'] = 'local-fixture'
    database_url: str = 'sqlite:///./verifact.db'
    redis_url: str | None = None
    secret_key: str = 'change-this-for-production'
    access_token_minutes: int = 60
    frontend_origin: str = 'http://localhost:5173'
    additional_cors_origins: str = ''
    public_base_url: str = 'http://localhost:5173'
    allowed_hosts: str = 'localhost,127.0.0.1,testserver,verifact-api'
    secure_cookies: bool = False
    score_coverage_threshold: float = 0.60
    max_input_chars: int = 24000
    max_request_bytes: int = 300_000
    request_timeout_seconds: int = 45
    rate_limit_default: str = '120/minute'
    rate_limit_auth: str = '10/minute'
    rate_limit_signup: str = '5/minute'
    google_factcheck_key: str | None = None
    newsapi_key: str | None = None
    gdelt_enabled: bool = False
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = 'gpt-4o-mini'
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = 'VeriFact'
    smtp_starttls: bool = True
    source_policy_path: str = 'app/fixtures/source_policy.json'
    model_config = SettingsConfigDict(env_file='.env', env_prefix='VERIFACT_', case_sensitive=False)

    @field_validator('score_coverage_threshold')
    @classmethod
    def validate_threshold(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError('VERIFACT_SCORE_COVERAGE_THRESHOLD must be between 0 and 1.')
        return value

    @property
    def cors_origins(self) -> list[str]:
        values = [self.frontend_origin, *self.additional_cors_origins.split(',')]
        return [value.strip().rstrip('/') for value in values if value.strip()]

    @property
    def host_list(self) -> list[str]:
        return [value.strip() for value in self.allowed_hosts.split(',') if value.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_email)

    @property
    def is_production(self) -> bool:
        return self.environment == 'production' or self.mode == 'production'

    @model_validator(mode='after')
    def validate_production(self):
        if self.is_production:
            if self.mode != 'production':
                raise ValueError('Production environment requires VERIFACT_MODE=production.')
            if self.secret_key in {'', 'change-this-for-production', 'replace-with-a-long-random-value-in-production'} or len(self.secret_key) < 32:
                raise ValueError('Production requires a unique VERIFACT_SECRET_KEY of at least 32 characters.')
            if not self.secure_cookies:
                raise ValueError('Production requires VERIFACT_SECURE_COOKIES=true.')
            if not self.frontend_origin.startswith('https://') or not self.public_base_url.startswith('https://'):
                raise ValueError('Production requires HTTPS VERIFACT_FRONTEND_ORIGIN and VERIFACT_PUBLIC_BASE_URL.')
            if not self.database_url.startswith('postgresql'):
                raise ValueError('Production requires a PostgreSQL VERIFACT_DATABASE_URL.')
            if not self.redis_url:
                raise ValueError('Production requires VERIFACT_REDIS_URL.')
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
