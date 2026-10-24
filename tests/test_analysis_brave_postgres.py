"""PostgreSQL proof with mocked Brave/Claude and a frozen public DOSM CSV excerpt.

The fictional programme deliberately uses the nonsynthetic flag solely to exercise
the genuine-source query lane offline. It is never real university evidence or a
live search/model acceptance result. Every network request is prohibited except
the explicitly injected MockTransport and in-process FastAPI TestClient.
"""

import json
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker
from test_analysis_providers import SECRET
from test_analysis_research import (
    SOURCE,
    research_setup,  # noqa: F401 - isolated source fixture
    runner,
)
from test_analysis_retrieval import make_programme
from test_migrations import migration_database  # noqa: F401 - isolated PostgreSQL fixture

from alembic import command
from shiftos.api.routers.analysis import router
from shiftos.db.base import utc_now
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import AnalysisRun, CourseFinding, DatasetVersion, EvidenceReference
from shiftos.models.evidence import WorkforceObservation
from shiftos.schemas.analysis import EvidencePacket
from shiftos.services.analysis import orchestrator
from shiftos.services.analysis.providers import BraveSearch
from shiftos.services.analysis.research import ResearchService
from shiftos.services.analysis.retrieval import retrieve_evidence
from shiftos.services.analysis.validation import offline_result, validate_result
from shiftos.services.ingestion.worker import run_once

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "SYNTHETIC-BRAVE-POSTGRES-OPERATOR"


