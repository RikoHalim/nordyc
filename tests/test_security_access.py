"""Offline operator scopes; no claim of named-user identity or live AI acceptance."""

import hashlib
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from career_helpers import career_settings, seed_career
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from shiftos.core.access import validate_access_configuration
from shiftos.core.config import Settings
from shiftos.core.enums import EvidenceClass
from shiftos.core.errors import DomainError
from shiftos.main import create_app
from shiftos.models import (
    ActionPlanRun,
    AnalysisRun,
    CareerRecommendation,
    CareerRun,
    Course,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
    Source,
)
from shiftos.services.ingestion.worker import run_once

TOKENS = {
    key: f"SYNTHETIC-SCOPED-{key}-OPERATOR-CREDENTIAL-NOT-LIVE"
    for key in ("reader", "writer", "reviewer", "other", "admin_read", "admin")
}


def auth(key):
    return {"Authorization": f"Bearer {TOKENS[key]}"}


def policy(path, institution, other):
    grants = {
        "reader": ([institution], ["read"]),
        "writer": ([institution], ["read", "write"]),
        "reviewer": ([institution], ["read", "review"]),
        "other": ([other], ["read", "write", "review"]),
        "admin_read": ([], ["admin", "read"]),
        "admin": ([], ["admin", "read", "write", "review"]),
    }
    value = {
        "version": "phase7-access-1",
        "principals": [
            {
                "principal_id": key,
                "token_sha256": hashlib.sha256(TOKENS[key].encode()).hexdigest(),
                "institution_ids": [str(value) for value in institutions],
                "permissions": permissions,
            }
            for key, (institutions, permissions) in grants.items()
        ],
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return value


def seed_owner(session, label):
    # These rows are ownership scaffolding, never an evaluated academic result.
    source = Source(
        publisher="Fictional access-test publisher",
        title=f"Private synthetic source {label}",
        evidence_class=EvidenceClass.SYNTHETIC_DEMO,
        is_synthetic=True,
    )
    session.add(source)
    session.flush()
    institution = Institution(
        name=f"Fictional institution {label}", source_id=source.id, is_synthetic=True
    )
    session.add(institution)
    session.flush()
    programme = Programme(
        institution_id=institution.id,
        name=f"Fictional programme {label}",
        source_id=source.id,
        is_synthetic=True,
    )
    session.add(programme)
    session.flush()
    revision = ProgrammeRevision(
        programme_id=programme.id, version_label="synthetic-access-1", is_synthetic=True
    )
    session.add(revision)
    session.flush()
    programme.active_revision_id = revision.id
    course = Course(
        programme_revision_id=revision.id,
        course_name=f"Fictional course {label}",
        source_id=source.id,
        is_synthetic=True,
    )
    session.add(course)
    runs = {}
    for kind, model in (
        ("PROGRAMME_ANALYSIS", AnalysisRun),
        ("CAREER_ANALYSIS", CareerRun),
        ("ACTION_PLAN", ActionPlanRun),
    ):
        job = Job(
            institution_id=institution.id,
            programme_revision_id=revision.id,
            kind=kind,
            is_synthetic=True,
            result_json={"private_quote": "SENTINEL-PRIVATE-SOURCE-CONTENT"},
        )
        session.add(job)
        session.flush()
        values = dict(
            institution_id=institution.id,
            programme_id=programme.id,
            programme_revision_id=revision.id,
            job_id=job.id,
            mode="offline",
            is_synthetic=True,
        )
        if model is ActionPlanRun:
            values.update(career_run_id=runs["career"].id, career_fingerprint="a" * 64)
        run = model(**values)
        session.add(run)
        session.flush()
        runs[{AnalysisRun: "analysis", CareerRun: "career", ActionPlanRun: "plan"}[model]] = run
    recommendation = CareerRecommendation(
        run_id=runs["career"].id,
        programme_revision_id=revision.id,
        recommendation_key="synthetic-scope-only",
        version_sha256="b" * 64,
        is_synthetic=True,
    )
    session.add(recommendation)
    session.commit()
    return SimpleNamespace(
        institution=institution,
        source=source,
        programme=programme,
        revision=revision,
        course=course,
        recommendation=recommendation,
        **runs,
    )


@pytest.fixture
def scoped(session, database, tmp_path):
    own, other = seed_owner(session, "A"), seed_owner(session, "B")
    path = tmp_path / "synthetic-access.json"
    data = policy(path, own.institution.id, other.institution.id)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        api_access_mode="scoped",
        api_access_policy_path=path,
        analysis_write_token=None,
        catalogue_write_token=None,
    )
    with TestClient(create_app(settings=settings, database=database)) as client:
        yield SimpleNamespace(
            own=own, other=other, client=client, settings=settings, path=path, policy=data
        )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer wrong-credential-with-at-least-thirty-two-characters"},
        {"Authorization": f"Basic {TOKENS['reader']}"},
        {"X-Analysis-Token": TOKENS["reader"], "X-Catalogue-Token": TOKENS["reader"]},
    ],
)
def test_scoped_routes_require_bearer_and_do_not_echo_credentials(scoped, headers):
    response = scoped.client.get("/api/v1/programmes", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"
    assert not any(value in response.text for value in TOKENS.values())


def test_global_lists_filter_before_total_count_and_pagination(scoped):
    for family, expected in (
        ("institutions", scoped.own.institution.id),
        ("programmes", scoped.own.programme.id),
    ):
        response = scoped.client.get(f"/api/v1/{family}?limit=1", headers=auth("reader"))
        assert response.status_code == 200, response.text
        assert response.json()["total"] == 1
        assert [row["id"] for row in response.json()["items"]] == [str(expected)]
        page = scoped.client.get(f"/api/v1/{family}?offset=1", headers=auth("reader")).json()
        assert page["total"] == 1 and page["items"] == []
        assert "Fictional institution B" not in response.text
        assert "Fictional programme B" not in response.text


@pytest.mark.parametrize(
    "resource",
    [
        "institution",
        "institution_programmes",
        "programme",
        "courses",
        "course",
        "coverage",
        "revisions",
        "revision_courses",
        "phase4_history",
        "career_history",
        "analysis",
        "career",
        "recommendations",
        "recommendation_reviews",
        "plan",
        "plan_evidence",
        "plan_reviews",
        "plan_history",
        "job",
    ],
)
def test_foreign_direct_ids_and_histories_are_hidden_before_serialization(scoped, resource):
    foreign = scoped.other
    paths = {
        "institution": f"institutions/{foreign.institution.id}",
        "institution_programmes": f"institutions/{foreign.institution.id}/programmes",
        "programme": f"programmes/{foreign.programme.id}",
        "courses": f"programmes/{foreign.programme.id}/courses",
        "course": f"courses/{foreign.course.id}",
        "coverage": f"programmes/{foreign.programme.id}/coverage",
        "revisions": f"programmes/{foreign.programme.id}/revisions",
        "revision_courses": (
            f"programmes/{foreign.programme.id}/revisions/{foreign.revision.id}/courses"
        ),
        "phase4_history": f"programmes/{foreign.programme.id}/analyses",
        "career_history": f"programmes/{foreign.programme.id}/career-analyses",
        "analysis": f"analyses/{foreign.analysis.id}",
        "career": f"career-analyses/{foreign.career.id}",
        "recommendations": f"career-analyses/{foreign.career.id}/recommendations",
        "recommendation_reviews": f"career-recommendations/{foreign.recommendation.id}/reviews",
        "plan": f"action-plans/{foreign.plan.id}",
        "plan_evidence": f"action-plans/{foreign.plan.id}/evidence",
        "plan_reviews": f"action-plans/{foreign.plan.id}/reviews",
        "plan_history": f"career-analyses/{foreign.career.id}/action-plans",
        "job": f"catalogue/jobs/{foreign.plan.job_id}",
    }
    response = scoped.client.get(f"/api/v1/{paths[resource]}", headers=auth("reader"))
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "SENTINEL" not in response.text
    assert "Fictional" not in response.text


def test_write_review_and_admin_are_separate_privileges(scoped, session):
    programme_path = f"/api/v1/institutions/{scoped.own.institution.id}/programmes"
    for key in ("reader", "reviewer", "admin_read"):
        response = scoped.client.post(programme_path, json={"name": "Denied"}, headers=auth(key))
        assert response.status_code == 403, response.text
    for path in (
        f"/api/v1/career-recommendations/{scoped.own.recommendation.id}/reviews",
        f"/api/v1/action-plans/{scoped.own.plan.id}/reviews",
    ):
        response = scoped.client.post(path, json={}, headers=auth("writer"))
        assert response.status_code == 403, response.text
    assert session.scalar(select(func.count()).select_from(Programme)) == 2
    assert (
        scoped.client.post(
            "/api/v1/institutions", json={"name": "Denied"}, headers=auth("writer")
        ).status_code
        == 403
    )


def test_scoped_writer_can_create_only_in_own_institution_and_attributed_source(scoped):
    response = scoped.client.post(
        "/api/v1/programmes",
        json={
            "name": "Fictional extra",
            "institution_id": str(scoped.own.institution.id),
            "source_id": str(scoped.own.source.id),
        },
        headers=auth("writer"),
    )
    assert response.status_code == 201, response.text
    created_id = response.json()["id"]
    for institution, source in (
        (scoped.other.institution.id, scoped.other.source.id),
        (scoped.own.institution.id, scoped.other.source.id),
        (scoped.own.institution.id, uuid4()),
    ):
        response = scoped.client.post(
            "/api/v1/programmes",
            json={
                "name": "Denied foreign attribution",
                "institution_id": str(institution),
                "source_id": str(source),
            },
            headers=auth("writer"),
        )
        assert response.status_code == 404, response.text
    assert (
        scoped.client.post(
            f"/api/v1/programmes/{created_id}/courses",
            json={"course_name": "Fictional course", "source_id": str(scoped.own.source.id)},
            headers=auth("writer"),
        ).status_code
        == 201
    )
    assert (
        scoped.client.post(
            f"/api/v1/programmes/{created_id}/courses",
            json={"course_name": "Denied", "source_id": str(scoped.other.source.id)},
            headers=auth("writer"),
        ).status_code
        == 404
    )


@pytest.mark.parametrize("suffix", ["imports", "curriculum-pdf", "analyses", "career-analyses"])
def test_foreign_submission_and_upload_fail_before_payload_processing(scoped, suffix):
    response = scoped.client.post(
        f"/api/v1/programmes/{scoped.other.programme.id}/{suffix}",
        content=b"not-a-document" if suffix == "curriculum-pdf" else b"{}",
        headers={
            **auth("writer"),
            "Content-Type": "application/pdf" if suffix == "curriculum-pdf" else "application/json",
        },
    )
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "path",
    [
        "sources",
        "evidence/datasets",
        "evidence/references",
        "evidence/occupations",
        "evidence/workforce-trends",
    ],
)
def test_global_source_catalogue_requires_explicit_admin(scoped, path):
    response = scoped.client.get(f"/api/v1/{path}", headers=auth("reader"))
    assert response.status_code == 403, response.text


