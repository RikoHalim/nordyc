"""Private loopback preview backed by owned PostgreSQL and the real job worker.

This is an explicit developer acceptance launcher, never a production entrypoint.
It seeds reviewed fictional inputs through the Phase 7 integration workflow,
installs clearly identified mock providers, and prohibits provider HTTP. All
credentials, source artifacts and receipts remain in an ignored private folder.
The owned schema lives until shutdown; a matching owner marker is required for
its removal. No ambient database or provider configuration is selected.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import logging
import os
import re
import secrets
import sys
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import uvicorn
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from alembic import command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from verify_system import mocked_workers, test_settings, validate_database_url  # noqa: E402

from shiftos.core.access import AccessPolicy, validate_access_configuration  # noqa: E402
from shiftos.db.session import Database  # noqa: E402
from shiftos.main import create_app  # noqa: E402
from shiftos.services.integration import run_synthetic_system  # noqa: E402

SCHEMA_PATTERN = re.compile(r"shiftos_preview_[0-9a-f]{32}")
OWNER_PREFIX = "SHIFTOS_PHASE8_SYNTHETIC_PREVIEW:"
logger = logging.getLogger(__name__)


@contextmanager
def preview_mocked_workers():
    """Block standard-library HTTP too; local API browser/test traffic is permitted."""
    original_connect = http.client.HTTPConnection.connect

    def loopback_connect(connection):
        if connection.host not in {"127.0.0.1", "localhost", "::1"} or (
            connection._tunnel_host is not None
            and connection._tunnel_host not in {"127.0.0.1", "localhost", "::1"}
        ):
            raise RuntimeError("External HTTP is prohibited in the synthetic preview")
        return original_connect(connection)

    with (
        mocked_workers() as scope,
        patch.object(http.client.HTTPConnection, "connect", loopback_connect),
    ):
        yield scope


def private_json(path: Path, value) -> None:
    """Atomically write a newly restricted file without printing secret values."""
    path = Path(path)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, default=str)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def private_directory(path: Path, *, allowed_root: Path | None = None) -> Path:
    """The CLI can write runtime artifacts only inside its ignored data/local."""
    allowed = (allowed_root or ROOT / "data" / "local").resolve()
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(allowed) or resolved == allowed:
        raise ValueError("Select a private preview directory inside this checkout's data/local")
    if Path(path).is_symlink():
        raise ValueError("Preview directories cannot be symbolic links")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        resolved.chmod(0o700)
    return resolved


def drop_owned_schema(engine, schema: str, marker: str) -> bool:
    """Refuse deletion when either the generated identity or ownership changed."""
    if not SCHEMA_PATTERN.fullmatch(schema) or not marker.startswith(OWNER_PREFIX):
        raise ValueError("Refusing cleanup of a schema without a preview owner identity")
    with engine.connect() as connection:
        found = connection.scalar(
            text(
                "SELECT obj_description(oid,'pg_namespace') FROM pg_namespace WHERE nspname=:name"
            ),
            {"name": schema},
        )
        if found != marker:
            return False
        connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        connection.commit()
        return True


@contextmanager
def owned_database(value: str):
    """Migrate only a fresh marked schema in an explicitly selected test database."""
    url = validate_database_url(value)
    schema, marker = "shiftos_preview_" + uuid4().hex, OWNER_PREFIX + uuid4().hex
    admin = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
    database = None
    created = False
    ownership = {"schema": schema, "owner_marker": marker, "cleanup": "pending"}
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f"COMMENT ON SCHEMA \"{schema}\" IS '{marker}'")
            connection.commit()
            created = True
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
        yield database, ownership
    finally:
        cleanup_blocked = ownership.get("cleanup_blocked", False)
        if database is not None and not cleanup_blocked:
            database.engine.dispose()
        if created and not cleanup_blocked:
            ownership["cleanup"] = (
                "removed_owned_schema"
                if drop_owned_schema(admin, schema, marker)
                else "refused_owner_mismatch"
            )
        admin.dispose()


def preview_settings(database_url, run_dir: Path):
    """Explicit synthetic settings override ambient credentials and persistent gates."""
    return test_settings(database_url).model_copy(
        update={
            "api_access_mode": "legacy",  # Internal input seed; network API is scoped below.
            "api_access_policy_path": None,
            "curriculum_upload_dir": run_dir / "private-uploads",
            "analysis_permissions_path": ROOT / "data" / "analysis_permissions.json",
            "analysis_research_policy": ROOT / "data" / "research_policy.json",
            "claude_model": "claude-opus-5",
            "replit_anthropic_api_key": None,
            "replit_anthropic_base_url": None,
            "brave_search_api_key": None,
            "gemini_api_key": None,
        }
    )


def issue_access(run_dir: Path, institution_ids: list[str]):
    """Raw random credentials live only in auth.private.json; policy stores hashes."""
    credentials = {}
    principals = []
    definitions = (
        ("operator", ["read", "write", "review"], institution_ids),
        ("reader", ["read"], institution_ids),
        ("foreign", ["read", "write", "review"], [str(uuid4())]),
        ("admin", ["read", "write", "review", "admin"], []),
    )
    for alias, permissions, scope in definitions:
        token = secrets.token_urlsafe(48)
        credentials[alias] = {
            "token": token,
            "institution_ids": scope,
            "permissions": permissions,
        }
        principals.append(
            {
                "principal_id": "synthetic-preview-" + alias,
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                "institution_ids": scope,
                "permissions": permissions,
            }
        )
    policy = {"version": "phase7-access-1", "principals": principals}
    AccessPolicy.model_validate(policy)
    private_json(run_dir / "access-policy.private.json", policy)
    private_json(run_dir / "auth.private.json", credentials)
    for grant in credentials.values():
        grant["token"] = SecretStr(grant["token"])
    return credentials


class BackgroundWorker:
    """Poll and claim actual persisted jobs using independent database sessions."""

    def __init__(self, database, settings, worker, *, interval=0.2):
        self.database, self.settings, self.worker = database, settings, worker
        self.interval = interval
        self.stop_event = threading.Event()
        self.completed_jobs = 0
        self.last_error = None
        self.thread = threading.Thread(target=self._run, name="synthetic-preview-worker")

    def _run(self):
        while not self.stop_event.is_set():
            try:
                claimed = self.worker(self.database, self.settings)
                if claimed is not None:
                    self.completed_jobs += 1
            except Exception:
                self.last_error = "WORKER_LOOP_ERROR"
                logger.error("synthetic_preview_worker_loop_failed")
            self.stop_event.wait(self.interval)

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=30)
        if self.thread.is_alive():
            raise RuntimeError("Preview worker has not stopped; owned database cleanup is withheld")


@dataclass
class Preview:
    app: object
    database: Database
    settings: object
    run_dir: Path
    reports: list[dict]
    credentials: dict
    worker: BackgroundWorker
    receipt: dict

    def save_receipt(self):
        self.receipt["worker"] = {
            "running": self.worker.thread.is_alive(),
            "completed_browser_jobs": self.worker.completed_jobs,
            "last_error": self.worker.last_error,
        }
        private_json(self.run_dir / "receipt.json", self.receipt)


@contextmanager
def synthetic_preview(database_url, run_dir, *, disciplines=("computing",)):
    """Keep source policies, mock scope, schema and actual worker alive together."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not disciplines or len(set(disciplines)) != len(disciplines):
        raise ValueError("Select each supported synthetic discipline at most once")
    if not set(disciplines) <= {"computing", "accounting", "biotechnology"}:
        raise ValueError("Select a supported labelled synthetic discipline")
    receipt = {
        "is_synthetic": True,
        "provider_execution": "mocked",
        "actual_model": "claude-opus-5-synthetic-mock",
        "live_requests": 0,
        "observed_cost": None,
        "external_http": "blocked",
        "persistent_configuration": "not_read_or_modified",
        "process_processing_scope": "synthetic_mocks_only_with_provider_http_blocked",
        "status": "preparing",
        "public_deployment": False,
        "programmes": [],
    }
    preview = None
    try:
        with owned_database(database_url) as (database, ownership):
            receipt["database"] = ownership
            settings = preview_settings(database_url, run_dir)
            with preview_mocked_workers() as (worker_function, calls):
                reports = []
                for discipline in disciplines:
                    report = run_synthetic_system(
                        database,
                        settings,
                        workdir=run_dir / "inputs" / discipline,
                        course_count=6,
                        discipline=discipline,
                        fixture_namespace=discipline.upper(),
                        mode="live",
                        worker=worker_function,
                        include_replay=False,
                    )
                    reports.append(report)
                    private_json(run_dir / f"{discipline}.receipt.json", report)
                    receipt["programmes"].append(
                        {"discipline": discipline, **report["lineage"], **report["labels"]}
                    )
                credentials = issue_access(
                    run_dir, [report["labels"]["institution_id"] for report in reports]
                )
                scoped = settings.model_copy(
                    update={
                        "api_access_mode": "scoped",
                        "api_access_policy_path": run_dir / "access-policy.private.json",
                        "catalogue_write_token": None,
                        "analysis_write_token": None,
                    }
                )
                validate_access_configuration(scoped)
                background = BackgroundWorker(database, scoped, worker_function).start()
                preview = Preview(
                    create_app(settings=scoped, database=database),
                    database,
                    scoped,
                    run_dir,
                    reports,
                    credentials,
                    background,
                    receipt,
                )
                receipt["status"] = "ready"
                receipt["mock_calls"] = dict(calls)
                preview.save_receipt()
                try:
                    yield preview
                finally:
                    try:
                        background.close()
                    except RuntimeError:
                        ownership["cleanup_blocked"] = True
                        ownership["cleanup"] = "refused_worker_still_running"
                        receipt["status"] = "shutdown_blocked_worker_running"
                        raise
                    receipt["status"] = "stopped"
                    receipt["mock_calls"] = dict(calls)
                    preview.save_receipt()
    finally:
        (run_dir / "auth.private.json").unlink(missing_ok=True)
        if preview is None:
            receipt["status"] = "failed_before_ready"
        private_json(run_dir / "receipt.json", receipt)


