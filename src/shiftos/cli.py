"""Catalogue administration; network access is confined to opt-in worker jobs."""

import argparse
import json
import sys
import time
from collections.abc import Sequence
from datetime import datetime
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
    pdf = commands.add_parser("upload-curriculum-pdf", help="Queue a private curriculum PDF upload")
    pdf.add_argument("path", type=Path)
    pdf.add_argument("--programme", type=UUID, required=True)
    pdf.add_argument("--source-url")
    pdf.add_argument("--regions", type=Path, help="Optional JSON list of reviewed page rectangles")
    worker = commands.add_parser("worker", help="Run durable catalogue jobs outside HTTP requests")
    worker.add_argument("--once", action="store_true")
    analysis = commands.add_parser(
        "analyse-programme", help="Queue evidence-bounded programme screening"
    )
    analysis.add_argument("--programme", type=UUID, required=True)
    analysis.add_argument("--revision", type=UUID)
    analysis.add_argument("--mode", choices=("live", "offline"), default="live")
    analysis.add_argument("--no-research", action="store_true")
    analysis.add_argument("--idempotency-key")
    claude = commands.add_parser(
        "verify-claude",
        help="Inspect managed Claude configuration; optionally test one synthetic course",
    )
    claude.add_argument(
        "--live", action="store_true", help="Make one bounded synthetic-only Claude request"
    )
    claude.add_argument("--report", type=Path, help="Write the secret-free verification report")
    commands.add_parser(
        "fail-stale-jobs", help="Explicitly fail abandoned catalogue jobs older than one hour"
    )
    evidence = commands.add_parser("ingest-evidence", help="Explicit registry-driven evidence ETL")
    evidence.add_argument("--registry", type=Path, default=Path("data/dataset_registry.csv"))
    evidence.add_argument("--policy", type=Path, default=Path("data/evidence_acquisition.json"))
    evidence.add_argument("--dataset", action="append", dest="dataset_ids")
    evidence.add_argument("--file", type=Path, dest="local_path")
    evidence.add_argument("--retrieved-at", type=datetime.fromisoformat)
    evidence.add_argument("--live", action="store_true", help="Opt in after per-source review")
    evidence.add_argument("--synthetic", action="store_true")
    evidence.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    database = None
    try:
        settings = Settings()
        if args.command == "verify-claude":
            from shiftos.services.analysis.claude_verification import (
                inspect_claude_configuration,
                verify_claude,
            )

            report = (
                verify_claude(settings) if args.live else inspect_claude_configuration(settings)
            )
            output = json.dumps(report, indent=2)
            if args.report:
                try:
                    args.report.parent.mkdir(parents=True, exist_ok=True)
                    args.report.write_text(output, encoding="utf-8")
                except OSError:
                    # A request may already be billable. Preserve its actual
                    # outcome/usage even when exporting the report fails.
                    print(
                        json.dumps(
                            {
                                **report,
                                "report_write_failed": True,
                                "report_error_code": "verification_report_write_failed",
                            },
                            indent=2,
                        )
                    )
                    return 1
            print(output)
            return 0 if report["status"] in {"configuration_ready", "live_verified"} else 1
        database = create_database(settings.database_url.get_secret_value())
        if args.command == "analyse-programme":
            from shiftos.repositories.analysis import enqueue_analysis
            from shiftos.schemas.analysis import AnalysisRequest

            with database.session_factory() as session:
                run = enqueue_analysis(
                    session,
                    args.programme,
                    AnalysisRequest(
                        revision_id=args.revision,
                        mode=args.mode,
                        research=not args.no_research,
                        idempotency_key=args.idempotency_key,
                    ),
                )
                print(json.dumps({"analysis_id": str(run.id), "job_id": str(run.job_id)}))
            return 0
        if args.command == "upload-curriculum-pdf":
            from shiftos.services.ingestion.pdf import PdfCourseRegion
            from shiftos.services.ingestion.uploads import enqueue_pdf_upload

            if not 0 < args.path.stat().st_size <= 20_000_000:
                raise ValueError("Invalid PDF size")
            regions = None
            if args.regions:
                if args.regions.stat().st_size > 15_000:
                    raise ValueError("Region manifest too large")
                raw_regions = json.loads(args.regions.read_text(encoding="utf-8"))
                if not isinstance(raw_regions, list) or not 1 <= len(raw_regions) <= 50:
                    raise ValueError("Invalid region manifest")
                regions = [PdfCourseRegion.model_validate(r) for r in raw_regions]
            with database.session_factory() as session:
                result = enqueue_pdf_upload(
                    session,
                    args.programme,
                    args.path.read_bytes(),
                    settings,
                    source_url=args.source_url,
                    regions=regions,
                )
                print(JobRead.model_validate(result).model_dump_json())
            return 0
        if args.command == "ingest-evidence":
            from shiftos.services.evidence.pipeline import run_ingestion

            reports = run_ingestion(
                database,
                registry_path=args.registry,
                policy_path=args.policy,
                dataset_ids=args.dataset_ids,
                local_path=args.local_path,
                retrieved_at=args.retrieved_at,
                enabled=args.live,
                is_synthetic=args.synthetic,
            )
            output = json.dumps(reports, indent=2)
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(output, encoding="utf-8")
            print(output)
            return int(any(item["status"] == "FAILED" for item in reports))
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
        if args.command == "verify-claude":
            print(
                json.dumps(
                    {
                        "status": "blocked",
                        "provider": "replit_claude",
                        "provider_requests": 0,
                        "error_code": "verification_configuration_or_report_invalid",
                    }
                )
            )
            return 1
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