def test_admin_read_can_inspect_global_catalogues_but_not_write(scoped):
    for path in ("sources", "evidence/datasets", "institutions", "programmes"):
        response = scoped.client.get(f"/api/v1/{path}", headers=auth("admin_read"))
        assert response.status_code == 200, response.text
    assert (
        scoped.client.get("/api/v1/institutions", headers=auth("admin_read")).json()["total"] == 2
    )
    assert (
        scoped.client.post(
            "/api/v1/institutions", headers=auth("admin_read"), json={"name": "Denied"}
        ).status_code
        == 403
    )


def test_policy_rotation_revokes_old_token_without_restart_or_leaking_policy(scoped):
    assert scoped.client.get("/api/v1/programmes", headers=auth("reader")).status_code == 200
    scoped.policy["principals"] = [
        row for row in scoped.policy["principals"] if row["principal_id"] != "reader"
    ]
    scoped.path.write_text(json.dumps(scoped.policy), encoding="utf-8")
    assert scoped.client.get("/api/v1/programmes", headers=auth("reader")).status_code == 401
    scoped.path.write_text('{"private-policy-sentinel":', encoding="utf-8")
    response = scoped.client.get("/api/v1/programmes", headers=auth("admin"))
    assert response.status_code == 503
    assert "private-policy-sentinel" not in response.text
    assert str(scoped.path) not in response.text


