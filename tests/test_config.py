from pathlib import Path

import pytest
from pydantic import ValidationError

from shiftos.core.config import Settings


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("APP_ENV", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


def test_settings_accept_configured_postgresql_and_hide_password() -> None:
    database_url = "postgresql+psycopg://synthetic:disposable-test-password@localhost/shiftos_test"
    settings = Settings(_env_file=None, app_env="production", database_url=database_url)
    assert settings.database_url.get_secret_value() == database_url
    assert settings.app_env == "production"
    assert "disposable-test-password" not in repr(settings)
    assert "disposable-test-password" not in str(settings)
    assert "disposable-test-password" not in settings.model_dump_json()


@pytest.mark.parametrize("app_env", ["development", "production"])
def test_sqlite_is_rejected_outside_test_mode(app_env: str) -> None:
    with pytest.raises(ValidationError, match="SQLite is allowed only in test mode"):
        Settings(_env_file=None, app_env=app_env, database_url="sqlite+pysqlite:///:memory:")


def test_explicit_test_mode_accepts_sqlite() -> None:
    settings = Settings(_env_file=None, app_env="test", database_url="sqlite+pysqlite:///:memory:")
    assert settings.database_url.get_secret_value() == "sqlite+pysqlite:///:memory:"


@pytest.mark.parametrize(
    "database_url",
    [
        "mysql+pymysql://synthetic:disposable-test-password@localhost/shiftos_test",
        "postgresql+psycopg2://synthetic:disposable-test-password@localhost/shiftos_test",
        "postgresql+asyncpg://synthetic:disposable-test-password@localhost/shiftos_test",
        "postgresql://synthetic:disposable-test-password@localhost/shiftos_test",
    ],
)
def test_unsupported_drivers_fail_without_exposing_credentials(database_url: str) -> None:
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, app_env="test", database_url=database_url)
    assert "Use PostgreSQL with psycopg" in str(error.value)
    assert "disposable-test-password" not in str(error.value)
    assert "disposable-test-password" not in repr(error.value)


def test_malformed_database_url_error_redacts_input() -> None:
    database_url = "postgresql+psycopg://synthetic:disposable-test-password@localhost:invalid/db"
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url=database_url)
    assert "DATABASE_URL must be a valid database URL" in str(error.value)
    assert "disposable-test-password" not in str(error.value)
    assert "disposable-test-password" not in repr(error.value)


def test_settings_load_dotenv_and_environment_takes_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=test\nDATABASE_URL=sqlite+pysqlite:///:memory:\n", encoding="utf-8"
    )
    settings = Settings(_env_file=env_file)
    assert settings.app_env == "test"
    assert settings.database_url.get_secret_value() == "sqlite+pysqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://synthetic@localhost/shiftos_test")
    assert (
        Settings(_env_file=env_file).database_url.get_secret_value()
        == "postgresql+psycopg://synthetic@localhost/shiftos_test"
    )


def test_phase_one_settings_need_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://")
