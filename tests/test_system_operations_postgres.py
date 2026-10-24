"""Non-billable API/worker runtime inspection against an isolated migrated PostgreSQL schema."""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from test_migrations import migration_database  # noqa: F401

from alembic import command
from shiftos.core.config import Settings
from shiftos.db.session import create_database
from shiftos.services.runtime import runtime_report


@pytest.mark.integration
def test_api_and_worker_preflight_share_real_database_and_schema(migration_database):  # noqa: F811
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    schema = connection.scalar(text("SELECT current_schema()"))
    connection.commit()
    url = make_url(os.environ["TEST_DATABASE_URL"]).set(drivername="postgresql+psycopg")
    isolated_url = url.update_query_dict({"options": f"-csearch_path={schema}"})
    settings = Settings(
        _env_file=None,
        app_env="test",
        analysis_model_provider="replit_claude",
        database_url=isolated_url.render_as_string(hide_password=False),
    )
    database = create_database(settings.database_url.get_secret_value())
    try:
        api = runtime_report(settings, database=database, check_database=True, component="api")
        worker = runtime_report(
            settings, database=database, check_database=True, component="worker"
        )
        assert api["status"] == worker["status"] == "configuration_checked"
        assert api["schema"]["status"] == worker["schema"]["status"] == "current"
        assert (
            api["database_configuration_fingerprint"]
            == worker["database_configuration_fingerprint"]
        )
        assert api["migrations_executed"] == worker["provider_requests"] == 0
        assert api["deployment_ready"] is False
        assert api["checks"]["external_processing_disabled"]
        assert api["checks"]["research_disabled"]
        assert api["checks"]["gemini_disabled"]
    finally:
        database.engine.dispose()
