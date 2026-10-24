"""Real offline Phase 4 context and selective comparison of immutable plans."""

from uuid import UUID

from career_helpers import TOKEN
from fastapi.testclient import TestClient
from pathways_helpers import seed_pathways

from shiftos.main import create_app
from shiftos.services.ingestion.worker import run_once


def test_phase4_context_and_new_plan_compare_exact_changed_dependency(session, database):
    fixture = seed_pathways(session, database)
    with TestClient(create_app(settings=fixture.settings, database=database)) as client:
        client.headers["X-Analysis-Token"] = TOKEN
        response = client.post(
            f"/api/v1/programmes/{fixture.records.programme.id}/analyses",
            json={"mode": "offline", "research": False},
        )
        assert response.status_code == 202, response.text
        phase4 = response.json()
        assert run_once(database, fixture.settings) == UUID(phase4["job_id"])
        actual = client.get(f"/api/v1/analyses/{phase4['id']}").json()
        assert actual["status"] in {"SUCCEEDED", "PARTIAL"}
        body = fixture.request.model_dump(mode="json")
        body["phase4_analysis_id"] = phase4["id"]
        path = f"/api/v1/career-analyses/{fixture.parent.id}/action-plans"

        def complete(payload):
            response = client.post(path, json=payload)
            assert response.status_code == 202, response.text
            queued = response.json()
            assert run_once(database, fixture.settings) == UUID(queued["job_id"])
            result = client.get(f"/api/v1/action-plans/{queued['id']}").json()
            assert result["status"] in {"SUCCEEDED", "PARTIAL"}, result.get("error")
            return result

        first = complete(body)
        context = first["result_json"]["overview"]["phase4_context"]
        assert context["status"] == "linked_same_revision"
        assert {row["course_id"] for row in context["courses"]} == set(
            first["result_json"]["overview"]["course_ids"]
        )
        body["previous_plan_id"] = first["id"]
        body["durations"].append(
            {
                "recommendation_id": str(fixture.by_skill["model"].id),
                "step_key": "review",
                "hours": 1,
                "basis_type": "planning_assumption",
                "basis": "Explicit fictional workload assumption; no calendar guarantee.",
                "reviewed": True,
                "reviewed_at": fixture.now.isoformat(),
            }
        )
        second = complete(body)
        reassessment = second["result_json"]["reassessment"]
        assert reassessment["status"] == "compared_frozen_dependencies"
        assert len(reassessment["changed_pathway_keys"]) == 1
        assert (
            len(reassessment["unchanged_pathway_keys"]) == len(first["result_json"]["pathways"]) - 1
        )
        historical = client.get(f"/api/v1/action-plans/{first['id']}").json()
        assert historical["fingerprint"] == first["fingerprint"]
