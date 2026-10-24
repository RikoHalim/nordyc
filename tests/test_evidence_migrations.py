from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from test_migrations import (  # reuse isolated PostgreSQL schema fixture
    _assert_metadata_matches,
    migration_database,  # noqa: F401
)

from alembic import command


def test_reference_migration_compiles_offline_postgresql_sql():
    buffer = StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=buffer)
    command.upgrade(config, "head", sql=True)
    sql = buffer.getvalue()
    assert "CREATE TABLE dataset_versions" in sql
    assert "CREATE TABLE workforce_observations" in sql
    assert "CREATE TABLE evidence_processing_logs" in sql
    assert "FOREIGN KEY(evidence_id, version_id) REFERENCES evidence_references" in sql
    assert "publication_date VARCHAR(100)" in sql
    assert "retrieved_at TIMESTAMP WITH TIME ZONE" in sql


@pytest.mark.integration
def test_reference_upgrade_preserves_curriculum_and_populated_downgrade_guard(
    migration_database,  # noqa: F811 - imported pytest fixture
):
    connection, config = migration_database
    command.upgrade(config, "0003_curriculum_ingestion")
    connection.commit()
    institution_id = uuid4()
    connection.execute(
        text("INSERT INTO institutions (id,name,is_synthetic) VALUES (:id,:name,true)"),
        {"id": institution_id, "name": "Synthetic Phase 3 migration university"},
    )
    connection.commit()
    command.upgrade(config, "0004_reference_evidence")
    connection.commit()
    _assert_metadata_matches(connection)
    assert (
        connection.scalar(
            text("SELECT name FROM institutions WHERE id=:id"), {"id": institution_id}
        )
        == "Synthetic Phase 3 migration university"
    )
    dataset_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO datasets (id,registry_key,name,category,is_synthetic) "
            "VALUES (:id,'SYNTHETIC-MIGRATION','Synthetic migration data','synthetic_demo',true)"
        ),
        {"id": dataset_id},
    )
    connection.commit()
    with pytest.raises(RuntimeError, match="Export Phase 3 reference evidence"):
        command.downgrade(config, "0003_curriculum_ingestion")
    connection.rollback()
    assert connection.scalar(text("SELECT count(*) FROM datasets")) == 1
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
        "0004_reference_evidence"
    )
    connection.execute(text("DELETE FROM datasets WHERE id=:id"), {"id": dataset_id})
    connection.commit()
    command.downgrade(config, "0003_curriculum_ingestion")
    connection.commit()
    assert "datasets" not in inspect(connection).get_table_names()
    assert connection.scalar(text("SELECT count(*) FROM institutions")) == 1
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    _assert_metadata_matches(connection)
