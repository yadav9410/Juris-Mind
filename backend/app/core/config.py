"""Central place for application settings.

Settings are read from environment variables or a local .env file.
This keeps passwords and API keys out of the Python source code.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings with safe development defaults."""

    app_name: str = "JurisMind API"
    app_env: str = "development"
    debug: bool = False
    # Migration/admin connection. Alembic uses this setting.
    database_url: str = "sqlite:///./jurismind_dev.db"
    # Runtime API connection. Must use the restricted jurismind_app role on PostgreSQL.
    app_database_url: str | None = None
    # Ingestion worker connection. Must use jurismind_ingest on PostgreSQL.
    ingestion_database_url: str | None = None
    ingestion_storage_dir: str = "./var/ingestion"
    ocr_enabled: bool = True
    ocr_languages: str = "eng"
    ocr_min_text_chars: int = 80

    # Supabase Auth project URL used for JWT issuer and JWKS validation.
    supabase_url: str | None = None
    # Supabase Auth verifies asymmetric signing keys through its JWKS endpoint.
    supabase_jwt_secret: str | None = None  # Reserved for legacy projects; not used by this verifier.
    # OpenAI provider settings. API key is read only from OPENAI_API_KEY.
    openai_api_key: str | None = None
    openai_enabled: bool = False
    openai_model: str = "gpt-4.1-mini"
    openai_max_output_tokens: int = 1800
    openai_timeout_seconds: int = 60
    openai_base_url: str = "https://api.openai.com/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse them throughout the application."""
    return Settings()
