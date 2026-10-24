"""Offline synthetic queue/persistence/API tests; no search or model calls."""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shiftos.api.routers.analysis import router
from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.main import create_app
from shiftos.models import (
    AnalysisRun,
    Course,
    CourseFinding,
    Dataset,
    DatasetVersion,
    EvidenceReference,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
    ResearchCache,
    Source,
)
from shiftos.repositories.analysis import (
    enqueue_analysis,
    get_analysis,
    lock_analysis_for_job,
    replace_findings,
)
from shiftos.repositories.catalogue import digest
from shiftos.schemas.analysis import AnalysisRequest


@pytest.fixture
def analysis_records(session):
    institution = Institution(name="Synthetic Analysis University", is_synthetic=True)
    session.add(institution)
    session.flush()
    programme = Programme(
        institution_id=institution.id,
        name="Synthetic Analysis Programme",
        is_synthetic=True,
    )
    session.add(programme)
    session.flush()
    revision = ProgrammeRevision(
        programme_id=programme.id,
        version_label="synthetic-analysis-v1",
        is_synthetic=True,
    )
    session.add(revision)
    session.flush()
    courses = [
        Course(
            programme_revision_id=revision.id,
            course_name=f"Synthetic Course {i}",
            is_synthetic=True,
        )
        for i in range(3)
    ]
    session.add_all(courses)
    programme.active_revision_id = revision.id
    session.commit()
    return {
        "institution": institution,
        "programme": programme,
        "revision": revision,
        "courses": courses,
    }


@pytest.fixture
def analysis_client(database, tmp_path):
    permissions = tmp_path / "analysis-permissions.synthetic.json"
    permissions.write_text(
        json.dumps({"version": "synthetic-test-1", "sources": {}}), encoding="utf-8"
    )
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        analysis_write_token="synthetic-analysis-token",
        analysis_permissions_path=permissions,
    )
    app = create_app(settings=settings, database=database)
    if not any(getattr(route, "path", None) == "/api/v1/analyses/{id}" for route in app.routes):
        app.include_router(router)
    with TestClient(app) as client:
        client.headers["X-Analysis-Token"] = "synthetic-analysis-token"
        yield client


def _queue(session, records, **kwargs):
    return enqueue_analysis(
        session, records["programme"].id, AnalysisRequest(mode="offline", **kwargs)
    )


def _source_pointer(session, key, *, allowed=True):
    source = Source(
        publisher="Synthetic API source",
        title="Synthetic revocable source",
        url="https://example.invalid/synthetic-source",
        is_synthetic=True,
        evidence_class="synthetic_demo",
    )
    dataset = Dataset(
        registry_key=f"SYNTHETIC-{uuid4()}",
        name="Synthetic source status",
        category="synthetic",
        is_synthetic=True,
    )
    session.add_all([source, dataset])
    session.flush()
    version = DatasetVersion(
        dataset_id=dataset.id,
        source_id=source.id,
        content_sha256="1" * 64,
        parser_version="synthetic-source-1",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        artifact_url=source.url,
        is_synthetic=True,
    )
    session.add(version)
    session.flush()
    reference = EvidenceReference(
        version_id=version.id,
        locator="Synthetic page 1",
        excerpt="Synthetic source text",
        review_status="reviewed",
        is_synthetic=True,
    )
    session.add(reference)
    session.flush()
    return {
        "id": key,
        "kind": "academic_standard",
        "evidence_reference_id": str(reference.id),
        "version_id": str(version.id),
        "source_id": "synthetic-source",
        "excerpt": "Synthetic permitted excerpt" if allowed else "Synthetic restricted excerpt",
        "facts": {"statement": "Synthetic source claim"},
        "rights": {"excerpt_output_allowed": allowed},
    }


def test_submission_is_queued_and_snapshot_bound(session, analysis_records):
    run = _queue(session, analysis_records)
    job = session.get(Job, run.job_id)
    assert job.kind == "PROGRAMME_ANALYSIS" and job.status == JobStatus.QUEUED
    assert run.programme_revision_id == analysis_records["revision"].id
    assert job.programme_revision_id == run.programme_revision_id
    assert job.institution_id == run.institution_id
    assert run.request_json["as_of"] is None
    assert len(run.manifest_json["inventory"]) == 3
    assert len(run.manifest_json["inventory_hash"]) == 64
    assert run.is_synthetic is True
    assert run.summary_json == {} and run.research_json == {}
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 0


