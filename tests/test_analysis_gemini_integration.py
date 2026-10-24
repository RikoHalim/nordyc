"""Real PostgreSQL/worker/API, actual Gemini adapter with synthetic HTTP responses.

No network/model service is used; this proves backend wiring, never live accuracy.
"""

import json
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from test_analysis_providers import gemini_reply
from test_analysis_retrieval import make_evidence
from test_analysis_worker import synthetic_programme
from test_migrations import migration_database  # noqa: F401 - shared isolated PostgreSQL fixture
from test_workforce_radar import radar_records

from alembic import command
from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import AnalysisRun, Course, CourseFinding, Job
from shiftos.schemas.analysis import DIMENSIONS, EvidencePacket, ProgrammeResult
from shiftos.services.analysis import orchestrator
from shiftos.services.analysis.providers import BraveSearch, GeminiProvider
from shiftos.services.analysis.validation import offline_result
from shiftos.services.ingestion.worker import run_once


@pytest.mark.integration
@pytest.mark.parametrize("outcome", ["valid", "invalid_citation", "authentication_error"])
def test_gemini_transport_worker_postgresql_citations_usage_and_protected_api(
    migration_database,  # noqa: F811 - imported PostgreSQL fixture
    tmp_path,
    monkeypatch,
    outcome,
):
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    policy = tmp_path / "gemini-integration-policy.synthetic.json"
    policy.write_text(
        json.dumps({"version": "synthetic-gemini-1", "sources": {}}), encoding="utf-8"
    )
    settings = Settings(
        _env_file=None,
        app_env="test",
        analysis_model_provider="gemini",
        gemini_enabled=True,
        gemini_api_key="SYNTHETIC-NOT-A-REAL-CREDENTIAL",
        gemini_model="gemini-synthetic-test",
        analysis_write_token="synthetic-gemini-api-access",
        analysis_external_processing_allowed=True,
        analysis_permissions_path=policy,
        analysis_provider_max_attempts=1,
        research_enabled=False,
    )
    with database.session_factory() as session:
        programme = synthetic_programme(session, discipline="accounting")
        programme.name = "SYNTHETIC Bachelor of Accounting"
        for course in session.scalars(select(Course)):
            course.course_name = f"Synthetic accountant accounting course {course.id}"
        session.commit()
        programme_id = programme.id
        make_evidence(session, discipline="accounting", metadata={"mqf_level": 6})
        make_evidence(session, kind="ai", discipline="accounting")
        # Reuse the published synthetic observation factory, on this PostgreSQL session.
        radar_records.__wrapped__(session)
    packets, requests = [], []

    def handler(request):
        requests.append(request)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == "SYNTHETIC-NOT-A-REAL-CREDENTIAL"
        body = json.loads(request.content)
        assert "tools" not in body
        assert body["generationConfig"]["responseJsonSchema"] == ProgrammeResult.model_json_schema()
        raw = json.loads(body["contents"][0]["parts"][0]["text"])
        raw.pop("validation_feedback", None)
        packet = EvidencePacket.model_validate(raw)
        packets.append(packet)
        assert len(packet.courses) == 3 and packet.is_synthetic
        assert {ref.kind for ref in packet.references} >= {"academic_standard", "workforce"}
        assert packet.gaps  # Missing syllabi/identity/AI support remain explicit.
        assert all(ref.model_eligible for ref in packet.references)
        if outcome == "authentication_error":
            return httpx.Response(401, text="SYNTHETIC-private-error-DO-NOT-PERSIST")
        result = offline_result(packet).model_dump(mode="json")
        result["result_mode"] = "live_model"
        if outcome == "invalid_citation":
            result["courses"][0]["foundational_relevance"]["citations"] = [
                {
                    "reference_id": "synthetic:invented-source",
                    "quote": "SYNTHETIC unsupported claim must not be published.",
                    "scope": "academic_benchmark",
                }
            ]
        response = gemini_reply(json.dumps(result))
        response["usageMetadata"] = {
            "promptTokenCount": 123,
            "candidatesTokenCount": 234,
            "thoughtsTokenCount": 20,
            "totalTokenCount": 377,
        }
        return httpx.Response(200, json=response)

    def forbidden(*args, **kwargs):
        pytest.fail("No actual model/search HTTP or Claude invocation is permitted")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(BraveSearch, "search", forbidden)
    monkeypatch.setattr(orchestrator, "ReplitClaudeProvider", forbidden)
    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        monkeypatch.setattr(orchestrator, "GeminiProvider", lambda s: GeminiProvider(s, transport))
        with TestClient(create_app(settings=settings, database=database)) as client:
            path = f"/api/v1/programmes/{programme_id}/analyses"
            assert client.post(path, json={"mode": "live"}).status_code == 401
            client.headers["X-Analysis-Token"] = "synthetic-gemini-api-access"
            payload = {"mode": "live", "research": False, "idempotency_key": "synthetic-gemini-v1"}
            queued = client.post(path, json=payload)
            assert queued.status_code == 202, queued.text
            run_id, job_id = UUID(queued.json()["id"]), UUID(queued.json()["job_id"])
            assert not requests  # HTTP handlers only enqueue; worker owns provider invocation.
            assert run_once(database, settings) == job_id
            response = client.get(f"/api/v1/analyses/{run_id}")
            assert response.status_code == 200, response.text
            result = response.json()
            expected_status = "SUCCEEDED" if outcome == "valid" else "PARTIAL"
            assert result["status"] == expected_status, result
            assert result["summary_json"]["summary"]["returned_count"] == 3
            assert result["summary_json"]["insights"]["unknowns"]
            assert result["manifest_json"]["model_provider"] == "gemini_direct"
            audit = result["manifest_json"]["model_processing"]
            assert not audit["fallbacks"]
            assert len(requests) == (2 if outcome == "invalid_citation" else 1)
            assert all(item["request_count"] == 1 for item in audit["responses"])
            if outcome != "authentication_error":
                assert result["model_name"] == "gemini-synthetic-test"
                assert audit["responses"][0]["usage"]["input_tokens"] == 123
                assert audit["responses"][0]["usage"]["thought_tokens"] == 20
            else:
                assert result["model_name"] is None
                assert audit["responses"][0]["error_code"] == "provider_authentication_failed"
            findings = client.get(f"/api/v1/analyses/{run_id}/courses").json()
            assert findings["total"] == 3
            for finding in findings["items"]:
                course = finding["result_json"]
                assert course["needs_syllabus_confirmation"]
                assert course["is_final_curriculum_verdict"] is False
                assert all(course[d]["status"] == "insufficient_evidence" for d in DIMENSIONS)
            assert "synthetic:invented-source" not in json.dumps(findings)
            assert "SYNTHETIC-private-error" not in json.dumps(result)
            assert "SYNTHETIC-NOT-A-REAL-CREDENTIAL" not in json.dumps(result)
            assert (
                client.get(
                    f"/api/v1/analyses/{run_id}", headers={"X-Analysis-Token": ""}
                ).status_code
                == 401
            )
            assert client.post(path, json=payload).json()["id"] == str(run_id)
            assert run_once(database, settings) is None
    schema = connection.dialect.default_schema_name
    with connection.engine.connect().execution_options(
        schema_translate_map={None: schema}
    ) as other:
        assert (
            other.scalar(select(Job.status).where(Job.id == job_id)) == JobStatus[expected_status]
        )
        assert other.scalar(select(func.count()).select_from(CourseFinding)) == 3
        persisted = other.scalar(select(AnalysisRun.manifest_json).where(AnalysisRun.id == run_id))
        assert persisted["model_processing"] == audit