@pytest.mark.integration
def test_mocked_brave_original_source_reaches_postgresql_worker_and_protected_results(
    migration_database,  # noqa: F811 - imported fixture
    research_setup,  # noqa: F811 - imported fixture
    monkeypatch,
):
    def forbidden(*args, **kwargs):
        pytest.fail("This integration test must never make real Brave/Claude/source requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    schema = connection.scalar(text("SELECT current_schema()"))
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    settings, original_csv, _, _ = research_setup
    # Reuse committed grants; the test does not grant or widen source permissions.
    settings.analysis_permissions_path = ROOT / "data/analysis_permissions.json"
    settings.brave_search_api_key = SecretStr(SECRET)
    settings.analysis_provider_max_attempts = 1
    settings.analysis_validation_max_attempts = 1
    settings.analysis_model_provider = "replit_claude"
    settings.claude_model = "claude-opus-5"
    settings.claude_enabled = True
    settings.gemini_enabled = False
    settings.analysis_gemini_fallback_enabled = False
    settings.analysis_write_token = SecretStr(TOKEN)
    permissions = json.loads(settings.analysis_permissions_path.read_text())["sources"]

    with database.session_factory() as session:
        # Nonsynthetic-flag *simulation*: required to query real DOSM source records.
        programme, revision, courses = make_programme(session, "accounting", synthetic=False)
        for number, course in enumerate(courses, 1):
            course.course_name = f"SYNTHETIC offline query-path Agriculture context {number}"
        session.commit()
        programme_id, revision_id = programme.id, revision.id
        packet_before = retrieve_evidence(
            session, revision_id, utc_now(), permitted_sources=permissions
        )
        assert "missing_workforce" in packet_before.gaps
        assert not any(item.kind == "workforce" for item in packet_before.references)

    searches, imports = [], []

    def discovery_response(request):
        searches.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "MOCK discovery pointer to public DOSM source",
                            "url": SOURCE,
                            "description": "UNTRUSTED_SEARCH_SNIPPET_NOT_EVIDENCE",
                        }
                    ]
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(discovery_response)) as client:
        research = ResearchService(
            database,
            settings,
            lambda configured: BraveSearch(configured, client),
            runner(original_csv, imports),
        ).run("accounting", ["missing_workforce"])
    assert research["status"] == "VERIFIED_IMPORTS_AVAILABLE"
    assert research["search_request_count"] == len(searches) == len(imports) == 1
    assert len(research["version_ids"]) == 1
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(WorkforceObservation)) == 2
        assert session.scalar(select(func.count()).select_from(EvidenceReference)) == 2
        version = session.scalar(select(DatasetVersion))
        assert str(version.id) == research["version_ids"][0]
        assert version.artifact_url == SOURCE and len(version.content_sha256) == 64
        packet = retrieve_evidence(session, revision_id, utc_now(), permitted_sources=permissions)
    admitted = [item for item in packet.references if item.kind == "workforce"]
    assert len(admitted) == 2 and all(item.model_eligible for item in admitted)
    assert all(item.scope == "workforce_context" for item in admitted)
    assert all(item.facts["geography"] == "MY" for item in admitted)
    assert all(item.relevance_basis == ["lexical_candidate_not_identity"] for item in admitted)
    assert all(not item.identity_reviewed for item in admitted)
    assert {item.observation_start for item in admitted} == {"2001-01-01", "2002-01-01"}
    assert {item.observation_end for item in admitted} == {"2001-12-31", "2002-12-31"}
    assert all(item.facts["population_level"] != "occupation" for item in admitted)
    assert all("UNTRUSTED_SEARCH_SNIPPET" not in item.excerpt for item in admitted)
    assert all(item.rights.external_model_allowed for item in admitted)
    assert all(course.reference_ids for course in packet.courses)
    original_quotes = {item.id: item.excerpt for item in admitted}

    mocked_calls = []

    class MockClaudeProvider:
        def __init__(self, configured):
            self.deadline = None
            self.last_response_metadata = {
                "actual_model": "mock-claude-opus-5",
                "request_count": 0,
                "usage": {},
            }

        def generate(self, payload, schema):
            mocked_calls.append(payload)
            context = EvidencePacket.model_validate(payload)
            assert all(item.dataset_key == "D-EMPLOYMENT-SECTOR" for item in context.references)
            assert all(item.model_eligible for item in context.references)
            result = offline_result(context).model_dump(mode="json")
            # Application mode simulation only; no live request or token usage.
            result["result_mode"] = "live_model"
            return result

    monkeypatch.setattr(orchestrator, "ReplitClaudeProvider", MockClaudeProvider)
    app = create_app(settings=settings, database=database)
    if not any(getattr(route, "path", None) == "/api/v1/analyses/{id}" for route in app.routes):
        app.include_router(router)
    with TestClient(app) as client:
        submission = f"/api/v1/programmes/{programme_id}/analyses"
        assert client.post(submission, json={"mode": "live", "research": False}).status_code == 401
        client.headers["X-Analysis-Token"] = TOKEN
        queued = client.post(submission, json={"mode": "live", "research": False})
        assert queued.status_code == 202, queued.text
        run_id, job_id = queued.json()["id"], queued.json()["job_id"]
        assert run_once(database, settings) == UUID(job_id)
        result = client.get(f"/api/v1/analyses/{run_id}")
        assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED"
        assert result.json()["model_name"] == "mock-claude-opus-5"
        assert result.json()["manifest_json"]["model_processing"]["request_count"] == 0
        response = client.get(f"/api/v1/analyses/{run_id}/courses")
        assert response.status_code == 200
        findings = response.json()
        assert findings["total"] == len(packet.courses) == 2
        for finding in findings["items"]:
            course = finding["result_json"]
            assert course["needs_syllabus_confirmation"] is True
            assert course["is_final_curriculum_verdict"] is False
            workforce = course["workforce_alignment"]
            assert workforce["status"] == "insufficient_evidence"
            assert "broad_population_not_individual_demand" in workforce["limitations"]
            assert workforce["citations"]
            for citation in workforce["citations"]:
                assert citation["quote"] in original_quotes[citation["reference_id"]]
        assert (
            client.get(f"/api/v1/analyses/{run_id}", headers={"X-Analysis-Token": ""}).status_code
            == 401
        )
    assert len(mocked_calls) == 1 and len(searches) == 1

    forged = deepcopy(offline_result(packet).model_dump(mode="json"))
    forged["courses"][0]["workforce_alignment"]["citations"][0]["quote"] = (
        "This fabricated source says every fictional graduate will obtain a job."
    )
    with pytest.raises(ValueError, match="Quote does not match"):
        validate_result(forged, packet)

    # A distinct PostgreSQL connection sees committed rows in the fixture's schema.
    connection.commit()
    with connection.engine.connect() as independent:
        independent.exec_driver_sql(f'SET search_path TO "{schema}"')
        with sessionmaker(bind=independent)() as session:
            stored = session.get(AnalysisRun, UUID(run_id))
            assert stored is not None and stored.model_name == "mock-claude-opus-5"
            assert session.scalar(select(func.count()).select_from(CourseFinding)) == 2
            assert session.scalar(select(func.count()).select_from(WorkforceObservation)) == 2
            assert session.scalar(select(func.count()).select_from(DatasetVersion)) == 1