def test_scoped_job_status_withholds_source_payload_without_changing_storage(scoped, session):
    for run in (scoped.own.analysis, scoped.own.career, scoped.own.plan):
        response = scoped.client.get(f"/api/v1/catalogue/jobs/{run.job_id}", headers=auth("reader"))
        assert response.status_code == 200, response.text
        assert response.json()["result"]["source_content_withheld"] is True
        assert "SENTINEL" not in response.text and "payload_json" not in response.json()
        assert session.get(Job, run.job_id).result_json["private_quote"] == (
            "SENTINEL-PRIVATE-SOURCE-CONTENT"
        )


def test_replay_post_requires_only_read_and_checks_programme_owner_without_writes(scoped, session):
    before = session.scalar(select(func.count()).select_from(Job))
    response = scoped.client.post(
        f"/api/v1/programmes/{scoped.own.programme.id}/replay-assessment",
        headers=auth("reader"),
        json={"analysis_id": str(scoped.own.analysis.id)},
    )
    assert response.status_code == 200, response.text
    foreign = scoped.client.post(
        f"/api/v1/programmes/{scoped.other.programme.id}/replay-assessment",
        headers=auth("reader"),
        json={"analysis_id": str(scoped.other.analysis.id)},
    )
    assert foreign.status_code == 404
    assert session.scalar(select(func.count()).select_from(Job)) == before
    assert "SENTINEL" not in response.text + foreign.text


