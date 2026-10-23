from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@dataclass(frozen=True)
class Database:
    engine: Engine
    session_factory: sessionmaker[Session]


def create_database(url: str) -> Database:
    parsed = make_url(url)
    options: dict = {"pool_pre_ping": True, "hide_parameters": True}
    if parsed.get_backend_name() == "sqlite":
        options.update(connect_args={"check_same_thread": False})
        if parsed.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool
    else:
        options.update(connect_args={"connect_timeout": 3}, pool_timeout=3)
    engine = create_engine(url, **options)
    if parsed.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

    return Database(engine, sessionmaker(bind=engine, expire_on_commit=False))


def get_session(request: Request) -> Iterator[Session]:
    database: Database = request.app.state.database
    with database.session_factory() as session:
        yield session
