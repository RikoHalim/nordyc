"""Offline maintenance commands: python -m shiftos.cli import-fixture PATH."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from shiftos.core.config import Settings
from shiftos.core.errors import DomainError
from shiftos.db.session import create_database
from shiftos.services.ingestion.fixtures import import_fixture


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SHIFT//OS offline administration")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("import-fixture", help="Import an explicitly synthetic fixture")
    command.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    database = None
    try:
        settings = Settings()
        database = create_database(settings.database_url.get_secret_value())
        with database.session_factory() as session:
            result = import_fixture(session, args.path)
            session.commit()
        print(result.model_dump_json())
    except DomainError:
        print("Fixture import rejected: existing IDs have incompatible content.", file=sys.stderr)
        return 1
    except (ValidationError, ValueError, OSError):
        print(
            "Fixture import rejected: provide a valid, explicitly synthetic JSON fixture.",
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError:
        print(
            "Fixture import failed: check database connectivity and apply migrations.",
            file=sys.stderr,
        )
        return 1
    finally:
        if database is not None:
            database.engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