def test_idempotency_returns_original_after_active_revision_changes(session, analysis_records):
    first = _queue(session, analysis_records, idempotency_key="synthetic-repeat")
    revision = ProgrammeRevision(
        programme_id=first.programme_id,
        version_label="synthetic-newer",
        is_synthetic=True,
    )
    session.add(revision)
    session.flush()
    analysis_records["programme"].active_revision_id = revision.id
    session.commit()
    repeat = _queue(session, analysis_records, idempotency_key="synthetic-repeat")
    assert repeat.id == first.id
    assert repeat.programme_revision_id == analysis_records["revision"].id
    with pytest.raises(DomainError, match="different request content"):
        _queue(session, analysis_records, idempotency_key="synthetic-repeat", research=False)
    assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1
    assert session.scalar(select(func.count()).select_from(Job)) == 1


def test_explicit_revision_and_cutoff_preserved(session, analysis_records):
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    run = _queue(
        session, analysis_records, revision_id=analysis_records["revision"].id, as_of=cutoff
    )
    assert run.request_json["as_of"].startswith("2026-01-01")
    assert get_analysis(session, run.id).id == run.id


def test_empty_or_foreign_revision_cannot_be_analysed(session, analysis_records):
    with pytest.raises(DomainError) as error:
        _queue(session, analysis_records, revision_id=uuid4())
    assert error.value.status_code == 404
    revision = ProgrammeRevision(
        programme_id=analysis_records["programme"].id,
        version_label="synthetic-empty",
        is_synthetic=True,
    )
    session.add(revision)
    session.commit()
    with pytest.raises(DomainError, match="nonempty course inventory"):
        _queue(session, analysis_records, revision_id=revision.id)


def test_findings_require_all_courses_and_terminal_runs_are_fenced(session, analysis_records):
    run = _queue(session, analysis_records)
    job = session.get(Job, run.job_id)
    with pytest.raises(DomainError, match="not running"):
        lock_analysis_for_job(session, job.id)
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC)
    session.commit()
    payload = [
        {"course_id": str(course.id), "review_flag": "insufficient_evidence"}
        for course in analysis_records["courses"]
    ]
    with pytest.raises(DomainError, match="every frozen course"):
        replace_findings(session, run, payload[:1])
    replace_findings(session, run, payload)
    session.commit()
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 3
    replace_findings(session, run, payload)
    session.commit()
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 3
    job.status, job.completed_at = JobStatus.SUCCEEDED, datetime.now(UTC)
    session.commit()
    with pytest.raises(DomainError, match="immutable"):
        replace_findings(session, run, payload)
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 3


