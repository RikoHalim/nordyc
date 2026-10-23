import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import IntegrityError

from alembic import command
from shiftos.db.base import Base


@pytest.fixture
def migration_database() -> Iterator[tuple[Connection, Config]]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to opt in to real PostgreSQL migration testing")
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL; SQLite cannot verify migrations")
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    engine = create_engine(url)
    schema = f"shiftos_test_{uuid4().hex}"
    project_root = Path(__file__).resolve().parents[1]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
            original_default_schema = connection.dialect.default_schema_name
            try:
                connection.exec_driver_sql(f'SET search_path TO "{schema}"')
                connection.commit()
                connection.dialect.default_schema_name = schema
                config.attributes["connection"] = connection
                yield connection, config
            finally:
                connection.rollback()
                connection.dialect.default_schema_name = original_default_schema
                connection.exec_driver_sql("SET search_path TO public")
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
                connection.commit()
    finally:
        engine.dispose()


def _assert_metadata_matches(connection: Connection) -> None:
    assert set(inspect(connection).get_table_names()) == set(Base.metadata.tables) | {
        "alembic_version"
    }
    context = MigrationContext.configure(
        connection, opts={"compare_type": True, "compare_server_default": True}
    )
    assert compare_metadata(context, Base.metadata) == []


def _seed_original_schema(connection: Connection) -> dict[str, list[dict]]:
    """Reflect 0001 tables so no new-model fields enter the old inserts."""
    original = MetaData()
    original.reflect(connection, only=list(set(Base.metadata.tables) - {"sources"}))
    institution_id, programme_id, revision_id = uuid4(), uuid4(), uuid4()
    course_id, document_id, anchor_id = uuid4(), uuid4(), uuid4()
    connection.execute(
        original.tables["institutions"]
        .insert()
        .values(id=institution_id, name="Synthetic Migration University", is_synthetic=True)
    )
    connection.execute(
        original.tables["programmes"]
        .insert()
        .values(
            id=programme_id,
            institution_id=institution_id,
            name="Synthetic Migration Programme",
            academic_year="2026/2027",
            is_synthetic=True,
        )
    )
    connection.execute(
        original.tables["programme_revisions"]
        .insert()
        .values(
            id=revision_id, programme_id=programme_id, version_label="demo-v1", is_synthetic=True
        )
    )
    connection.execute(
        original.tables["programmes"].update().values(active_revision_id=revision_id)
    )
    connection.execute(
        original.tables["courses"]
        .insert()
        .values(
            id=course_id,
            programme_revision_id=revision_id,
            course_name="Synthetic Migration Course",
            year=2,
            course_type="ELECTIVE",
            is_synthetic=True,
        )
    )
    connection.execute(
        original.tables["documents"]
        .insert()
        .values(
            id=document_id,
            programme_revision_id=revision_id,
            course_id=course_id,
            filename="synthetic-migration.json",
            document_kind="PROGRAMME_STRUCTURE",
            format="JSON",
            content_sha256="0" * 64,
            parser_version="synthetic-v1",
            metadata_json={"is_synthetic": True, "purpose": "migration test"},
            is_synthetic=True,
        )
    )
    connection.execute(
        original.tables["document_anchors"]
        .insert()
        .values(
            id=anchor_id,
            document_id=document_id,
            locator="synthetic:courses:0",
            excerpt="Synthetic Migration Course",
            is_synthetic=True,
        )
    )
    connection.execute(
        original.tables["courses"].update().values(inventory_source_anchor_id=anchor_id)
    )
    connection.execute(
        original.tables["jobs"]
        .insert()
        .values(id=uuid4(), programme_revision_id=revision_id, is_synthetic=True)
    )
    connection.commit()
    return {
        name: [dict(row) for row in connection.execute(select(table)).mappings()]
        for name, table in original.tables.items()
    }


def _assert_original_rows_preserved(
    connection: Connection, snapshot: dict[str, list[dict]]
) -> None:
    reflected = MetaData()
    reflected.reflect(connection, only=list(snapshot))
    for name, rows in snapshot.items():
        original_columns = [reflected.tables[name].c[column] for column in rows[0]]
        assert [
            dict(row) for row in connection.execute(select(*original_columns)).mappings()
        ] == rows


@pytest.mark.integration
def test_postgresql_migration_clean_upgrade_and_downgrade(
    migration_database: tuple[Connection, Config],
) -> None:
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    _assert_metadata_matches(connection)
    connection.commit()
    command.downgrade(config, "base")
    connection.commit()
    assert set(inspect(connection).get_table_names()) <= {"alembic_version"}
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    _assert_metadata_matches(connection)