def test_openapi_exposes_bearer_and_completed_result_schemas_without_narrowing_metadata(scoped):
    document = scoped.client.get("/openapi.json").json()
    for route in (
        "/api/v1/programmes",
        "/api/v1/career-analyses/{id}",
        "/api/v1/action-plans/{id}",
    ):
        assert document["paths"][route]["get"]["security"] == [{"HTTPBearer": []}]
    schemas = document["components"]["schemas"]
    for response, completed in (("CareerRead", "CareerResult"), ("PlanRead", "PlanResult")):
        alternatives = schemas[response]["properties"]["result_json"]["anyOf"]
        assert {"$ref": f"#/components/schemas/{completed}"} in alternatives
        assert any(value.get("type") == "object" for value in alternatives)
    assert not any(token in json.dumps(document) for token in TOKENS.values())


def test_access_configuration_reports_only_safe_counts_and_production_fails_closed(scoped):
    summary = validate_access_configuration(scoped.settings)
    assert summary == {
        "mode": "scoped",
        "ready": True,
        "production_eligible": True,
        "principal_count": 6,
        "global_admin_count": 2,
    }
    assert str(scoped.own.institution.id) not in json.dumps(summary)
    for token in TOKENS.values():
        assert hashlib.sha256(token.encode()).hexdigest() not in json.dumps(summary)
    with pytest.raises(DomainError) as error:
        validate_access_configuration(Settings(_env_file=None, app_env="production"))
    assert error.value.status_code == 503 and error.value.code == "ACCESS_POLICY_REQUIRED"