def test_composite_finding_ownership_and_run_revision_are_enforced(session, analysis_records):
    run = _queue(session, analysis_records)
    other_programme = Programme(
        institution_id=run.institution_id,
        name="Synthetic Other Programme",
        is_synthetic=True,
    )
    session.add(other_programme)
    session.flush()
    other_revision = ProgrammeRevision(
        programme_id=other_programme.id,
        version_label="synthetic-other",
        is_synthetic=True,
    )
    session.add(other_revision)
    session.flush()
    other_course = Course(
        programme_revision_id=other_revision.id,
        course_name="Synthetic Other Course",
        is_synthetic=True,
    )
    session.add(other_course)
    session.commit()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            CourseFinding(
                run_id=run.id,
                course_id=other_course.id,
                programme_revision_id=run.programme_revision_id,
                result_json={},
                is_synthetic=True,
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            CourseFinding(
                run_id=run.id,
                course_id=other_course.id,
                programme_revision_id=other_revision.id,
                result_json={},
                is_synthetic=True,
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            AnalysisRun(
                institution_id=run.institution_id,
                programme_id=other_programme.id,
                programme_revision_id=run.programme_revision_id,
                job_id=run.job_id,
                mode="offline",
                is_synthetic=True,
            )
        )
        session.flush()


def test_analysis_api_queued_history_empty_results_and_validation(
    analysis_client, analysis_records
):
    programme = analysis_records["programme"].id
    path = f"/api/v1/programmes/{programme}/analyses"
    response = analysis_client.post(
        path, json={"mode": "offline", "idempotency_key": "synthetic-api"}
    )
    assert response.status_code == 202, response.text
    run = response.json()
    assert run["status"] == "QUEUED" and run["is_synthetic"] is True
    repeat = analysis_client.post(
        path, json={"mode": "offline", "idempotency_key": "synthetic-api"}
    )
    assert repeat.json()["id"] == run["id"]
    assert analysis_client.get(path).json()["total"] == 1
    assert analysis_client.get(f"/api/v1/analyses/{run['id']}").json()["job_id"] == run["job_id"]
    assert analysis_client.get(f"/api/v1/analyses/{run['id']}/courses").json()["total"] == 0
    assert analysis_client.get(path + "?limit=101").status_code == 422
    assert (
        analysis_client.post(
            path, json={"arbitrary_fetch_url": "https://example.invalid"}
        ).status_code
        == 422
    )


def test_all_analysis_routes_are_protected_and_unset_token_fails_closed(database, analysis_records):
    settings = Settings(_env_file=None, app_env="test", database_url="sqlite+pysqlite:///:memory:")
    app = create_app(settings=settings, database=database)
    if not any(getattr(route, "path", None) == "/api/v1/analyses/{id}" for route in app.routes):
        app.include_router(router)
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/programmes/{analysis_records['programme'].id}/analyses", json={}
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "ANALYSIS_ACCESS_DISABLED"
        assert client.get(f"/api/v1/analyses/{uuid4()}").status_code == 503


@pytest.mark.parametrize(
    "suffix", ["", "/courses", "/courses/00000000-0000-0000-0000-000000000000"]
)
def test_protected_reads_do_not_reveal_existence_without_correct_token(analysis_client, suffix):
    response = analysis_client.get(
        f"/api/v1/analyses/{uuid4()}" + suffix, headers={"X-Analysis-Token": "synthetic-wrong"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"


def test_findings_and_manifest_redact_unpermitted_original_text(
    session,
    analysis_records,
    analysis_client,
):
    run = _queue(session, analysis_records)
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC)
    session.commit()
    references = [
        _source_pointer(session, "reference:denied", allowed=False),
        _source_pointer(session, "reference:allowed"),
    ]
    policy = json.loads(analysis_client.app.state.settings.analysis_permissions_path.read_text())
    run.manifest_json = {
        **run.manifest_json,
        "permission_policy": {"version": policy["version"], "sha256": digest(policy)},
        "packet": {"references": references},
        "raw": "Synthetic raw source",
        "prompt": "Synthetic model input",
    }
    payload = [
        {
            "course_id": str(course.id),
            "citations": [
                {"reference_id": "reference:denied", "quote": "Synthetic restricted excerpt"},
                {"reference_id": "reference:allowed", "quote": "Synthetic permitted excerpt"},
            ],
        }
        for course in analysis_records["courses"]
    ]
    replace_findings(session, run, payload)
    session.commit()
    result = analysis_client.get(f"/api/v1/analyses/{run.id}").json()
    assert "Synthetic restricted" not in str(result)
    assert "raw" not in result["manifest_json"] and "prompt" not in result["manifest_json"]
    assert result["manifest_json"]["packet"]["references"][0]["source_id"] == "synthetic-source"
    findings = analysis_client.get(f"/api/v1/analyses/{run.id}/courses").json()
    assert findings["total"] == 3
    first = findings["items"][0]
    assert "quote" not in first["result_json"]["citations"][0]
    assert first["result_json"]["citations"][1]["quote"] == "Synthetic permitted excerpt"
    detail = analysis_client.get(f"/api/v1/analyses/{run.id}/courses/{first['course_id']}")
    assert detail.status_code == 200
    assert detail.json() == first
    with session.begin_nested():
        assert session.get(CourseFinding, UUID(first["id"])).result_json["citations"][0]["quote"]


def test_changed_or_unavailable_policy_withholds_old_quotes_without_mutating_run(
    session,
    analysis_records,
    analysis_client,
    tmp_path,
):
    policy_path = tmp_path / "permissions.synthetic.json"
    policy = {"version": "synthetic-permission-v1", "sources": {}}
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    analysis_client.app.state.settings.analysis_permissions_path = policy_path
    run = _queue(session, analysis_records)
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC)
    session.commit()
    pointer = _source_pointer(session, "reference:revocable")
    pointer["excerpt"] = "Synthetic revocable text"
    run.manifest_json = {
        **run.manifest_json,
        "permission_policy": {"version": policy["version"], "sha256": digest(policy)},
        "packet": {"references": [pointer]},
    }
    findings = [
        {
            "course_id": str(course.id),
            "citations": [
                {"reference_id": "reference:revocable", "quote": "Synthetic revocable text"},
            ],
        }
        for course in analysis_records["courses"]
    ]
    replace_findings(session, run, findings)
    session.commit()
    path = f"/api/v1/analyses/{run.id}"
    first = analysis_client.get(path).json()
    assert first["needs_evidence_revalidation"] is False
    assert first["manifest_json"]["packet"]["references"][0]["excerpt"]
    policy_path.write_text(
        json.dumps({**policy, "version": "synthetic-permission-v2"}), encoding="utf-8"
    )
    changed = analysis_client.get(path).json()
    assert changed["needs_evidence_revalidation"] is True
    assert "excerpt" not in changed["manifest_json"]["packet"]["references"][0]
    assert "facts" not in changed["manifest_json"]["packet"]["references"][0]
    page = analysis_client.get(path + "/courses").json()
    assert page["items"][0]["needs_evidence_revalidation"] is True
    assert "quote" not in page["items"][0]["result_json"]["citations"][0]
    policy_path.write_text("not JSON", encoding="utf-8")
    invalid = analysis_client.get(path).json()
    assert invalid["needs_evidence_revalidation"] is True
    assert invalid["evidence_access_limitations"]
    session.expire_all()
    stored = session.get(AnalysisRun, run.id)
    assert stored.manifest_json["packet"]["references"][0]["excerpt"] == "Synthetic revocable text"


@pytest.mark.parametrize(
    "change",
    [
        "rejected",
        "rights_withdrawn",
        "retracted",
        "superseded",
        "correction_pending",
        "reference_flag",
        "missing_identity",
    ],
)
def test_current_source_status_withholds_frozen_text_and_preserves_history(
    session,
    analysis_records,
    analysis_client,
    change,
):
    run = _queue(session, analysis_records)
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC)
    session.commit()
    pointer = _source_pointer(session, "reference:status")
    policy = json.loads(analysis_client.app.state.settings.analysis_permissions_path.read_text())
    run.manifest_json = {
        **run.manifest_json,
        "permission_policy": {"version": policy["version"], "sha256": digest(policy)},
        "packet": {"references": [pointer]},
    }
    findings = [
        {
            "course_id": str(course.id),
            "citations": [
                {"reference_id": "reference:status", "quote": "Synthetic permitted excerpt"},
            ],
        }
        for course in analysis_records["courses"]
    ]
    replace_findings(session, run, findings)
    run.fingerprint = "f" * 64
    job.status, job.completed_at = JobStatus.SUCCEEDED, datetime.now(UTC)
    session.commit()
    path = f"/api/v1/analyses/{run.id}"
    unchanged = analysis_client.get(path).json()
    assert unchanged["needs_evidence_revalidation"] is False
    assert unchanged["manifest_json"]["packet"]["references"][0]["excerpt"]
    reference = session.get(EvidenceReference, UUID(pointer["evidence_reference_id"]))
    version = session.get(DatasetVersion, UUID(pointer["version_id"]))
    if change == "rejected":
        reference.review_status = "rejected"
    elif change == "reference_flag":
        reference.metadata_json = {"retracted": True}
    elif change == "missing_identity":
        invalid = {**pointer}
        invalid.pop("version_id")
        run.manifest_json = {**run.manifest_json, "packet": {"references": [invalid]}}
    else:
        version.metadata_json = {change: True}
    session.commit()
    response = analysis_client.get(path).json()
    assert response["needs_evidence_revalidation"] is True
    assert response["evidence_access_limitations"]
    assert response["manifest_json"]["packet"]["references"][0]["source_id"] == "synthetic-source"
    assert "excerpt" not in response["manifest_json"]["packet"]["references"][0]
    page = analysis_client.get(path + "/courses").json()
    assert page["items"][0]["needs_evidence_revalidation"] is True
    assert "quote" not in page["items"][0]["result_json"]["citations"][0]
    session.expire_all()
    stored = session.get(AnalysisRun, run.id)
    assert stored.fingerprint == "f" * 64
    assert (
        stored.manifest_json["packet"]["references"][0]["excerpt"] == "Synthetic permitted excerpt"
    )
    assert (
        session.scalar(select(CourseFinding).where(CourseFinding.run_id == run.id)).result_json[
            "citations"
        ][0]["quote"]
        == "Synthetic permitted excerpt"
    )


