"""Catalogue administration; network access is confined to opt-in worker jobs."""

import argparse
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from shiftos.core.config import Settings
from shiftos.core.errors import DomainError
from shiftos.db.session import create_database
from shiftos.schemas.ingestion import CatalogueImport, JobRead
from shiftos.services.ingestion.catalogue import enqueue_import
from shiftos.services.ingestion.fixtures import import_fixture
from shiftos.services.ingestion.worker import fail_stale_jobs, run_once


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SHIFT//OS catalogue administration")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("import-fixture", help="Import an explicitly synthetic fixture")
    command.add_argument("path", type=Path)
    catalogue = commands.add_parser(
        "import-curriculum", help="Queue a source-attributed structured JSON catalogue"
    )
    catalogue.add_argument("path", type=Path)
    catalogue.add_argument("--institution", type=UUID, required=True)
    worker = commands.add_parser("worker", help="Run durable catalogue jobs outside HTTP requests")
    worker.add_argument("--once", action="store_true")
    commands.add_parser(
        "fail-stale-jobs", help="Explicitly fail abandoned catalogue jobs older than one hour"
    )
    args = parser.parse_args(argv)
    database = None
    try:
        settings = Settings()
        database = create_database(settings.database_url.get_secret_value())
        if args.command == "worker":
            while True:
                job_id = run_once(database, settings)
                if job_id:
                    print(f"Processed catalogue job {job_id}", flush=True)
                if args.once:
                    return 0
                time.sleep(2)
        if args.command == "fail-stale-jobs":
            print(f"Failed stale jobs: {fail_stale_jobs(database)}")
            return 0
        with database.session_factory() as session:
            if args.command == "import-curriculum":
                if args.path.stat().st_size > 1_048_576:
                    raise ValueError("Manifest exceeds size limit")
                data = CatalogueImport.model_validate_json(args.path.read_bytes())
                result = JobRead.model_validate(enqueue_import(session, args.institution, data))
            else:
                result = import_fixture(session, args.path)
            session.commit()
        print(result.model_dump_json())
    except DomainError as exc:
        print(f"Command rejected: {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except (ValidationError, ValueError, OSError):
        print(
            "Import rejected: provide valid bounded JSON or an explicitly synthetic fixture.",
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError:
        print(
            "Command failed: check database connectivity and apply migrations.",
            file=sys.stderr,
        )
        return 1
    finally:
        if database is not None:
            database.engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
