import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, create_engine, func, inspect, select, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from alembic import command
from shiftos.core.config import Settings
from shiftos.db.base import Base
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import Course, ProgrammeRevision, Source
from shiftos.services.ingestion.worker import run_once


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
    metadata = Base.metadata
    revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    # Tests targeting the historical 0003 boundary compare only tables present then.
    if revision == "0003_curriculum_ingestion":
        metadata = MetaData(naming_convention=Base.metadata.naming_convention)
        for name in (
            "institutions",
            "programmes",
            "programme_revisions",
            "courses",
            "documents",
            "document_anchors",
            "jobs",
            "sources",
        ):
            Base.metadata.tables[name].to_metadata(metadata)
    elif revision == "0004_reference_evidence":
        metadata = MetaData(naming_convention=Base.metadata.naming_convention)
        for name, table in Base.metadata.tables.items():
            if name not in {
                "analysis_runs",
                "course_findings",
                "research_cache",
                "career_runs",
                "career_recommendations",
                "career_reviews",
                "action_plan_runs",
                "plan_recommendations",
                "action_plan_reviews",
            }:
                table.to_metadata(metadata)
    elif revision == "0005_programme_analysis":
        metadata = MetaData(naming_convention=Base.metadata.naming_convention)
        for name, table in Base.metadata.tables.items():
            if name not in {
                "career_runs",
                "career_recommendations",
                "career_reviews",
                "action_plan_runs",
                "plan_recommendations",
                "action_plan_reviews",
            }:
                table.to_metadata(metadata)
    elif revision == "0006_career_alignment":
        metadata = MetaData(naming_convention=Base.metadata.naming_convention)
        for name, table in Base.metadata.tables.items():
            if name not in {"action_plan_runs", "plan_recommendations", "action_plan_reviews"}:
                table.to_metadata(metadata)
    assert set(inspect(connection).get_table_names()) == set(metadata.tables) | {"alembic_version"}
    context = MigrationContext.configure(
        connection, opts={"compare_type": True, "compare_server_default": True}
    )
    assert compare_metadata(context, metadata) == []


def _seed_original_schema(connection: Connection) -> dict[str, list[dict]]:
    """Reflect 0001 tables so no new-model fields enter the old inserts."""
    original = MetaData()
    original.reflect(
        connection,
        only=[
            "institutions",
            "programmes",
            "programme_revisions",
            "courses",
            "documents",
            "document_anchors",
            "jobs",
        ],
    )
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
        if not rows:
            assert connection.scalar(select(func.count()).select_from(reflected.tables[name])) == 0
            continue
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
    # Exercise the 0002 guard in isolation; 0003 has its own loss-prevention tests.
    command.upgrade(config, "0002_catalogue_sources")
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


