"""Bounded acceptance driver for the real FastAPI, CLI worker and PostgreSQL.

prepare and rehearse never contact a model or research service. live requires a
separately approved budget and reserves an on-disk receipt before queuing work.
No provider is mocked during live execution. Credentials remain in Replit.
"""

import argparse
import contextlib
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from phase42_database import CASE, CLUSTER, NAME, ROOT, URL, prepare

sys.path.insert(0, str(ROOT / "src"))
OUTPUT_TOKENS = 6144
REQUEST_BYTES = 24576
API_PORT = 18542
FIELDS = (
    "foundational_relevance",
    "ai_transformation",
    "workforce_alignment",
    "curriculum_currency",
    "future_resilience",
)


def identity(name):
    return uuid5(NAMESPACE_URL, "https://example.invalid/shiftos/phase42-e2e-v1/" + name)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def configure():
    """Explicit isolated runtime settings; do not edit .env or shared configuration."""
    os.environ.update(
        DATABASE_URL=URL,
        APP_ENV="development",
        ANALYSIS_MODEL_PROVIDER="replit_claude",
        CLAUDE_ENABLED="true",
        CLAUDE_MODEL="claude-opus-5",
        GEMINI_ENABLED="false",
        ANALYSIS_GEMINI_FALLBACK_ENABLED="false",
        RESEARCH_ENABLED="false",
        ANALYSIS_EXTERNAL_PROCESSING_ALLOWED="false",
        ANALYSIS_PROVIDER_MAX_ATTEMPTS="1",
        ANALYSIS_VALIDATION_MAX_ATTEMPTS="1",
        ANALYSIS_PROVIDER_TIMEOUT_SECONDS="60",
        ANALYSIS_PROVIDER_MAX_REQUEST_BYTES=str(REQUEST_BYTES),
        CLAUDE_MAX_OUTPUT_TOKENS=str(OUTPUT_TOKENS),
        ANALYSIS_MAX_COURSES="2",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONUNBUFFERED="1",
    )
    for name in ("TEST_DATABASE_URL", "GEMINI_API_KEY", "BRAVE_SEARCH_API_KEY"):
        os.environ.pop(name, None)
    token_file = CASE / "api-token.private"
    if not token_file.exists():
        with token_file.open("x") as file:
            file.write(secrets.token_urlsafe(32))
        token_file.chmod(0o600)
    os.environ["ANALYSIS_WRITE_TOKEN"] = token_file.read_text()


def settings():
    from shiftos.core.config import Settings

    return Settings(_env_file=None)


