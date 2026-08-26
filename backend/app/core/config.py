from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'VeriFact'
    environment: str = 'development'
    mode: str = 'local-fixture'
    database_url: str = 'sqlite:///./verifact.db'
    secret_key: str = 'change-this-for-production'
    access_token_minutes: int = 60
    frontend_origin: str = 'http://localhost:5173'
    public_base_url: str = 'http://localhost:5173'
    secure_cookies: bool = False
    score_coverage_threshold: float = 0.60
    max_input_chars: int = 24000
    google_factcheck_key: str | None = None
    newsapi_key: str | None = None
    gdelt_enabled: bool = False
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = 'gpt-4o-mini'
    source_policy_path: str = 'app/fixtures/source_policy.json'
    model_config = SettingsConfigDict(env_file='.env', env_prefix='VERIFACT_', case_sensitive=False)

@lru_cache
def get_settings() -> Settings:
    return Settings()
