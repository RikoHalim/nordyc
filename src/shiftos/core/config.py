import ipaddress
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


def normalize_replit_anthropic_base_url(value: str) -> str:
    """Validate an operator-provisioned bridge, never a request-supplied source URL."""
    value = value.strip()
    try:
        parsed = urlsplit(value)
        host = parsed.hostname.rstrip(".") if parsed.hostname else None
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError("Configure a valid Replit-managed Anthropic base URL") from None
    if (
        not host
        or parsed.scheme not in {"http", "https"}
        or parsed.username is not None
        or parsed.password is not None
        or "?" in value
        or "#" in value
        or "\\" in value
        or any(character.isspace() or ord(character) < 32 for character in value)
        or "%" in parsed.path
        or "//" in parsed.path
        or any(part in {".", ".."} for part in parsed.path.split("/"))
        or host == "anthropic.com"
        or host.endswith(".anthropic.com")
        or (port is not None and port < 1)
    ):
        raise ValueError("Configure a valid Replit-managed Anthropic base URL")
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = host == "localhost"
    if parsed.scheme == "http" and not loopback:
        raise ValueError("Replit bridge HTTP is allowed only on loopback")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
        populate_by_name=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    api_access_mode: Literal["legacy", "scoped"] = "legacy"
    api_access_policy_path: Path | None = None
    database_url: SecretStr = SecretStr("postgresql+psycopg://shiftos@localhost:5432/shiftos")
    discovery_enabled: bool = False
    discovery_terms_reviewed: bool = False
    catalogue_write_token: SecretStr | None = None
    curriculum_upload_dir: Path = Path("data/private/curriculum_uploads")
    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="", max_length=100)
    gemini_enabled: bool = False
    analysis_model_provider: Literal["gemini", "replit_claude"] = "gemini"
    analysis_gemini_fallback_enabled: bool = False
    claude_enabled: bool = False
    claude_model: str = Field(default="claude-opus-5", max_length=100)
    claude_max_output_tokens: int = Field(default=16384, ge=1, le=16384)
    replit_anthropic_api_key: SecretStr | None = Field(
        default=None, validation_alias="AI_INTEGRATIONS_ANTHROPIC_API_KEY"
    )
    replit_anthropic_base_url: str | None = Field(
        default=None, validation_alias="AI_INTEGRATIONS_ANTHROPIC_BASE_URL", repr=False
    )
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
    analysis_validation_max_attempts: int = Field(default=2, ge=1, le=2)
    analysis_provider_max_request_bytes: int = Field(default=1_000_000, ge=1024, le=1_000_000)

    @field_validator("gemini_model")
    @classmethod
    def validate_gemini_model(cls, value: str) -> str:
        value = value.strip()
        if value and not re.fullmatch(r"gemini-[a-z0-9][a-z0-9.\-]{0,90}", value):
            raise ValueError("GEMINI_MODEL must be a Gemini model code, without a URL or path")
        return value

    @field_validator("claude_model")
    @classmethod
    def validate_claude_model(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"claude-[a-z0-9][a-z0-9.\-]{0,90}", value):
            raise ValueError("CLAUDE_MODEL must be a Claude model code, without a URL or path")
        return value

    @field_validator("replit_anthropic_base_url")
    @classmethod
    def validate_replit_base_url(cls, value: str | None) -> str | None:
        return normalize_replit_anthropic_base_url(value) if value is not None else None

    @field_validator(
        "catalogue_write_token",
        "analysis_write_token",
        "gemini_api_key",
        "brave_search_api_key",
        "replit_anthropic_api_key",
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
        # Managed PostgreSQL services commonly supply the standard URI scheme.
        # Keep SQLAlchemy on the existing synchronous psycopg3 driver explicitly.
        if url.drivername in {"postgresql", "postgres"}:
            url = url.set(drivername="postgresql+psycopg")
            value = SecretStr(url.render_as_string(hide_password=False))
        allowed = {"postgresql+psycopg"}
        if info.data.get("app_env") == "test":
            allowed.add("sqlite+pysqlite")
        if url.drivername not in allowed:
            raise ValueError("Use PostgreSQL with psycopg; SQLite is allowed only in test mode")
        return value