def migrate_and_seed():
    from alembic.config import Config
    from sqlalchemy import text

    from alembic import command
    from shiftos.core.enums import EvidenceClass
    from shiftos.db.session import create_database
    from shiftos.models import (
        Course,
        Dataset,
        DatasetVersion,
        EvidenceReference,
        Institution,
        Programme,
        ProgrammeRevision,
        Skill,
        Source,
    )
    from shiftos.services.analysis.claude_verification import _synthetic_packet

    database = create_database(URL)
    with database.engine.connect() as conn:
        assert conn.execute(text("SHOW data_directory")).scalar_one() == str(CLUSTER)
        assert conn.execute(text("SELECT current_database()")).scalar_one() == NAME
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")
    policy = json.loads((ROOT / "data/analysis_permissions.json").read_text())
    rule = policy["sources"]["C-ESCO-V103"]
    assert all(
        rule[key] is True
        for key in ("internal_analysis_allowed", "external_model_allowed", "excerpt_output_allowed")
    )
    pointer = _synthetic_packet({"sha256": "0" * 64}).references[0]
    with database.session_factory() as session:
        if session.get(Institution, identity("institution")) is None:
            session.add(
                Institution(
                    id=identity("institution"),
                    name="SYNTHETIC Phase 4.2 University",
                    is_synthetic=True,
                )
            )
            session.flush()
            session.add(
                Programme(
                    id=identity("programme"),
                    institution_id=identity("institution"),
                    name="SYNTHETIC Bachelor of Water Engineering",
                    discipline_key="engineering",
                    is_synthetic=True,
                )
            )
            session.flush()
            session.add(
                ProgrammeRevision(
                    id=identity("revision"),
                    programme_id=identity("programme"),
                    version_label="synthetic-phase42-e2e-v1",
                    is_synthetic=True,
                )
            )
            session.flush()
            session.get(Programme, identity("programme")).active_revision_id = identity("revision")
            for key, name in (
                ("course-irrigation", "SYNTHETIC Irrigation Systems"),
                ("course-ethics", "SYNTHETIC Engineering Ethics"),
            ):
                session.add(
                    Course(
                        id=identity(key),
                        programme_revision_id=identity("revision"),
                        course_name=name,
                        year=1,
                        is_synthetic=True,
                    )
                )
            session.add(
                Source(
                    id=pointer.source_id,
                    publisher=pointer.publisher,
                    title=pointer.title,
                    url=pointer.source_url,
                    collected_at=pointer.retrieved_at,
                    evidence_class=EvidenceClass.SYNTHETIC_DEMO,
                    is_synthetic=True,
                    license_status="permitted_attributed_ESCO_verification_copy",
                )
            )
            dataset = Dataset(
                registry_key="C-ESCO-V103",
                name="ESCO synthetic verification copy",
                category="occupation_benchmark",
                is_synthetic=True,
            )
            session.add(dataset)
            session.flush()
            session.add(
                DatasetVersion(
                    id=pointer.version_id,
                    dataset_id=dataset.id,
                    source_id=pointer.source_id,
                    content_sha256=hashlib.sha256(pointer.excerpt.encode()).hexdigest(),
                    parser_version="phase42-attributed-verification-copy-1",
                    retrieved_at=pointer.retrieved_at,
                    artifact_url=pointer.facts["source_artifact_url"],
                    is_synthetic=True,
                    metadata_json={"analysis_permissions": rule, **pointer.facts},
                )
            )
            session.flush()
            session.add(
                EvidenceReference(
                    id=pointer.evidence_reference_id,
                    version_id=pointer.version_id,
                    locator=pointer.locator,
                    excerpt=pointer.excerpt,
                    review_status="reviewed",
                    is_synthetic=True,
                    metadata_json={"analysis_permissions": rule, **pointer.facts},
                )
            )
            session.flush()
            session.add(
                Skill(
                    id=pointer.record_id,
                    version_id=pointer.version_id,
                    evidence_id=pointer.evidence_reference_id,
                    external_id=pointer.source_url,
                    taxonomy="ESCO:v1.0.3",
                    label=pointer.facts["original_label"],
                    description=pointer.excerpt,
                    is_synthetic=True,
                    metadata_json={"analysis_permissions": rule, **pointer.facts},
                )
            )
            session.commit()
    database.engine.dispose()


def preflight():
    from pydantic import SecretStr

    from shiftos.db.session import create_database
    from shiftos.schemas.analysis import ProgrammeResult
    from shiftos.services.analysis.claude_verification import inspect_claude_configuration
    from shiftos.services.analysis.orchestrator import _batch_packet, _permissions, _retrieve
    from shiftos.services.analysis.providers import ClaudeProvider

    config = settings()
    policy, _ = _permissions(config)
    database = create_database(URL)
    packet = _retrieve(database, identity("revision"), datetime.now(UTC), policy)
    database.engine.dispose()
    assert len(packet.courses) == 2
    admitted = [ref for ref in packet.references if ref.model_eligible]
    assert admitted and all(ref.dataset_key == "C-ESCO-V103" for ref in admitted)
    ready = inspect_claude_configuration(config)
    assert ready["blockers"] == ["external_processing_not_approved"], ready["blockers"]
    measured = {}

    def measure(request):
        measured["request_bytes"] = len(request.content)
        return httpx.Response(
            200,
            json={
                "model": "claude-opus-5",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "{}"}],
                "usage": {},
            },
        )

    fake = config.model_copy(
        update={
            "analysis_external_processing_allowed": True,
            "replit_anthropic_api_key": SecretStr("SYNTHETIC-PREFLIGHT-NO-CREDENTIAL"),
            "replit_anthropic_base_url": "https://synthetic.invalid",
        }
    )
    with httpx.Client(transport=httpx.MockTransport(measure)) as client:
        ClaudeProvider(fake, client).generate(
            _batch_packet(packet, packet.courses).model_dump(mode="json"),
            ProgrammeResult.model_json_schema(),
        )
    assert measured["request_bytes"] <= REQUEST_BYTES
    result = {
        "status": "ready_for_separate_live_approval",
        "model_requests": 0,
        "course_count": len(packet.courses),
        "admitted_reference_count": len(admitted),
        "request_bytes_measured_offline": measured["request_bytes"],
        "request_byte_cap": REQUEST_BYTES,
        "output_token_cap": OUTPUT_TOKENS,
        "transport_attempt_cap": 1,
        "validation_attempt_cap": 1,
        "timeout_seconds": 60,
        "gemini_enabled": False,
        "research_enabled": False,
        "external_processing": False,
        "evidence_gaps": packet.gaps,
        "limitations": [
            "No admitted academic-standard or workforce observations in this narrow fixture",
            "ESCO legacy benchmark is not taught content or Malaysian demand",
            "One course has no matching evidence; every course must still be returned",
        ],
    }
    write_json(CASE / "preflight.json", result)
    return result


