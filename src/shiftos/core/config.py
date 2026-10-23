from typing import Literal

from pydantic import SecretStr, ValidationInfo, field_validator
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

    @field_validator("catalogue_write_token")
    @classmethod
    def validate_catalogue_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().strip():
            raise ValueError("CATALOGUE_WRITE_TOKEN must be nonempty when configured")
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