@pytest.mark.integration
def test_populated_0001_upgrade_preserves_data_and_enforces_new_constraints(
    migration_database: tuple[Connection, Config],
) -> None:
    connection, config = migration_database
    command.upgrade(config, "0001_foundation")
    connection.commit()
    snapshot = _seed_original_schema(connection)
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    _assert_metadata_matches(connection)
    assert connection.scalar(text("SELECT is_verified FROM courses")) is False
    assert connection.scalar(text("SELECT source_id FROM courses")) is None
    assert connection.scalar(text("SELECT source_locator FROM courses")) is None
    assert connection.scalar(text("SELECT count(*) FROM sources")) == 0

    institutions = Base.metadata.tables["institutions"]
    revisions = Base.metadata.tables["programme_revisions"]
    courses = Base.metadata.tables["courses"]
    sources = Base.metadata.tables["sources"]
    programme_id = snapshot["programmes"][0]["id"]
    revision_id = snapshot["programme_revisions"][0]["id"]
    for table, values in [
        (revisions, {"programme_id": programme_id, "version_label": "demo-v1"}),
        (courses, {"programme_revision_id": uuid4(), "course_name": "Synthetic Orphan"}),
        (institutions, {"name": "Synthetic Invalid Country", "country": "US"}),
        (sources, {"publisher": "Synthetic Publisher", "title": "Missing origin"}),
        (
            sources,
            {
                "publisher": "Synthetic Publisher",
                "title": "Inconsistent synthetic",
                "url": "https://example.invalid/source",
                "is_synthetic": True,
            },
        ),
        (
            sources,
            {
                "publisher": "Synthetic Publisher",
                "title": "Invalid class",
                "url": "https://example.invalid/source",
                "evidence_class": "INVENTED",
            },
        ),
        (
            courses,
            {
                "programme_revision_id": revision_id,
                "course_name": "Missing source",
                "is_verified": True,
            },
        ),
    ]:
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(table.insert().values(id=uuid4(), **values))
    source_id = uuid4()
    published_at = datetime(2026, 1, 2, tzinfo=UTC)
    connection.execute(
        sources.insert().values(
            id=source_id,
            publisher="Synthetic Test Publisher",
            title="Synthetic origin metadata example",
            url="https://example.invalid/source",
            published_at=published_at,
        )
    )
    source = connection.execute(select(sources)).mappings().one()
    assert source["evidence_class"] == "inference"
    assert source["published_at"] == published_at
    assert source["observed_at"] is None
    assert source["collected_at"] is None
    assert source["created_at"].utcoffset() is not None
    connection.execute(
        courses.update().values(
            source_id=source_id, source_locator="#course-list", updated_at=courses.c.updated_at
        )
    )
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(sources.delete().where(sources.c.id == source_id))
    connection.commit()
    with pytest.raises(RuntimeError, match="Refusing 0002 downgrade: sources"):
        command.downgrade(config, "0001_foundation")
    connection.rollback()
    assert "sources" in inspect(connection).get_table_names()
    assert connection.scalar(select(sources.c.id)) == source_id
    _assert_original_rows_preserved(connection, snapshot)


@pytest.mark.integration
def test_downgrade_refuses_new_metadata_and_preserves_old_rows_on_safe_roundtrip(
    migration_database: tuple[Connection, Config],
) -> None:
    connection, config = migration_database
    command.upgrade(config, "0001_foundation")
    connection.commit()
    snapshot = _seed_original_schema(connection)
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    for table_name, column, value in [
        ("institutions", "website_url", "https://example.invalid/university"),
        ("institutions", "source_locator", "#university"),
        ("programmes", "level", "undergraduate"),
        ("programmes", "discipline_key", "synthetic-arts"),
        ("programmes", "canonical_url", "https://example.invalid/programme"),
        ("programmes", "source_locator", "#programme"),
        ("courses", "source_locator", "#course"),
    ]:
        table = Base.metadata.tables[table_name]
        connection.execute(table.update().values({column: value, "updated_at": table.c.updated_at}))
        connection.commit()
        with pytest.raises(RuntimeError, match=f"Refusing 0002 downgrade: {table_name}"):
            command.downgrade(config, "0001_foundation")
        connection.rollback()
        assert connection.scalar(select(table.c[column])) == value
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0002_catalogue_sources"
        )
        connection.execute(table.update().values({column: None, "updated_at": table.c.updated_at}))
        connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    connection.commit()
    command.downgrade(config, "0001_foundation")
    connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    assert "sources" not in inspect(connection).get_table_names()
    course_columns = {column["name"] for column in inspect(connection).get_columns("courses")}
    assert "is_verified" not in course_columns
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    _assert_metadata_matches(connection)