@contextlib.contextmanager
def api_server():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", API_PORT))
    with (CASE / "api.log").open("w") as log:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "shiftos.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(API_PORT),
                "--no-access-log",
            ],
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{API_PORT}", trust_env=False) as client:
                for _ in range(60):
                    if proc.poll() is not None:
                        raise RuntimeError("API process exited; inspect isolated log")
                    try:
                        if client.get("/health/ready").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("API readiness timeout")
                yield client
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def workflow(live, budget):
    from sqlalchemy import select

    from shiftos.db.session import create_database
    from shiftos.models import AnalysisRun, CourseFinding, Job
    from shiftos.services.analysis.orchestrator import _permissions, _retrieve
    from shiftos.services.analysis.validation import validate_result

    config = settings()
    if live:
        assert budget is not None and 0.5 <= budget <= 1, "Explicit bounded approval required"
    name = "live" if live else "rehearsal"
    # No repeat live calls even if the process or report export fails after a request.
    receipt = CASE / f"{name}-attempt.json"
    with receipt.open("x" if live else "w") as file:
        json.dump(
            {
                "status": "reserved",
                "live": live,
                "budget_usd": budget,
                "started_at": datetime.now(UTC).isoformat(),
            },
            file,
        )
    report = {
        "status": "failed",
        "live": live,
        "model_requests": 0,
        "observed_cost": None,
        "observed_cost_status": "not_reported",
    }
    try:
        with api_server() as client:
            path = f"/api/v1/programmes/{identity('programme')}/analyses"
            body = {
                "mode": "live" if live else "offline",
                "research": False,
                "idempotency_key": "phase42-" + name + "-v1",
            }
            assert client.post(path, json=body).status_code == 401
            headers = {"X-Analysis-Token": config.analysis_write_token.get_secret_value()}
            submitted = client.post(path, json=body, headers=headers)
            assert submitted.status_code == 202
            run = submitted.json()
            assert run["status"] == "QUEUED"
            assert run["programme_revision_id"] == str(identity("revision"))
            report.update(analysis_id=run["id"], job_id=run["job_id"], submission_http_status=202)
            worker_env = os.environ.copy()
            worker_env["ANALYSIS_EXTERNAL_PROCESSING_ALLOWED"] = "true" if live else "false"
            began = time.monotonic()
            with (CASE / f"{name}-worker.log").open("w") as log:
                worker = subprocess.run(
                    [sys.executable, "-m", "shiftos.cli", "worker", "--once"],
                    cwd=ROOT,
                    env=worker_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=100,
                )
            report["worker_elapsed_ms"] = round((time.monotonic() - began) * 1000, 3)
            assert worker.returncode == 0
            target = f"/api/v1/analyses/{run['id']}"
            assert client.get(target).status_code == 401
            assert client.get(target, headers={"X-Analysis-Token": "wrong"}).status_code == 401
            response = client.get(target, headers=headers)
            assert response.status_code == 200
            result = response.json()
            courses_response = client.get(target + "/courses", headers=headers)
            assert courses_response.status_code == 200
            rows = courses_response.json()
            assert rows["total"] == 2 and len(rows["items"]) == 2
            # Independent engine/connection proves committed PostgreSQL state.
            database = create_database(URL)
            with database.session_factory() as session:
                stored = session.get(AnalysisRun, UUID(run["id"]))
                findings = session.scalars(
                    select(CourseFinding).where(CourseFinding.run_id == stored.id)
                ).all()
                assert len(findings) == 2
                job = session.get(Job, stored.job_id)
                assert job.completed_at and job.started_at
                assert job.status.value == result["status"]
                assert result["started_at"] and result["completed_at"]
                assert stored.summary_json == result["summary_json"]
                assert {str(row.course_id) for row in findings} == {
                    item["course_id"] for item in rows["items"]
                }
                policy, _ = _permissions(config)
                packet = _retrieve(database, identity("revision"), datetime.now(UTC), policy)
                validated = validate_result(
                    {**stored.summary_json, "courses": [row.result_json for row in findings]},
                    packet,
                )
                processing = stored.manifest_json["model_processing"]
                report.update(
                    status=result["status"],
                    model_processing=processing,
                    actual_model=stored.model_name,
                    course_count=len(findings),
                    model_requests=processing.get("request_count", 0),
                    citations=sum(
                        len(getattr(row, dimension).citations)
                        for row in validated.courses
                        for dimension in FIELDS
                    ),
                    independent_database_read=True,
                    protected_api_read=True,
                    result_mode=validated.result_mode,
                    source_reference_count=len(packet.references),
                    schema_validated=True,
                    grounding_validated=True,
                    all_courses_accounted_for=True,
                    started_at=job.started_at.isoformat(),
                    completed_at=job.completed_at.isoformat(),
                    programme_summary=validated.summary.model_dump(mode="json"),
                    course_results=[
                        {
                            "course_id": str(row.course_id),
                            "course_name": row.course_name,
                            "needs_syllabus_confirmation": row.needs_syllabus_confirmation,
                            "dimension_statuses": {
                                name: getattr(row, name).status for name in FIELDS
                            },
                        }
                        for row in validated.courses
                    ],
                )
                assert all(
                    not row.is_final_curriculum_verdict and row.needs_syllabus_confirmation
                    for row in validated.courses
                )
                unmatched = next(
                    row for row in validated.courses if row.course_id == identity("course-ethics")
                )
                assert all(
                    getattr(unmatched, name).status == "insufficient_evidence"
                    and not getattr(unmatched, name).citations
                    for name in FIELDS
                )
                if live:
                    assert stored.model_name == "claude-opus-5"
                    assert processing["request_count"] == 1 and processing["calls"] == 1
                    assert processing["validated_model_courses"] == 2
                    assert processing["fallback_courses"] == 0 and not processing["fallbacks"]
                    assert report["citations"] > 0 and validated.result_mode == "live_model"
                else:
                    assert processing["calls"] == 0 and stored.model_name is None
                assert result["status"] == "SUCCEEDED"
                assert not result["needs_evidence_revalidation"]
            database.engine.dispose()
            report["status"] = "live_e2e_verified" if live else "offline_e2e_rehearsal_passed"
        return report
    finally:
        write_json(receipt, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "rehearse", "live"])
    parser.add_argument("--approved-budget-usd", type=float)
    args = parser.parse_args()
    if args.action == "live" and args.approved_budget_usd is None:
        parser.error("Live execution requires prior explicit owner approval and a spending limit")
    prepare()
    configure()
    migrate_and_seed()
    ready = preflight()
    report = (
        ready
        if args.action == "prepare"
        else workflow(args.action == "live", args.approved_budget_usd)
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "verification_failed",
                    "error_type": type(exc).__name__,
                    "detail": "Inspect the isolated local report; no automatic retry",
                }
            )
        )
        raise SystemExit(1) from None
