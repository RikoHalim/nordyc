"""Transfer one fictional programme's committed results into a fresh owned schema.

This administration helper never calls a model, reads PDF bytes, starts a worker,
changes the source database, or imports into an existing schema. Credentials are
read only from a named environment variable and never included in the snapshot.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Numeric, Uuid, and_, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alembic.config import Config  # noqa: E402

import shiftos.models  # noqa: E402,F401
from alembic import command  # noqa: E402
from shiftos.api.routers.analysis import _access_state  # noqa: E402
from shiftos.core.config import Settings  # noqa: E402
from shiftos.db.base import Base, UTCDateTime  # noqa: E402
from shiftos.models import ActionPlanRun, AnalysisRun, CareerRun, CourseFinding  # noqa: E402
from shiftos.repositories import career, pathways  # noqa: E402
from shiftos.repositories.catalogue import digest  # noqa: E402
from shiftos.schemas.analysis import EvidencePacket  # noqa: E402
from shiftos.services.analysis.validation import validate_result  # noqa: E402
from shiftos.services.career.engine import validate_career_result  # noqa: E402
from shiftos.services.pathways.engine import validate_plan_result  # noqa: E402

FORMAT = "shiftos-programme-transfer-1"
HEAD = "0007_academic_action_plans"
OWNER_PREFIX = "SHIFTOS_PROGRAMME_TRANSFER:"
SOURCE_PREFIXES = ("SHIFTOS_PHASE8_SYNTHETIC_PREVIEW:", OWNER_PREFIX)
SCHEMA = re.compile(r"shiftos_(?:preview|transfer)_[0-9a-f]{32}\Z")
UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
PRIVATE_PATH = re.compile(
    r"(?:(?:^|[\s\"'])[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'])/(?:home|Users|tmp|var)/|data[\\/]local[\\/])"
)
SECRET_VALUE = re.compile(
    r"(?:postgres(?:ql)?(?:\+psycopg)?|mysql|sqlite)://|"
    r"\b(?:sk-ant-|sk-proj-|AIza)[A-Za-z0-9_-]{12,}|"
    r"[?&](?:api_key|apikey|access_token|token|secret|password)=",
    re.IGNORECASE,
)
SECRET_KEYS = {
    "api_key",
    "authorization",
    "access_token",
    "password",
    "session_secret",
    "database_url",
    "connection_string",
    "private_key",
    "pdf_bytes",
    "file_bytes",
}
OWNED = {
    "institutions",
    "programmes",
    "programme_revisions",
    "courses",
    "documents",
    "document_anchors",
    "jobs",
    "analysis_runs",
    "course_findings",
    "career_runs",
    "career_recommendations",
    "career_reviews",
    "action_plan_runs",
    "plan_recommendations",
    "action_plan_reviews",
}
REFERENCES = {
    "sources",
    "datasets",
    "dataset_versions",
    "evidence_references",
    "occupations",
    "skills",
    "occupation_skills",
    "occupational_tasks",
    "workforce_observations",
    "ai_impact_evidence",
    "academic_standards",
    "sdg_references",
}
TABLES = {name: Base.metadata.tables[name] for name in OWNED | REFERENCES}
MAX_ROWS = 5000
MAX_BYTES = 15_000_000


class TransferError(ValueError):
    """A safe refusal without connection strings, source prose or private paths."""


def _encode(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    if isinstance(value, (UUID, datetime, date, Decimal)):
        return str(value)
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise TransferError("Snapshot contains unsupported binary or object data")


def _uuids(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _uuids(key)
            yield from _uuids(item)
    elif isinstance(value, list):
        for item in value:
            yield from _uuids(item)
    elif isinstance(value, str):
        yield from (UUID(match) for match in UUID_PATTERN.findall(value))


def _safe(value):
    if isinstance(value, dict):
        for key, item in value.items():
            sensitive_key = key.casefold() in SECRET_KEYS or key.casefold().endswith(
                ("_api_key", "_password", "_secret", "_access_token")
            )
            if sensitive_key and item:
                raise TransferError("Snapshot contains a forbidden credential or file field")
            _safe(key)
            _safe(item)
    elif isinstance(value, list):
        for item in value:
            _safe(item)
    elif isinstance(value, str) and (PRIVATE_PATH.search(value) or SECRET_VALUE.search(value)):
        raise TransferError("Snapshot contains a private path or credential-like value")


def _scope(rows, programme_id):
    """Refuse cross-programme ancestry and real records except attributed UN standards."""
    programmes = rows.get("programmes", [])
    if len(programmes) != 1 or str(programmes[0]["id"]) != str(programme_id):
        raise TransferError("Snapshot must contain exactly the selected fictional programme")
    institution_id = str(programmes[0]["institution_id"])
    institutions = rows.get("institutions", [])
    if len(institutions) != 1 or str(institutions[0]["id"]) != institution_id:
        raise TransferError("Snapshot includes another institution")
    revisions = {str(row["id"]) for row in rows.get("programme_revisions", [])}
    for name, values in rows.items():
        if name not in TABLES:
            raise TransferError("Snapshot contains an unsupported table")
        for row in values:
            if set(row) != set(TABLES[name].c.keys()):
                raise TransferError("Snapshot columns do not match this application version")
            if name in OWNED and row.get("is_synthetic") is not True:
                raise TransferError("Only explicitly fictional programme records can transfer")
            if name in OWNED:
                if row.get("programme_id") and str(row["programme_id"]) != str(programme_id):
                    raise TransferError("Snapshot includes another programme")
                if row.get("institution_id") and str(row["institution_id"]) != institution_id:
                    raise TransferError("Snapshot includes another institution")
                if (
                    row.get("programme_revision_id")
                    and str(row["programme_revision_id"]) not in revisions
                ):
                    raise TransferError("Snapshot includes another revision")
            if name == "jobs" and row["status"] not in {"SUCCEEDED", "PARTIAL"}:
                raise TransferError("Only completed jobs can transfer; no worker replay is allowed")
            if (
                name in {"analysis_runs", "career_runs", "action_plan_runs"}
                and row["mode"] != "offline"
            ):
                raise TransferError("This helper transfers offline demonstrations only")
            if name == "sources" and not row["is_synthetic"]:
                if row["evidence_class"] != "published_standard" or row["publisher"] not in {
                    "United Nations",
                    "United Nations General Assembly",
                }:
                    raise TransferError(
                        "Real source transfer is limited to the attributed UN standard"
                    )
            if name == "datasets" and not row["is_synthetic"]:
                fictional_versions = [
                    version
                    for version in rows.get("dataset_versions", [])
                    if str(version["dataset_id"]) == str(row["id"])
                ]
                fictional_registry = (
                    row["registry_key"].startswith("SYNTHETIC-")
                    and fictional_versions
                    and all(version["is_synthetic"] for version in fictional_versions)
                )
                if row["registry_key"] != "F-UN-SDG-RES70-1" and not fictional_registry:
                    raise TransferError("A real dataset outside the admitted UN pack was selected")
            if name in REFERENCES and not row.get("is_synthetic", False):
                if name not in {
                    "sources",
                    "datasets",
                    "dataset_versions",
                    "evidence_references",
                    "sdg_references",
                }:
                    raise TransferError("Real occupational or curriculum evidence cannot transfer")


def _add(connection, rows, table, condition):
    found = connection.execute(select(table).where(condition)).mappings().all()
    for row in found:
        rows[table.name][str(row["id"])] = dict(row)
    if sum(map(len, rows.values())) > MAX_ROWS:
        raise TransferError("Selected programme exceeds the bounded transfer row limit")
    return found


def build_snapshot(connection, programme_id: UUID) -> dict:
    """Read explicit owned descendants, then only required parent/pointer closure."""
    programme_id = UUID(str(programme_id))
    rows = {name: {} for name in TABLES}
    p = _add(connection, rows, TABLES["programmes"], TABLES["programmes"].c.id == programme_id)
    if len(p) != 1 or p[0]["is_synthetic"] is not True:
        raise TransferError("Select an existing explicitly fictional programme")
    _add(
        connection,
        rows,
        TABLES["institutions"],
        TABLES["institutions"].c.id == p[0]["institution_id"],
    )
    for name in ("programme_revisions", "analysis_runs", "career_runs", "action_plan_runs"):
        _add(connection, rows, TABLES[name], TABLES[name].c.programme_id == programme_id)
    revisions = [UUID(key) for key in rows["programme_revisions"]]
    for name in (
        "courses",
        "documents",
        "jobs",
        "course_findings",
        "career_recommendations",
        "career_reviews",
        "plan_recommendations",
        "action_plan_reviews",
    ):
        _add(connection, rows, TABLES[name], TABLES[name].c.programme_revision_id.in_(revisions))
    # Upload/import jobs target the programme before a new revision exists.
    jobs = TABLES["jobs"]
    for job in connection.execute(
        select(jobs).where(jobs.c.institution_id == p[0]["institution_id"])
    ).mappings():
        if str(job["payload_json"].get("programme_id", "")) == str(programme_id):
            rows["jobs"][str(job["id"])] = dict(job)
    documents = [UUID(key) for key in rows["documents"]]
    _add(
        connection,
        rows,
        TABLES["document_anchors"],
        TABLES["document_anchors"].c.document_id.in_(documents),
    )
    seen = set()
    while True:
        before = sum(map(len, rows.values()))
        for name, values in list(rows.items()):
            table = TABLES[name]
            for row in list(values.values()):
                for constraint in table.foreign_key_constraints:
                    elements = list(constraint.elements)
                    if not elements or any(row[fk.parent.name] is None for fk in elements):
                        continue
                    parent = elements[0].column.table
                    if parent.name not in TABLES:
                        raise TransferError("Snapshot has an unsupported parent dependency")
                    condition = and_(*(fk.column == row[fk.parent.name] for fk in elements))
                    if not _add(connection, rows, parent, condition):
                        raise TransferError("Selected records have an unresolved parent dependency")
        encoded = _encode({name: list(values.values()) for name, values in rows.items()})
        ids = set(_uuids(encoded)) - seen
        seen.update(ids)
        if ids:
            for table in TABLES.values():
                _add(connection, rows, table, table.c.id.in_(ids))
        if sum(map(len, rows.values())) == before:
            break
    cited_documents = set()
    for name in ("career_runs", "action_plan_runs"):
        for row in rows[name].values():
            signatures = row["manifest_json"].get("source_signatures", {})
            cited_documents.update(
                key.split(":", 1)[1] for key in signatures if key.startswith("document:")
            )
    omitted = []
    for key, document in rows["documents"].items():
        if document["storage_path"]:
            if key in cited_documents:
                raise TransferError(
                    "A cited document retains private storage; exact safe transfer is blocked"
                )
            document["storage_path"] = None
            omitted.append({"table": "documents", "id": key, "field": "storage_path"})
    payload = {
        "format": FORMAT,
        "programme_id": str(programme_id),
        "migration_head": HEAD,
        "created_at": datetime.now(UTC).isoformat(),
        "omitted_storage": omitted,
        "rows": _encode(
            {
                name: sorted(values.values(), key=lambda row: str(row["id"]))
                for name, values in sorted(rows.items())
                if values
            }
        ),
    }
    payload["sha256"] = digest(payload)
    validate_snapshot(payload)
    return payload


def validate_snapshot(snapshot) -> None:
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "format",
        "programme_id",
        "migration_head",
        "created_at",
        "omitted_storage",
        "rows",
        "sha256",
    }:
        raise TransferError("Invalid snapshot envelope")
    if snapshot["format"] != FORMAT or snapshot["migration_head"] != HEAD:
        raise TransferError("Snapshot format or migration version is incompatible")
    if snapshot["sha256"] != digest({k: v for k, v in snapshot.items() if k != "sha256"}):
        raise TransferError("Snapshot integrity check failed")
    if len(json.dumps(snapshot).encode()) > MAX_BYTES:
        raise TransferError("Snapshot exceeds the bounded byte limit")
    rows = snapshot["rows"]
    if not isinstance(rows, dict) or sum(map(len, rows.values())) > MAX_ROWS:
        raise TransferError("Invalid snapshot row inventory")
    _scope(rows, UUID(snapshot["programme_id"]))
    for name, values in rows.items():
        if len({row["id"] for row in values}) != len(values):
            raise TransferError("Snapshot contains duplicate record IDs")
        if name == "documents" and any(row["storage_path"] for row in values):
            raise TransferError("Original file storage must not be transferred")
    _safe(snapshot)


def _decode(table, row):
    values = dict(row)
    for column in table.columns:
        value = values[column.name]
        if value is None:
            continue
        if isinstance(column.type, Uuid):
            values[column.name] = UUID(value)
        elif isinstance(column.type, (UTCDateTime, DateTime)):
            values[column.name] = datetime.fromisoformat(value)
        elif isinstance(column.type, Date):
            values[column.name] = date.fromisoformat(value)
        elif isinstance(column.type, Numeric):
            values[column.name] = Decimal(value)
    return values


def restore_rows(connection, snapshot) -> None:
    """Insert exact rows into an empty migrated schema; restore only cyclic pointers."""
    validate_snapshot(snapshot)
    for table in Base.metadata.tables.values():
        if connection.scalar(select(table.c.id).limit(1)) is not None:
            raise TransferError("Destination application schema must be empty")
    for table in Base.metadata.sorted_tables:
        for row in snapshot["rows"].get(table.name, []):
            values = _decode(table, row)
            if table.name == "programmes":
                values["active_revision_id"] = None
            if table.name == "courses":
                values["inventory_source_anchor_id"] = None
            connection.execute(table.insert().values(**values))
    for name, field in (
        ("programmes", "active_revision_id"),
        ("courses", "inventory_source_anchor_id"),
    ):
        table = TABLES[name]
        for row in snapshot["rows"].get(name, []):
            if row[field]:
                values = _decode(table, row)
                connection.execute(
                    table.update()
                    .where(table.c.id == values["id"])
                    .values(**{field: values[field], "updated_at": values["updated_at"]})
                )


def verify_restored(connection, snapshot) -> dict:
    """Validate canonical results and current source/privacy guards without replay."""
    settings = Settings(
        _env_file=None, analysis_permissions_path=ROOT / "data/analysis_permissions.json"
    )
    with Session(bind=connection) as session:
        pid = UUID(snapshot["programme_id"])
        phase4 = session.scalars(select(AnalysisRun).where(AnalysisRun.programme_id == pid)).all()
        careers = session.scalars(select(CareerRun).where(CareerRun.programme_id == pid)).all()
        plans = session.scalars(
            select(ActionPlanRun).where(ActionPlanRun.programme_id == pid)
        ).all()
        for run in phase4:
            packet = EvidencePacket.model_validate(run.manifest_json["packet"])
            findings = session.scalars(
                select(CourseFinding).where(CourseFinding.run_id == run.id)
            ).all()
            validate_result(
                {**run.summary_json, "courses": [row.result_json for row in findings]}, packet
            )
            if not _access_state(session, run, settings)[0]:
                raise TransferError("Transferred course findings require source revalidation")
        for run in careers:
            validate_career_result(run.result_json)
            if (
                digest(run.result_json) != run.fingerprint
                or not career.access_state(session, run, settings)[0]
            ):
                raise TransferError("Transferred career result requires source revalidation")
        for run in plans:
            validate_plan_result(run.result_json)
            if (
                digest(run.result_json) != run.fingerprint
                or not pathways.access_state(session, run, settings)[0]
            ):
                raise TransferError("Transferred action plan requires source revalidation")
    return {
        "status": "PASS",
        "programme_id": str(pid),
        "phase4_runs": len(phase4),
        "career_runs": len(careers),
        "plan_runs": len(plans),
        "live_requests": 0,
    }


def _engine(variable, *, allow_managed=False):
    try:
        url = make_url(os.environ[variable])
        if url.get_backend_name() != "postgresql" or not url.database or not url.host:
            raise ValueError
        if url.host not in {"127.0.0.1", "localhost", "::1"} and not allow_managed:
            raise TransferError("Managed PostgreSQL requires --allow-managed-database")
        return create_engine(
            url.set(drivername="postgresql+psycopg"),
            hide_parameters=True,
            connect_args={"connect_timeout": 10},
        )
    except (KeyError, ValueError):
        raise TransferError("Configure the named PostgreSQL environment variable") from None


def _local_file(path):
    result = Path(path).resolve()
    if not result.is_relative_to((ROOT / "data/local").resolve()):
        raise TransferError("Transfer files must remain inside ignored data/local")
    return result


def export_programme(engine, source_schema, programme_id, output):
    if not SCHEMA.fullmatch(source_schema):
        raise TransferError("Select an explicitly owned preview or transfer source schema")
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            marker = connection.scalar(
                text(
                    "SELECT obj_description(oid,'pg_namespace') "
                    "FROM pg_namespace WHERE nspname=:schema"
                ),
                {"schema": source_schema},
            )
            if not marker or not marker.startswith(SOURCE_PREFIXES):
                raise TransferError("Source schema has no recognised ownership marker")
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{source_schema}"')
            if connection.scalar(text("SELECT version_num FROM alembic_version")) != HEAD:
                raise TransferError("Source migration version is incompatible")
            snapshot = build_snapshot(connection, UUID(programme_id))
            verify_restored(connection, snapshot)
    path = _local_file(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, sort_keys=True)
    if os.name != "nt":
        path.chmod(0o600)
    return {
        "status": "EXPORTED",
        "programme_id": snapshot["programme_id"],
        "sha256": snapshot["sha256"],
        "row_count": sum(map(len, snapshot["rows"].values())),
        "omitted_original_files": len(snapshot["omitted_storage"]),
        "live_requests": 0,
    }


def import_programme(engine, input_path):
    path = _local_file(input_path)
    if path.stat().st_size > MAX_BYTES:
        raise TransferError("Snapshot exceeds the bounded byte limit")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    schema, marker = "shiftos_transfer_" + uuid4().hex, OWNER_PREFIX + uuid4().hex
    with engine.begin() as connection:
        if connection.scalar(
            text("SELECT 1 FROM pg_namespace WHERE nspname=:schema"), {"schema": schema}
        ):
            raise TransferError("Destination schema already exists")
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        connection.exec_driver_sql(f"COMMENT ON SCHEMA \"{schema}\" IS '{marker}'")
        connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "alembic"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        restore_rows(connection, snapshot)
        result = verify_restored(connection, snapshot)
    return {
        **result,
        "schema": schema,
        "owner_marker": marker,
        "snapshot_sha256": snapshot["sha256"],
        "original_files_transferred": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("export", "import"))
    parser.add_argument(
        "--database-url-env",
        required=True,
        help="Environment-variable name, never the connection string",
    )
    parser.add_argument("--allow-managed-database", action="store_true")
    parser.add_argument("--source-schema")
    parser.add_argument("--programme")
    parser.add_argument("--file", required=True, type=Path)
    args = parser.parse_args(argv)
    engine = None
    try:
        engine = _engine(args.database_url_env, allow_managed=args.allow_managed_database)
        if args.operation == "export":
            if not args.source_schema or not args.programme:
                raise TransferError("Export requires --source-schema and --programme")
            result = export_programme(engine, args.source_schema, args.programme, args.file)
        else:
            result = import_programme(engine, args.file)
        print(json.dumps(result))
        return 0
    except (TransferError, OSError, ValueError):
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": (
                        "Transfer refused; verify scope, ownership, permissions and configuration."
                    ),
                }
            )
        )
        return 1
    except Exception:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": "Database transfer failed safely; source records remain unchanged.",
                }
            )
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
