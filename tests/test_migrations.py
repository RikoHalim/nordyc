import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from alembic import command
from shiftos.db.base import Base


@pytest.mark.integration
def test_postgresql_migration_upgrade_constraints_and_downgrade() -> None:
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
                command.upgrade(config, "head")
                connection.commit()
                inspector = inspect(connection)
                assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {
                    "alembic_version"
                }
                context = MigrationContext.configure(
                    connection, opts={"compare_type": True, "compare_server_default": True}
                )
                assert compare_metadata(context, Base.metadata) == []

                institutions = Base.metadata.tables["institutions"]
                programmes = Base.metadata.tables["programmes"]
                revisions = Base.metadata.tables["programme_revisions"]
                courses = Base.metadata.tables["courses"]
                institution_id, programme_id, revision_id = uuid4(), uuid4(), uuid4()
                connection.execute(
                    institutions.insert().values(
                        id=institution_id, name="Synthetic Migration University"
                    )
                )
                connection.execute(
                    programmes.insert().values(
                        id=programme_id,
                        institution_id=institution_id,
                        name="Synthetic Migration Programme",
                    )
                )
                connection.execute(
                    revisions.insert().values(
                        id=revision_id, programme_id=programme_id, version_label="demo-v1"
                    )
                )
                connection.commit()
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(
                        revisions.insert().values(
                            id=uuid4(), programme_id=programme_id, version_label="demo-v1"
                        )
                    )
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(
                        courses.insert().values(
                            id=uuid4(),
                            programme_revision_id=uuid4(),
                            course_name="Synthetic Orphan",
                        )
                    )
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(
                        institutions.insert().values(
                            id=uuid4(), name="Invalid Country", country="US"
                        )
                    )
                assert connection.scalar(select(institutions.c.created_at)).utcoffset() is not None
                connection.rollback()

                command.downgrade(config, "base")
                connection.commit()
                assert set(inspect(connection).get_table_names()) <= {"alembic_version"}
                command.upgrade(config, "head")
                connection.commit()
                assert "courses" in inspect(connection).get_table_names()
            finally:
                connection.rollback()
                connection.dialect.default_schema_name = original_default_schema
                connection.exec_driver_sql("SET search_path TO public")
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
                connection.commit()
    finally:
        engine.dispose()
