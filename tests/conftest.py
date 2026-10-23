from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shiftos.core.config import Settings
from shiftos.db.base import Base
from shiftos.db.session import Database, create_database
from shiftos.main import create_app


@pytest.fixture
def fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "sample_programme.json"


@pytest.fixture
def database() -> Iterator[Database]:
    database = create_database("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(database.engine)
    try:
        yield database
    finally:
        database.engine.dispose()


@pytest.fixture
def session(database: Database) -> Iterator[Session]:
    with database.session_factory() as session:
        yield session


@pytest.fixture
def client(database: Database) -> Iterator[TestClient]:
    settings = Settings(_env_file=None, app_env="test", database_url="sqlite+pysqlite:///:memory:")
    with TestClient(create_app(settings=settings, database=database)) as client:
        yield client