@pytest.mark.integration
def test_populated_0002_upgrade_to_0003_preserves_provenance_and_safe_roundtrip(
    migration_database: tuple[Connection, Config],
) -> None:
    """No new importer metadata may be invented for pre-existing catalogue rows."""
    connection, config = migration_database
    command.upgrade(config, "0002_catalogue_sources")
    connection.commit()
    _seed_original_schema(connection)
    previous = MetaData()
    previous.reflect(connection)
    source_id = uuid4()
    connection.execute(
        previous.tables["sources"]
        .insert()
        .values(
            id=source_id,
            publisher="Synthetic Migration Publisher",
            title="Synthetic 0002 catalogue",
            url="https://example.invalid/legacy-catalogue",
            evidence_class="synthetic_demo",
            is_synthetic=True,
        )
    )
    connection.execute(
        previous.tables["courses"]
        .update()
        .values(
            source_id=source_id,
            source_locator="#synthetic-legacy-course",
            updated_at=previous.tables["courses"].c.updated_at,
        )
    )
    connection.execute(
        previous.tables["institutions"]
        .update()
        .values(
            website_url="https://example.invalid/",
            updated_at=previous.tables["institutions"].c.updated_at,
        )
    )
    connection.commit()
    snapshot = {
        name: [dict(row) for row in connection.execute(select(table)).mappings()]
        for name, table in previous.tables.items()
        if name != "alembic_version"
    }
    connection.commit()
    command.upgrade(config, "0003_curriculum_ingestion")
    connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    _assert_metadata_matches(connection)
    assert connection.scalar(text("SELECT import_fingerprint FROM programme_revisions")) is None
    assert connection.scalar(text("SELECT metadata_json FROM programme_revisions")) == {}
    assert connection.scalar(text("SELECT raw_year_label FROM courses")) is None
    assert connection.scalar(text("SELECT source_url FROM courses")) is None
    assert connection.scalar(text("SELECT review_notes FROM courses")) == []
    assert connection.scalar(text("SELECT institution_id FROM jobs")) is None
    assert connection.scalar(text("SELECT payload_json FROM jobs")) == {}
    assert connection.scalar(text("SELECT result_json FROM jobs")) == {}
    connection.commit()
    command.downgrade(config, "0002_catalogue_sources")
    connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    assert "import_fingerprint" not in {
        column["name"] for column in inspect(connection).get_columns("programme_revisions")
    }
    connection.commit()
    command.upgrade(config, "head")
    connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    _assert_metadata_matches(connection)


@pytest.mark.integration
def test_0003_downgrade_refuses_each_populated_phase2_metadata_family(
    migration_database: tuple[Connection, Config],
) -> None:
    connection, config = migration_database
    command.upgrade(config, "0002_catalogue_sources")
    connection.commit()
    snapshot = _seed_original_schema(connection)
    connection.commit()
    command.upgrade(config, "0003_curriculum_ingestion")
    connection.commit()
    for table_name, column, value, empty in [
        ("programmes", "ingestion_key", "a" * 64, None),
        ("programme_revisions", "import_fingerprint", "b" * 64, None),
        ("programme_revisions", "metadata_json", {"synthetic_note": "retain"}, {}),
        ("courses", "raw_year_label", "Year 2/3", None),
        ("courses", "raw_semester_label", "Semester 1/2", None),
        ("courses", "elective_group", "Synthetic elective group", None),
        ("courses", "source_url", "https://example.invalid/catalogue", None),
        ("courses", "review_notes", ["Synthetic review note"], []),
        ("jobs", "institution_id", snapshot["institutions"][0]["id"], None),
        ("jobs", "idempotency_key", "synthetic-key", None),
        ("jobs", "payload_json", {"synthetic_payload": True}, {}),
        ("jobs", "result_json", {"synthetic_result": "retain"}, {}),
    ]:
        table = Base.metadata.tables[table_name]
        connection.execute(table.update().values({column: value, "updated_at": table.c.updated_at}))
        connection.commit()
        with pytest.raises(RuntimeError, match="Export Phase 2 catalogue data"):
            command.downgrade(config, "0002_catalogue_sources")
        connection.rollback()
        assert connection.scalar(select(table.c[column])) == value
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0003_curriculum_ingestion"
        )
        connection.execute(table.update().values({column: empty, "updated_at": table.c.updated_at}))
        connection.commit()
    _assert_original_rows_preserved(connection, snapshot)
    _assert_metadata_matches(connection)