@pytest.mark.parametrize(
    "mutation", ["duplicate_id", "duplicate_hash", "empty_scope", "admin_only", "extra_field"]
)
def test_invalid_policy_fails_closed_without_echoing_rejected_input(scoped, mutation):
    first = scoped.policy["principals"][0]
    if mutation == "duplicate_id":
        scoped.policy["principals"][1]["principal_id"] = first["principal_id"]
    elif mutation == "duplicate_hash":
        scoped.policy["principals"][1]["token_sha256"] = first["token_sha256"]
    elif mutation == "empty_scope":
        first["institution_ids"] = []
    elif mutation == "admin_only":
        first["permissions"] = ["admin"]
    else:
        first["private_input_sentinel"] = "do-not-echo-policy"
    scoped.path.write_text(json.dumps(scoped.policy), encoding="utf-8")
    response = scoped.client.get("/api/v1/programmes", headers=auth("reader"))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ACCESS_POLICY_INVALID"
    assert first["token_sha256"] not in response.text
    assert "do-not-echo-policy" not in response.text


@pytest.mark.parametrize("kind", ["PROGRAMME_ANALYSIS", "CAREER_ANALYSIS", "ACTION_PLAN"])
def test_legacy_analysis_jobs_require_analysis_auth_and_never_return_raw_results(
    database, session, kind
):
    owner = seed_owner(session, "legacy")
    job = session.scalar(
        select(Job).where(Job.institution_id == owner.institution.id, Job.kind == kind)
    )
    settings = Settings(_env_file=None, app_env="test", analysis_write_token=TOKENS["reader"])
    with TestClient(create_app(settings=settings, database=database)) as client:
        path = f"/api/v1/catalogue/jobs/{job.id}"
        assert client.get(path).status_code == 401
        read = client.get(path, headers={"X-Analysis-Token": TOKENS["reader"]})
    assert read.status_code == 200, read.text
    assert read.json()["result"]["source_content_withheld"] is True
    assert "SENTINEL" not in read.text and "payload_json" not in read.json()
    session.expire_all()
    assert (
        session.get(Job, job.id).result_json["private_quote"] == "SENTINEL-PRIVATE-SOURCE-CONTENT"
    )


def test_scoped_bearer_authorizes_real_offline_career_worker_and_explicit_review_role(
    database, session, tmp_path
):
    records = seed_career(session)
    path = tmp_path / "synthetic-career-access.json"
    policy(path, records.institution.id, uuid4())
    settings = career_settings(
        api_access_mode="scoped", api_access_policy_path=path, analysis_write_token=None
    )
    with TestClient(create_app(settings=settings, database=database)) as client:
        response = client.post(
            f"/api/v1/programmes/{records.programme.id}/career-analyses",
            headers=auth("writer"),
            json=records.request.model_dump(mode="json"),
        )
        assert response.status_code == 202, response.text
        run_id = UUID(response.json()["id"])
        run = session.get(CareerRun, run_id)
        assert run_once(database, settings) == run.job_id
        session.expire_all()
        read = client.get(f"/api/v1/career-analyses/{run_id}", headers=auth("reader"))
        assert read.status_code == 200, read.text
        assert read.json()["status"] in {"SUCCEEDED", "PARTIAL"}, read.text
        recommendation = session.scalar(
            select(CareerRecommendation).where(CareerRecommendation.run_id == run_id)
        )
        review_path = f"/api/v1/career-recommendations/{recommendation.id}/reviews"
        body = {
            "decision": "under_review",
            "reason": "Fictional offline academic review",
            "expected_recommendation_version": recommendation.version_sha256,
        }
        assert client.post(review_path, headers=auth("writer"), json=body).status_code == 403
        assert client.post(review_path, headers=auth("other"), json=body).status_code == 404
        review = client.post(review_path, headers=auth("reviewer"), json=body)
        assert review.status_code == 201, review.text
        assert review.json()["actor"] == "authenticated_analysis_operator"
        spoofed = client.post(
            review_path, headers=auth("reviewer"), json={**body, "actor": "university-committee"}
        )
        assert spoofed.status_code == 422