def serve_preview(preview: Preview, *, host="127.0.0.1", port=8008):
    if host not in {"127.0.0.1", "::1"} or not 1 <= port <= 65535:
        raise ValueError(
            "Synthetic preview can bind only a literal loopback address and valid port"
        )
    server = uvicorn.Server(
        uvicorn.Config(preview.app, host=host, port=port, access_log=False, log_level="warning")
    )
    stopped = threading.Event()

    def monitor():
        announced = False
        while not stopped.wait(0.5):
            if server.started and not announced:
                announced = True
                preview.receipt["status"] = "ready"
                # Never print the raw credential or pass it as a CLI argument.
                print(
                    json.dumps(
                        {
                            "status": "ready",
                            "api_origin": preview.receipt["api_origin"],
                            "private_auth_file": str(preview.run_dir / "auth.private.json"),
                            "receipt_file": str(preview.run_dir / "receipt.json"),
                            "stop_file": str(preview.run_dir / "STOP"),
                            "provider_execution": "mocked",
                            "live_requests": 0,
                        }
                    ),
                    flush=True,
                )
            preview.save_receipt()
            if (preview.run_dir / "STOP").exists():
                server.should_exit = True
                return

    monitor_thread = threading.Thread(target=monitor, name="synthetic-preview-lifecycle")
    monitor_thread.start()
    try:
        preview.receipt["api_origin"] = (
            f"http://[{host}]:{port}" if host == "::1" else (f"http://{host}:{port}")
        )
        preview.receipt["status"] = "starting_api"
        preview.save_receipt()
        server.run()
    finally:
        stopped.set()
        monitor_thread.join(timeout=2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--port", type=int, default=8008)
    parser.add_argument("--state-dir", type=Path, default=ROOT / "data/local/phase8-preview")
    parser.add_argument(
        "--disciplines",
        nargs="+",
        default=["computing", "accounting", "biotechnology"],
        choices=("computing", "accounting", "biotechnology"),
    )
    args = parser.parse_args(argv)
    # Validate before any database operation or filesystem writes.
    validate_database_url(args.database_url)
    if not 1 <= args.port <= 65535:
        parser.error("Supply a valid loopback API port")
    parent = private_directory(args.state_dir)
    run_dir = Path(tempfile.mkdtemp(prefix="preview-", dir=parent))
    with synthetic_preview(
        args.database_url, run_dir, disciplines=tuple(args.disciplines)
    ) as preview:
        serve_preview(preview, port=args.port)


if __name__ == "__main__":
    main()