def test_research_cache_key_identity(session):
    session.add(
        ResearchCache(
            cache_key="a" * 64,
            policy_sha256="b" * 64,
            response_json={"status": "synthetic"},
            expires_at=datetime(2027, 1, 1, tzinfo=UTC),
            is_synthetic=True,
        )
    )
    session.commit()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            ResearchCache(
                cache_key="a" * 64,
                policy_sha256="c" * 64,
                response_json={},
                expires_at=datetime(2027, 1, 1, tzinfo=UTC),
                is_synthetic=True,
            )
        )
        session.flush()


def test_legacy_job_route_cannot_bypass_analysis_token(
    session,
    analysis_records,
    analysis_client,
):
    run = _queue(session, analysis_records)
    path = f"/api/v1/catalogue/jobs/{run.job_id}"
    assert analysis_client.get(path).status_code == 200
    assert analysis_client.get(path, headers={"X-Analysis-Token": ""}).status_code == 401
    assert (
        analysis_client.get(path, headers={"X-Analysis-Token": "synthetic-wrong"}).status_code
        == 401
    )
    legacy = Job(
        institution_id=run.institution_id,
        kind="CURRICULUM_IMPORT",
        is_synthetic=True,
    )
    session.add(legacy)
    session.commit()
    assert (
        analysis_client.get(
            f"/api/v1/catalogue/jobs/{legacy.id}", headers={"X-Analysis-Token": ""}
        ).status_code
        == 200
    )
    analysis_client.app.state.settings.analysis_write_token = None
    assert analysis_client.get(path).status_code == 503
