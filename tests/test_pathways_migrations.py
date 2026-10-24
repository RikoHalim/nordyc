"""Offline PostgreSQL SQL checks supplement the real plan migration tests."""

from io import StringIO
from pathlib import Path

from alembic.config import Config

from alembic import command


def _config(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/shiftos_offline_sql")
    buffer = StringIO()
    return Config(
        str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=buffer
    ), buffer


def test_action_plan_sql_binds_parent_recommendation_and_review_versions(monkeypatch):
    config, buffer = _config(monkeypatch)
    command.upgrade(config, "head", sql=True)
    sql = buffer.getvalue()
    for table in ("action_plan_runs", "plan_recommendations", "action_plan_reviews"):
        assert f"CREATE TABLE {table}" in sql
    assert "FOREIGN KEY(career_run_id, programme_revision_id) REFERENCES career_runs" in sql
    assert (
        "FOREIGN KEY(recommendation_id, career_run_id, programme_revision_id, "
        "recommendation_version) REFERENCES career_recommendations" in sql
    )
    assert (
        "FOREIGN KEY(plan_run_id, programme_revision_id, plan_fingerprint) "
        "REFERENCES action_plan_runs" in sql
    )
    assert "CREATE TRIGGER action_plan_reviews_append_only BEFORE UPDATE OR DELETE" in sql
    assert "CREATE TRIGGER action_plan_runs_immutable BEFORE UPDATE OR DELETE" in sql
    assert "CONSTRAINT uq_action_plan_runs_id_revision_fingerprint UNIQUE" in sql
    assert "CONSTRAINT uq_action_plan_runs_id_career_revision UNIQUE" in sql


def test_action_plan_offline_downgrade_refuses_populated_history(monkeypatch):
    config, buffer = _config(monkeypatch)
    command.downgrade(config, "0007_academic_action_plans:0006_career_alignment", sql=True)
    sql = buffer.getvalue()
    assert "Export Phase 6 action plans and reviews before downgrade; refusing data loss" in sql
    assert "count(*) FROM plan_recommendations" in sql
    assert "DROP TABLE action_plan_reviews" in sql
    assert "DROP FUNCTION shiftos_plan_immutable()" in sql
