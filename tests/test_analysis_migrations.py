from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from test_migrations import _assert_metadata_matches, migration_database  # noqa: F401

from alembic import command


def test_analysis_migration_compiles_postgresql_sql():
    buffer = StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=buffer)
    command.upgrade(config, "head", sql=True)
    sql = buffer.getvalue()
    assert "CREATE TABLE analysis_runs" in sql
    assert "CREATE TABLE course_findings" in sql
    assert "CREATE TABLE research_cache" in sql
    assert "FOREIGN KEY(run_id, programme_revision_id) REFERENCES analysis_runs" in sql
    assert "FOREIGN KEY(course_id, programme_revision_id) REFERENCES courses" in sql
    assert "expires_at TIMESTAMP WITH TIME ZONE" in sql


@pytest.mark.integration
def test_analysis_schema_upgrade_preserves_old_data_and_refuses_populated_downgrade(
    migration_database,  # noqa: F811 - shared fixture
):
    connection, config = migration_database
    command.upgrade(config, "0004_reference_evidence")
    connection.commit()
    institution_id, dataset_id = uuid4(), uuid4()
    connection.execute(
        text(
            "INSERT INTO institutions (id,name,is_synthetic) "
            "VALUES (:id,'Synthetic Phase4 University',true)"
        ),
        {"id": institution_id},
    )
    connection.execute(
        text(
            "INSERT INTO datasets (id,registry_key,name,category,is_synthetic) "
            "VALUES (:id,'SYNTHETIC-PHASE4-PRIOR','Synthetic retained dataset','synthetic',true)"
        ),
        {"id": dataset_id},
    )
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    _assert_metadata_matches(connection)
    assert connection.scalar(text("SELECT count(*) FROM institutions")) == 1
    assert connection.scalar(text("SELECT count(*) FROM datasets")) == 1
    cache_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO research_cache "
            "(id,cache_key,policy_sha256,response_json,expires_at,is_synthetic) "
            "VALUES (:id,:cache,:policy,'{}',:expires,true)"
        ),
        {
            "id": cache_id,
            "cache": "a" * 64,
            "policy": "b" * 64,
            "expires": datetime(2027, 1, 1, tzinfo=UTC),
        },
    )
    connection.commit()
    with pytest.raises(RuntimeError, match="Export Phase 4 analysis"):
        command.downgrade(config, "0004_reference_evidence")
    connection.rollback()
    assert connection.scalar(text("SELECT count(*) FROM research_cache")) == 1
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version"))
        == "0005_programme_analysis"
    )
    connection.execute(text("DELETE FROM research_cache WHERE id=:id"), {"id": cache_id})
    connection.commit()
    command.downgrade(config, "0004_reference_evidence")
    connection.commit()
    assert "analysis_runs" not in inspect(connection).get_table_names()
    _assert_metadata_matches(connection)
    assert connection.scalar(text("SELECT count(*) FROM datasets")) == 1
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    _assert_metadata_matches(connection)
