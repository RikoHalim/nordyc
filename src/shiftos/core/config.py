from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr("postgresql+psycopg://shiftos@localhost:5432/shiftos")
    discovery_enabled: bool = False
    discovery_terms_reviewed: bool = False
    catalogue_write_token: SecretStr | None = None
    curriculum_upload_dir: Path = Path("data/private/curriculum_uploads")
    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="", max_length=100)
    gemini_enabled: bool = False
    brave_search_api_key: SecretStr | None = None
    research_enabled: bool = False
    analysis_write_token: SecretStr | None = None
    analysis_external_processing_allowed: bool = False
    analysis_research_policy: Path = Path("data/research_policy.json")
    analysis_permissions_path: Path = Path("data/analysis_permissions.json")
    analysis_max_courses: int = Field(default=1000, ge=1, le=1000)
    research_max_queries: int = Field(default=10, ge=1, le=10)
    research_timeout_seconds: int = Field(default=180, ge=1, le=180)
    analysis_provider_timeout_seconds: int = Field(default=20, ge=1, le=60)
    analysis_provider_max_attempts: int = Field(default=3, ge=1, le=3)

    @field_validator("gemini_model")
    @classmethod
    def validate_gemini_model(cls, value: str) -> str:
        import re

        value = value.strip()
        if value and not re.fullmatch(r"gemini-[a-z0-9][a-z0-9.\-]{0,90}", value):
            raise ValueError("GEMINI_MODEL must be a Gemini model code, without a URL or path")
        return value

    @field_validator(
        "catalogue_write_token", "analysis_write_token", "gemini_api_key", "brave_search_api_key"
    )
    @classmethod
    def validate_catalogue_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().strip():
            raise ValueError("Configured credentials must be nonempty")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except Exception:
            raise ValueError("DATABASE_URL must be a valid database URL") from None
        allowed = {"postgresql+psycopg"}
        if info.data.get("app_env") == "test":
            allowed.add("sqlite+pysqlite")
        if url.drivername not in allowed:
            raise ValueError("Use PostgreSQL with psycopg; SQLite is allowed only in test mode")
        return value
