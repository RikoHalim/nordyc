"""Static SQL verification complements the real PostgreSQL migration regressions."""

from io import StringIO
from pathlib import Path

from alembic.config import Config

from alembic import command


def test_career_migration_compiles_postgresql_constraints_and_history_guards(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/shiftos_offline_sql")
    buffer = StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=buffer)
    command.upgrade(config, "head", sql=True)
    sql = buffer.getvalue()
    assert "CREATE TABLE career_runs" in sql
    assert "CREATE TABLE career_recommendations" in sql
    assert "CREATE TABLE career_reviews" in sql
    assert "FOREIGN KEY(run_id, programme_revision_id) REFERENCES career_runs" in sql
    assert (
        "FOREIGN KEY(recommendation_id, run_id, programme_revision_id, recommendation_version)"
        in sql
    )
    assert "CREATE TRIGGER career_reviews_append_only BEFORE UPDATE OR DELETE" in sql
    assert "CREATE TRIGGER career_runs_immutable BEFORE UPDATE OR DELETE" in sql
    assert "actor = 'authenticated_analysis_operator'" in sql


def test_career_offline_downgrade_refuses_populated_history(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/shiftos_offline_sql")
    buffer = StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=buffer)
    command.downgrade(config, "0006_career_alignment:0005_programme_analysis", sql=True)
    sql = buffer.getvalue()
    assert "Export Phase 5 career runs and reviews before downgrade; refusing data loss" in sql
    assert "count(*) FROM career_reviews" in sql
    assert "DROP TABLE career_reviews" in sql
    assert "DROP FUNCTION shiftos_career_append_only()" in sql
