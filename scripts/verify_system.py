"""Explicit non-network synthetic acceptance in newly owned PostgreSQL schemas.

The mock adapter below is acceptance-only. It invokes the real worker and result
validators, never a paid provider. Credentials are not read or copied into the
process settings. Each workload gets a new isolated schema with an owner marker;
the ambient application/production schema is never selected for writes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import tracemalloc
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from alembic import command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

from shiftos.core.config import Settings  # noqa: E402
from shiftos.db.session import Database  # noqa: E402
from shiftos.schemas.analysis import EvidencePacket  # noqa: E402
from shiftos.services.analysis.validation import offline_result  # noqa: E402
from shiftos.services.ingestion.worker import run_once  # noqa: E402
from shiftos.services.integration import run_synthetic_system  # noqa: E402


@contextmanager
def mocked_workers():
    """No HTTP and no real credential is usable within this explicit test scope."""
    calls = Counter()

    class MockClaude:
        def __init__(self, settings):
            self.settings, self.deadline = settings, None
            self.last_response_metadata = {}

        def generate(self, payload, schema, **kwargs):
            started = time.perf_counter()
            task = payload.get("task", "phase4_course_analysis")
            calls[task] += 1
            if task == "phase5_admitted_option_comparison":
                result = {
                    "choices": [
                        {
                            "recommendation_key": row["key"],
                            "option_index": 0,
                            "reason": "minimum_disruption",
                            "review_question": (
                                "Review the evidence limitations before changing the curriculum."
                            ),
                            "citations": row["citations"][:1],
                        }
                        for row in payload["options"]
                    ]
                }
            elif task == "phase6_admitted_pathway_review":
                result = {
                    "choices": [
                        {
                            "pathway_key": row["key"],
                            "scenario_key": payload["scenarios"][0]["key"],
                            "review_question": (
                                "Confirm the proposed activity and its assessment evidence."
                            ),
                            "citations": row["citations"][:1],
                        }
                        for row in payload["pathways"]
                    ]
                }
            else:
                result = offline_result(EvidencePacket.model_validate(payload)).model_dump(
                    mode="json"
                )
                result["result_mode"] = "live_model"
            self.last_response_metadata = {
                "actual_model": self.settings.claude_model + "-synthetic-mock",
                "request_count": 1,
                "usage": {},
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            return result

    def deny_http(*args, **kwargs):
        raise RuntimeError("Real HTTP is prohibited in synthetic system verification")

    async def deny_async_http(*args, **kwargs):
        raise RuntimeError("Real HTTP is prohibited in synthetic system verification")

    def worker(database, settings):
        return run_once(database, settings)

    worker.synthetic_mock_only = True
    with (
        patch("shiftos.services.analysis.orchestrator.ReplitClaudeProvider", MockClaude),
        patch("shiftos.services.career.reasoning.ReplitClaudeProvider", MockClaude),
        patch("shiftos.services.pathways.reasoning.ReplitClaudeProvider", MockClaude),
        patch.object(httpx.HTTPTransport, "handle_request", deny_http),
        patch.object(httpx.AsyncHTTPTransport, "handle_async_request", deny_async_http),
    ):
        yield worker, calls


def test_settings(database_url):
    """Process-local fixture settings; existing environment/files remain untouched."""
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=database_url,
        catalogue_write_token="SYNTHETIC-SYSTEM-CATALOGUE",
        analysis_write_token="SYNTHETIC-SYSTEM-ANALYSIS",
        analysis_model_provider="replit_claude",
        claude_enabled=True,
        replit_anthropic_api_key=None,
        replit_anthropic_base_url=None,
        brave_search_api_key=None,
        gemini_api_key=None,
        gemini_enabled=False,
        analysis_gemini_fallback_enabled=False,
        research_enabled=False,
        discovery_enabled=False,
        discovery_terms_reviewed=False,
        analysis_external_processing_allowed=True,
        analysis_provider_max_attempts=1,
        analysis_validation_max_attempts=1,
        claude_max_output_tokens=4096,
    )


def validate_database_url(value):
    url = make_url(value)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not url.database
        or not any(
            label in url.database.casefold() for label in ("test", "verification", "synthetic")
        )
        or url.query
    ):
        raise ValueError(
            "Select an explicit owned loopback PostgreSQL test database without URL options"
        )
    return url.set(drivername="postgresql+psycopg")


@contextmanager
def isolated_database(value):
    url = validate_database_url(value)
    schema = "shiftos_system_" + uuid4().hex
    owner_marker = "SHIFTOS_PHASE7_SYNTHETIC_ONLY:" + uuid4().hex
    admin = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
    database = None
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f"COMMENT ON SCHEMA \"{schema}\" IS '{owner_marker}'")
            connection.commit()
        engine = create_engine(
            url,
            hide_parameters=True,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3, "options": f"-csearch_path={schema}"},
        )
        database = Database(engine, sessionmaker(bind=engine, expire_on_commit=False))
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "alembic"))
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()
        yield database
    finally:
        if database is not None:
            database.engine.dispose()
        with admin.connect() as connection:
            found = connection.scalar(
                text(
                    "SELECT obj_description(oid, 'pg_namespace') FROM pg_namespace "
                    "WHERE nspname=:name"
                ),
                {"name": schema},
            )
            if found == owner_marker and re.fullmatch(r"shiftos_system_[0-9a-f]{32}", schema):
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
                connection.commit()
        admin.dispose()


def _normalise(value, identifiers=None):
    """Publish readable schema examples, clearly labelled as normalised fixtures."""
    identifiers = identifiers if identifiers is not None else {}
    if isinstance(value, dict):
        return {key: _normalise(item, identifiers) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_normalise(item, identifiers) for item in value]
    if isinstance(value, str):

        def replace(match):
            original = str(UUID(match.group()))
            identifiers.setdefault(
                original, str(uuid5(NAMESPACE_URL, f"synthetic-api-{len(identifiers)}"))
            )
            return identifiers[original]

        if UUID_PATTERN.search(value):
            return UUID_PATTERN.sub(replace, value)
        if re.fullmatch(r"[0-9a-f]{64}", value):
            return "0" * 64
        if re.match(r"^\d{4}-\d{2}-\d{2}T", value):
            return "2026-10-25T00:00:00+00:00"
    return value


def export_api_examples(report, output):
    output.mkdir(parents=True, exist_ok=True)
    samples = {
        key: report["responses"][key]
        for key in ("courses", "phase4_courses", "pathways", "scenarios", "sdg", "plan_review")
    }
    identifiers = {}
    for key, response in samples.items():
        if isinstance(response, dict) and isinstance(response.get("items"), list):
            response = {**response, "items": response["items"][:3], "limit": 3}
        artifact = {
            "fixture_id": report["fixture_id"],
            "is_synthetic": True,
            "provider_execution": report["provider_execution"],
            "normalised_fields": ["UUIDs", "timestamps", "content digests"],
            "limitations": (
                "Bounded, redacted schema example from an actual synthetic API response; "
                "not a live provider or production result. Normalised version hashes "
                "must never be submitted as real review approvals."
            ),
            "response": _normalise(response, identifiers),
        }
        (output / f"{key}.synthetic.json").write_text(
            json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        required=True,
        help="Explicit owned loopback PostgreSQL test URL; never the ambient production URL",
    )
    parser.add_argument("--sizes", type=int, nargs="+", default=[6, 30, 100])
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--export-api", action="store_true")
    args = parser.parse_args()
    try:
        validate_database_url(args.database_url)
        if len(args.sizes) > 3 or any(not 6 <= size <= 200 for size in args.sizes):
            raise ValueError("Choose at most three bounded 6–200-course workloads")
        args.report.resolve().relative_to((ROOT / "data/local").resolve())
    except (ValueError, TypeError):
        parser.error(
            "Use an explicit owned loopback PostgreSQL test database, bounded sizes "
            "and a report under data/local"
        )
    reports = []
    try:
        for size in args.sizes:
            with isolated_database(args.database_url) as database:
                with mocked_workers() as (worker, calls):
                    tracemalloc.start()
                    try:
                        receipt = run_synthetic_system(
                            database,
                            test_settings(args.database_url),
                            workdir=args.report.parent / f"inputs-{size}",
                            course_count=size,
                            mode="live",
                            worker=worker,
                        )
                        receipt["metrics"]["python_peak_bytes"] = tracemalloc.get_traced_memory()[1]
                    finally:
                        tracemalloc.stop()
                    receipt["mocked_provider_calls"] = dict(calls)
                    reports.append(receipt)
        result = {
            "status": "PASS",
            "is_synthetic": True,
            "live_requests": 0,
            "observed_cost": None,
            "workloads": reports,
            "database_isolation": (
                "Per-run owned marked schemas removed after committed independent reads."
            ),
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        if args.export_api:
            export_api_examples(reports[0], ROOT / "examples/api")
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "workloads": [
                        {
                            "courses": row["course_count"],
                            "elapsed_ms": row["metrics"]["elapsed_ms"],
                            "sql_statements": row["metrics"]["sql_statements"],
                            "plan_response_bytes": row["metrics"]["plan_response_bytes"],
                            "postgresql_verified": row["persistence"]["postgresql_verified"],
                            "mocked_calls": row["mocked_provider_calls"],
                        }
                        for row in reports
                    ],
                    "live_requests": 0,
                    "observed_cost": None,
                }
            )
        )
    except Exception as exc:
        print(
            json.dumps({"status": "FAILED", "error_type": type(exc).__name__, "live_requests": 0})
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
