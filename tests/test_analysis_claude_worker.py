"""Synthetic Claude/Gemini responses only; no actual model, billing or research calls."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from test_analysis_worker import synthetic_programme
from test_migrations import migration_database  # noqa: F401 - isolated PostgreSQL fixture

from alembic import command
from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import AnalysisRun, CourseFinding, Job
from shiftos.repositories.analysis import enqueue_analysis
from shiftos.schemas.analysis import AnalysisRequest, EvidencePacket
from shiftos.services.analysis import orchestrator
from shiftos.services.analysis.providers import ProviderError
from shiftos.services.analysis.validation import offline_result
from shiftos.services.ingestion.worker import run_once


@pytest.fixture(autouse=True)
def forbid_external_http(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Synthetic provider tests cannot make external HTTP requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def synthetic_settings(tmp_path, **changes):
    permission_path = tmp_path / "claude-worker-permissions.synthetic.json"
    permission_path.write_text(
        json.dumps({"version": "synthetic-claude-worker-1", "sources": {}}), encoding="utf-8"
    )
    values = {
        "_env_file": None,
        "app_env": "test",
        "analysis_permissions_path": permission_path,
        "analysis_write_token": "synthetic-claude-worker-access",
        "analysis_external_processing_allowed": True,
        "claude_enabled": True,
        "claude_model": "claude-opus-5",
        "gemini_enabled": True,
        "gemini_model": "gemini-synthetic-test",
        "analysis_gemini_fallback_enabled": False,
        "research_enabled": False,
    }
    return Settings(**(values | changes))


def synthetic_models(
    monkeypatch, *, claude="valid", gemini="valid", extra_metadata=None, on_return=None
):
    """Usage/model labels are deliberately fictional mock observations, not actual billing."""
    calls = []

    def provider(provider_name, outcome):
        class SyntheticProvider:
            def __init__(self, settings):
                self.deadline = None
                self.settings = settings
                self.last_response_metadata = {}

            def generate(self, payload, schema):
                calls.append(provider_name)
                requested = (
                    self.settings.claude_model
                    if provider_name == "replit_claude"
                    else self.settings.gemini_model
                )
                self.last_response_metadata = {
                    "provider": provider_name,
                    "requested_model": requested,
                    "actual_model": None,
                    "usage": {},
                    "request_count": 0,
                    "observed_cost": None,
                }
                if isinstance(outcome, ProviderError):
                    raise outcome
                self.last_response_metadata.update(
                    actual_model=f"synthetic-{provider_name}-response-model",
                    usage={"input_tokens": 17, "output_tokens": 13},
                    request_count=1,
                )
                self.last_response_metadata.update(extra_metadata or {})
                if outcome == "invalid_schema":
                    return {"fabricated_score": 98, "courses": []}
                packet = EvidencePacket.model_validate(
                    {key: value for key, value in payload.items() if key != "validation_feedback"}
                )
                result = offline_result(packet).model_dump(mode="json")
                result["result_mode"] = "live_model"
                if outcome == "invalid_citation":
                    result["courses"][0]["foundational_relevance"]["citations"] = [
                        {
                            "reference_id": "synthetic:unassociated-source",
                            "quote": "Synthetic unsupported source claim for rejection.",
                            "scope": "academic_benchmark",
                        }
                    ]
                if on_return is not None:
                    on_return(payload)
                return result

        return SyntheticProvider

    monkeypatch.setattr(orchestrator, "ReplitClaudeProvider", provider("replit_claude", claude))
    monkeypatch.setattr(orchestrator, "GeminiProvider", provider("gemini", gemini))
    return calls


def process_live(database, session, settings):
    programme = synthetic_programme(session)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(mode="live", research=False))
    assert run_once(database, settings) == run.job_id
    session.expire_all()
    return session.get(AnalysisRun, run.id), session.get(Job, run.job_id)


def assert_complete_synthetic_findings(session, run):
    findings = session.scalars(select(CourseFinding).where(CourseFinding.run_id == run.id)).all()
    assert len(findings) == 3
    assert all(row.is_synthetic for row in findings)
    assert all(row.result_json["is_final_curriculum_verdict"] is False for row in findings)
    assert all(row.result_json["needs_syllabus_confirmation"] is True for row in findings)


@pytest.mark.parametrize("selected", ["gemini", "replit_claude"])
def test_default_gemini_and_explicit_claude_selection_preserve_actual_identity(
    database, session, monkeypatch, tmp_path, selected
):
    changes = {"analysis_model_provider": selected} if selected == "replit_claude" else {}
    settings = synthetic_settings(tmp_path, **changes)
    calls = synthetic_models(monkeypatch)
    run, job = process_live(database, session, settings)
    assert calls == [selected]
    assert job.status == JobStatus.SUCCEEDED, job.error
    assert run.summary_json["result_mode"] == "live_model"
    assert run.manifest_json["model_provider"] == (
        "gemini_direct" if selected == "gemini" else selected
    )
    assert run.manifest_json["model_configured"] == (
        settings.gemini_model if selected == "gemini" else settings.claude_model
    )
    assert run.model_name == f"synthetic-{selected}-response-model"
    processing = run.manifest_json["model_processing"]
    assert processing["calls"] == 1 and processing["fallbacks"] == []
    response = processing["responses"][0]
    assert response["status"] == "returned"
    assert response["actual_model"] == run.model_name
    assert response["usage"] == {"input_tokens": 17, "output_tokens": 13}
    assert response["observed_cost"] is None
    assert response["request_count"] == 1
    assert_complete_synthetic_findings(session, run)


def test_operational_claude_failure_does_not_silently_substitute_gemini(
    database, session, monkeypatch, tmp_path
):
    calls = synthetic_models(monkeypatch, claude=ProviderError("provider_unavailable"))
    run, job = process_live(
        database, session, synthetic_settings(tmp_path, analysis_model_provider="replit_claude")
    )
    assert calls == ["replit_claude"]
    assert job.status == JobStatus.PARTIAL
    assert run.summary_json["result_mode"] == "offline_synthetic"
    assert run.model_name is None
    processing = run.manifest_json["model_processing"]
    assert processing["fallbacks"] == []
    assert processing["responses"][0]["status"] == "provider_error"
    assert processing["responses"][0]["error_code"] == "provider_unavailable"
    assert processing["responses"][0]["request_count"] == 0
    assert_complete_synthetic_findings(session, run)


def test_single_validation_attempt_never_makes_a_paid_repair(
    database, session, monkeypatch, tmp_path
):
    calls = synthetic_models(monkeypatch, claude="invalid_schema")
    run, job = process_live(
        database,
        session,
        synthetic_settings(
            tmp_path,
            analysis_model_provider="replit_claude",
            analysis_validation_max_attempts=1,
        ),
    )
    assert calls == ["replit_claude"]
    assert job.status == JobStatus.PARTIAL
    assert run.manifest_json["model_processing"]["request_count"] == 1
    assert_complete_synthetic_findings(session, run)


def test_safe_http_status_and_latency_are_persisted(database, session, monkeypatch, tmp_path):
    synthetic_models(monkeypatch, extra_metadata={"http_status": 200, "duration_ms": 123.5})
    run, job = process_live(
        database,
        session,
        synthetic_settings(tmp_path, analysis_model_provider="replit_claude"),
    )
    assert job.status == JobStatus.SUCCEEDED
    response = run.manifest_json["model_processing"]["responses"][0]
    assert response["http_status"] == 200 and response["duration_ms"] == 123.5


def test_fallback_flag_never_switches_default_gemini_to_claude(
    database, session, monkeypatch, tmp_path
):
    calls = synthetic_models(monkeypatch, gemini=ProviderError("provider_unavailable"))
    run, job = process_live(
        database,
        session,
        synthetic_settings(tmp_path, analysis_gemini_fallback_enabled=True),
    )
    assert calls == ["gemini"]
    assert job.status == JobStatus.PARTIAL
    assert run.manifest_json["model_processing"]["fallbacks"] == []
    assert_complete_synthetic_findings(session, run)


def test_failed_opt_in_gemini_fallback_abstains_without_further_provider_switches(
    database, session, monkeypatch, tmp_path
):
    calls = synthetic_models(
        monkeypatch,
        claude=ProviderError("provider_unavailable"),
        gemini=ProviderError("provider_authentication_failed"),
    )
    run, job = process_live(
        database,
        session,
        synthetic_settings(
            tmp_path,
            analysis_model_provider="replit_claude",
            analysis_gemini_fallback_enabled=True,
        ),
    )
    assert calls == ["replit_claude", "gemini"]
    assert job.status == JobStatus.PARTIAL
    assert run.summary_json["result_mode"] == "offline_synthetic"
    assert run.model_name is None
    responses = run.manifest_json["model_processing"]["responses"]
    assert len(responses) == 2 and all(row["status"] == "provider_error" for row in responses)
    assert_complete_synthetic_findings(session, run)


@pytest.mark.parametrize(
    "code", ["provider_unavailable", "provider_deadline", "provider_rate_limited"]
)
def test_explicit_gemini_fallback_is_limited_to_operational_claude_failures(
    database, session, monkeypatch, tmp_path, code
):
    calls = synthetic_models(monkeypatch, claude=ProviderError(code))
    run, job = process_live(
        database,
        session,
        synthetic_settings(
            tmp_path,
            analysis_model_provider="replit_claude",
            analysis_gemini_fallback_enabled=True,
        ),
    )
    assert calls == ["replit_claude", "gemini"]
    assert job.status == JobStatus.PARTIAL
    assert run.summary_json["result_mode"] == "live_model"
    assert run.manifest_json["model_provider"] == "replit_claude"
    assert run.manifest_json["model_configured"] == "claude-opus-5"
    assert run.model_name == "synthetic-gemini-response-model"
    processing = run.manifest_json["model_processing"]
    assert processing["fallbacks"] == [
        {"from_provider": "replit_claude", "to_provider": "gemini_direct", "reason": code}
    ]
    assert [row["status"] for row in processing["responses"]] == ["provider_error", "returned"]
    assert processing["responses"][1]["usage"] == {"input_tokens": 17, "output_tokens": 13}
    assert_complete_synthetic_findings(session, run)


@pytest.mark.parametrize(
    "code",
    [
        "provider_authentication_failed",
        "external_processing_not_approved",
        "provider_response_invalid",
        "provider_redirect_rejected",
        "model_disabled",
        "model_not_configured",
    ],
)
def test_opt_in_never_bypasses_authentication_privacy_or_protocol_failure(
    database, session, monkeypatch, tmp_path, code
):
    calls = synthetic_models(monkeypatch, claude=ProviderError(code))
    run, job = process_live(
        database,
        session,
        synthetic_settings(
            tmp_path,
            analysis_model_provider="replit_claude",
            analysis_gemini_fallback_enabled=True,
        ),
    )
    assert calls == ["replit_claude"]
    assert job.status == JobStatus.PARTIAL
    assert run.manifest_json["model_processing"]["fallbacks"] == []
    assert run.summary_json["result_mode"] != "live_model"
    assert_complete_synthetic_findings(session, run)


@pytest.mark.parametrize("outcome", ["invalid_schema", "invalid_citation"])
def test_rejected_output_repairs_same_provider_and_preserves_usage_without_fallback(
    database, session, monkeypatch, tmp_path, outcome
):
    calls = synthetic_models(monkeypatch, claude=outcome)
    run, job = process_live(
        database,
        session,
        synthetic_settings(
            tmp_path,
            analysis_model_provider="replit_claude",
            analysis_gemini_fallback_enabled=True,
        ),
    )
    assert calls == ["replit_claude", "replit_claude"]
    assert job.status == JobStatus.PARTIAL
    processing = run.manifest_json["model_processing"]
    assert processing["fallbacks"] == []
    assert [row["status"] for row in processing["responses"]] == [
        "validation_rejected",
        "validation_rejected",
    ]
    assert all(row["usage"]["output_tokens"] == 13 for row in processing["responses"])
    assert "fabricated_score" not in str(run.summary_json)
    assert "synthetic:unassociated-source" not in str(run.summary_json)
    assert_complete_synthetic_findings(session, run)


def test_provider_usage_metadata_is_sanitized_before_persistence_and_protected_reads(
    database, session, monkeypatch, tmp_path
):
    settings = synthetic_settings(tmp_path, analysis_model_provider="replit_claude")
    synthetic_models(
        monkeypatch,
        extra_metadata={
            "api_key": "synthetic-secret-must-not-persist",
            "headers": {"Authorization": "synthetic-secret-must-not-persist"},
            "upstream_body": "synthetic-secret-must-not-persist",
        },
    )
    run, job = process_live(database, session, settings)
    assert job.status == JobStatus.SUCCEEDED
    assert "synthetic-secret-must-not-persist" not in json.dumps(run.manifest_json)
    with TestClient(create_app(settings=settings, database=database)) as client:
        path = f"/api/v1/analyses/{run.id}"
        assert client.get(path).status_code == 401
        response = client.get(path, headers={"X-Analysis-Token": "synthetic-claude-worker-access"})
        assert response.status_code == 200, response.text
        metadata = response.json()["manifest_json"]["model_processing"]["responses"][0]
        assert metadata["usage"] == {"input_tokens": 17, "output_tokens": 13}
        assert metadata["actual_model"] == "synthetic-replit_claude-response-model"
        assert metadata["observed_cost"] is None
        assert "synthetic-secret-must-not-persist" not in response.text


def test_offline_synthetic_run_never_invokes_selected_claude_or_gemini_fallback(
    database, session, monkeypatch, tmp_path
):
    calls = synthetic_models(monkeypatch)
    settings = synthetic_settings(
        tmp_path, analysis_model_provider="replit_claude", analysis_gemini_fallback_enabled=True
    )
    programme = synthetic_programme(session)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(mode="offline"))
    assert run_once(database, settings) == run.job_id
    session.expire_all()
    run = session.get(AnalysisRun, run.id)
    assert calls == []
    assert run.model_name is None
    assert run.summary_json["result_mode"] == "offline_synthetic"
    assert run.manifest_json["model_processing"]["calls"] == 0
    assert_complete_synthetic_findings(session, run)


def test_policy_change_after_response_retains_safe_usage_without_publishing_findings_or_text(
    database, session, monkeypatch, tmp_path
):
    from test_analysis_retrieval import make_evidence

    settings = synthetic_settings(tmp_path, analysis_model_provider="replit_claude")
    _, _, reference, _, _ = make_evidence(session, kind="occupation", discipline="computing")
    withheld_text = "Synthetic source text must be withheld after publication permission changes."
    reference.excerpt = withheld_text
    session.commit()

    def revoke_after_response(payload):
        assert withheld_text in json.dumps(payload)
        settings.analysis_permissions_path.write_text(
            json.dumps({"version": "synthetic-policy-changed-during-generation", "sources": {}}),
            encoding="utf-8",
        )

    calls = synthetic_models(
        monkeypatch,
        on_return=revoke_after_response,
        extra_metadata={"api_key": "synthetic-secret-must-not-persist"},
    )
    run, job = process_live(database, session, settings)
    assert calls == ["replit_claude"]
    assert job.status == JobStatus.FAILED and "ANALYSIS_POLICY_CHANGED" in job.error
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 0
    assert run.summary_json == {}
    assert "packet" not in run.manifest_json
    assert run.manifest_json["publication_status"] == "failed"
    assert run.manifest_json["model_provider"] == "replit_claude"
    assert run.manifest_json["model_configured"] == "claude-opus-5"
    assert run.model_name == "synthetic-replit_claude-response-model"
    audit = run.manifest_json["model_processing"]
    assert audit == job.result_json["model_processing"]
    assert audit["responses"][0]["usage"] == {"input_tokens": 17, "output_tokens": 13}
    assert audit["responses"][0]["actual_model"] == run.model_name
    assert audit["responses"][0]["observed_cost"] is None
    assert withheld_text not in json.dumps(run.manifest_json)
    assert "synthetic-secret-must-not-persist" not in json.dumps(run.manifest_json)
    with TestClient(create_app(settings=settings, database=database)) as client:
        response = client.get(
            f"/api/v1/analyses/{run.id}",
            headers={"X-Analysis-Token": "synthetic-claude-worker-access"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "FAILED"
        assert response.json()["manifest_json"]["model_processing"] == audit
        assert withheld_text not in response.text
        assert "synthetic-secret-must-not-persist" not in response.text
        assert (
            client.get(
                f"/api/v1/analyses/{run.id}/courses",
                headers={"X-Analysis-Token": "synthetic-claude-worker-access"},
            ).json()["total"]
            == 0
        )


def test_late_usage_cannot_modify_an_already_terminated_job(
    database, session, monkeypatch, tmp_path
):
    """Crash/terminated-job billing gaps require external reconciliation, not stale writes."""
    settings = synthetic_settings(tmp_path, analysis_model_provider="replit_claude")
    programme = synthetic_programme(session)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(mode="live", research=False))
    original_manifest = deepcopy(run.manifest_json)

    def terminate_during_response(_payload):
        with database.session_factory() as operation:
            stopped = operation.get(Job, run.job_id)
            stopped.status, stopped.completed_at = JobStatus.FAILED, datetime.now(UTC)
            stopped.error = "Synthetic operator termination retains ownership"
            stopped.result_json = {"operator_note": "Synthetic terminated job is immutable"}
            operation.commit()

    calls = synthetic_models(monkeypatch, on_return=terminate_during_response)
    assert run_once(database, settings) == run.job_id
    session.expire_all()
    stored = session.get(Job, run.job_id)
    saved = session.get(AnalysisRun, run.id)
    assert calls == ["replit_claude"]
    assert stored.status == JobStatus.FAILED
    assert stored.error == "Synthetic operator termination retains ownership"
    assert stored.result_json == {"operator_note": "Synthetic terminated job is immutable"}
    assert saved.manifest_json == original_manifest and saved.model_name is None
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 0


@pytest.mark.integration
def test_postgresql_claude_usage_and_actual_model_round_trip_through_worker_and_api(
    migration_database,  # noqa: F811 - imported fixture
    tmp_path,
    monkeypatch,
):
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    settings = synthetic_settings(tmp_path, analysis_model_provider="replit_claude")
    calls = synthetic_models(monkeypatch)
    with database.session_factory() as session:
        programme = synthetic_programme(session)
        programme_id = programme.id
    # A worker must not join a caller's open transaction on this fixture's shared Connection.
    # Complete the API submission before starting the separate worker session.
    with TestClient(create_app(settings=settings, database=database)) as client:
        client.headers["X-Analysis-Token"] = "synthetic-claude-worker-access"
        queued = client.post(
            f"/api/v1/programmes/{programme_id}/analyses",
            json={"mode": "live", "research": False},
        )
        assert queued.status_code == 202, queued.text
        run_id, job_id = UUID(queued.json()["id"]), UUID(queued.json()["job_id"])
        assert queued.json()["status"] == "QUEUED"
        assert run_once(database, settings) == job_id
        assert calls == ["replit_claude"]
        response = client.get(f"/api/v1/analyses/{run_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "SUCCEEDED" and body["is_synthetic"] is True
        assert body["model_name"] == "synthetic-replit_claude-response-model"
        observed = body["manifest_json"]["model_processing"]["responses"][0]
        assert observed["usage"] == {"input_tokens": 17, "output_tokens": 13}
        assert observed["observed_cost"] is None
        assert client.get(f"/api/v1/analyses/{run_id}/courses").json()["total"] == 3
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(CourseFinding)) == 3
        assert session.get(Job, job_id).status == JobStatus.SUCCEEDED
        assert_complete_synthetic_findings(session, session.get(AnalysisRun, run_id))
    # Verify committed state through another PostgreSQL connection, beyond the fixture session.
    schema = connection.dialect.default_schema_name
    with connection.engine.connect().execution_options(
        schema_translate_map={None: schema}
    ) as other:
        assert other.scalar(select(Job.status).where(Job.id == job_id)) == JobStatus.SUCCEEDED
        persisted = other.scalar(select(AnalysisRun.manifest_json).where(AnalysisRun.id == run_id))
        assert persisted["model_processing"]["responses"][0]["usage"] == {
            "input_tokens": 17,
            "output_tokens": 13,
        }
    assert run_once(database, settings) is None