@pytest.mark.integration
def test_postgresql_curriculum_queue_reimport_revisions_and_fastapi_retrieval(
    migration_database: tuple[Connection, Config],
) -> None:
    """Migrations, ORM writes, worker and HTTP reads share an isolated PG schema."""
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    settings = Settings(_env_file=None, app_env="test")
    manifest = {
        "name": "Bachelor of Synthetic PostgreSQL Studies",
        "canonical_url": "https://example.invalid/courses/synthetic-pg",
        "source_url": "https://example.invalid/courses/synthetic-pg",
        "source_locator": "#synthetic-curriculum",
        "retrieved_at": "2026-10-20T00:00:00Z",
        "reviewed": True,
        "courses": [
            {
                "course_name": "Synthetic PG Foundations",
                "year": 1,
                "source_locator": "#synthetic-year1 > li",
                "source_excerpt": "Synthetic PG Foundations",
            },
            {
                "course_name": "Synthetic PG Elective",
                "course_type": "ELECTIVE",
                "raw_year_label": "Year 3/4",
                "elective_group": "Synthetic choice group",
                "source_locator": "#synthetic-elective > li",
                "source_excerpt": "Synthetic PG Elective",
            },
        ],
    }
    with TestClient(create_app(settings=settings, database=database)) as client:
        response = client.post(
            "/api/v1/institutions",
            json={
                "name": "Synthetic PostgreSQL Test University",
                "website_url": "https://example.invalid/",
                "is_synthetic": True,
            },
        )
        assert response.status_code == 201, response.text
        institution = response.json()

        def enqueue_and_process(payload: dict) -> dict:
            response = client.post(
                f"/api/v1/institutions/{institution['id']}/imports",
                json={"is_synthetic": True, "programmes": [payload]},
            )
            assert response.status_code == 202, response.text
            queued = response.json()
            assert run_once(database, settings) == UUID(queued["id"])
            completed = client.get(f"/api/v1/catalogue/jobs/{queued['id']}").json()
            assert completed["status"] == "SUCCEEDED", completed
            return completed["result"]["entries"][0]

        first = enqueue_and_process(manifest)
        repeated = enqueue_and_process(manifest)
        assert repeated["status"] == "unchanged"
        assert first["revision_id"] == repeated["revision_id"]
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(ProgrammeRevision)) == 1
            assert session.scalar(select(func.count()).select_from(Source)) == 1
            assert session.scalar(select(func.count()).select_from(Course)) == 2
        changed = {
            **manifest,
            "retrieved_at": "2026-10-21T00:00:00Z",
            "courses": [
                {
                    "course_name": "Synthetic PG Revised Foundations",
                    "year": 2,
                    "source_locator": "#synthetic-year2 > li",
                    "source_excerpt": "Synthetic PG Revised Foundations",
                }
            ],
        }
        second = enqueue_and_process(changed)
        assert second["revision_id"] != first["revision_id"]
        replay = enqueue_and_process(manifest)
        assert replay["status"] == "unchanged" and replay["active"] is False
        path = f"/api/v1/programmes/{first['programme_id']}"
        active = client.get(path + "/courses")
        assert active.status_code == 200
        assert active.json()["programme_revision_id"] == second["revision_id"]
        assert active.json()["items"][0]["course_name"] == "Synthetic PG Revised Foundations"
        old = client.get(path + f"/revisions/{first['revision_id']}/courses")
        assert old.status_code == 200
        assert old.json()["total"] == 2
        elective = next(item for item in old.json()["items"] if item["course_type"] == "ELECTIVE")
        assert elective["year"] is None and elective["raw_year_label"] == "Year 3/4"
        assert elective["source_url"] == manifest["source_url"]
        assert elective["is_synthetic"] is True and elective["is_verified"] is False
        assert client.get(path + "/revisions").json()["total"] == 2
        coverage = client.get(path + "/coverage").json()
        assert coverage["course_count"] == 1
        assert coverage["graduation_curriculum_complete"] is False
        forbidden = client.post(path + "/courses", json={"course_name": "Synthetic mutation"})
        assert forbidden.status_code == 409
    connection.commit()
    with pytest.raises(RuntimeError, match="Export Phase 2 catalogue data"):
        command.downgrade(config, "0002_catalogue_sources")
    connection.rollback()
    assert connection.scalar(text("SELECT count(*) FROM programme_revisions")) == 2
    assert connection.scalar(text("SELECT count(*) FROM courses")) == 3
