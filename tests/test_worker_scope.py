"""Session workers cannot claim another institution, discovery or billable jobs."""

from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from test_analysis_worker import settings, synthetic_programme
from test_curriculum_upload import content, upload, upload_context  # noqa: F401

from shiftos.core.enums import JobStatus
from shiftos.models import AnalysisRun, CareerRun, Course, CourseFinding, Job, Programme
from shiftos.repositories.analysis import enqueue_analysis
from shiftos.repositories.career import enqueue_career
from shiftos.repositories.pathways import enqueue_plan
from shiftos.schemas.analysis import AnalysisRequest
from shiftos.schemas.career import CareerRequest
from shiftos.schemas.pathways import PlanRequest
from shiftos.services.ingestion.worker import run_once

PUBLIC_KINDS = frozenset(
    {"CURRICULUM_PDF_UPLOAD", "PROGRAMME_ANALYSIS", "CAREER_ANALYSIS", "ACTION_PLAN"}
)


@pytest.fixture(autouse=True)
def forbid_provider_requests(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("An offline session worker must never make an external request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def filtered(database, programme, **kwargs):
    return run_once(
        database,
        settings(),
        allowed_kinds=PUBLIC_KINDS,
        institution_ids=[programme.institution_id],
        offline_analysis_only=True,
        **kwargs,
    )


def test_filters_leave_foreign_discovery_and_live_jobs_queued_while_offline_completes(
    database, session
):
    own = synthetic_programme(session, count=1)
    foreign = synthetic_programme(session, count=1)
    foreign_run = enqueue_analysis(session, foreign.id, AnalysisRequest(mode="offline"))
    live = enqueue_analysis(session, own.id, AnalysisRequest(mode="live", research=False))
    discovery = Job(
        institution_id=own.institution_id,
        kind="CURRICULUM_DISCOVERY",
        payload_json={"provider": "xmum"},
        is_synthetic=True,
    )
    session.add(discovery)
    session.commit()
    offline = enqueue_analysis(session, own.id, AnalysisRequest(mode="offline", research=False))
    assert filtered(database, own) == offline.job_id
    session.expire_all()
    assert session.get(Job, offline.job_id).status == JobStatus.SUCCEEDED
    for job_id in (foreign_run.job_id, live.job_id, discovery.id):
        queued = session.get(Job, job_id)
        assert queued.status == JobStatus.QUEUED
        assert queued.started_at is None
    assert session.scalars(select(CourseFinding).where(CourseFinding.run_id == offline.id)).one()
    assert filtered(database, own) is None


def test_session_filter_runs_real_offline_career_and_plan_without_academic_invention(
    database, session
):
    own = synthetic_programme(session, count=1)
    live_career = enqueue_career(session, own.id, CareerRequest(mode="live"))
    offline = enqueue_career(session, own.id, CareerRequest(mode="offline"))
    assert filtered(database, own) == offline.job_id
    session.expire_all()
    result = session.get(CareerRun, offline.id).result_json
    assert len(result["course_ids"]) == 1
    assert result["status"] == "insufficient_evidence"
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["category"] == "request_review"
    live_plan = enqueue_plan(session, offline.id, PlanRequest(mode="live"), settings())
    plan = enqueue_plan(session, offline.id, PlanRequest(mode="offline"), settings())
    assert filtered(database, own) == plan.job_id
    session.expire_all()
    assert session.get(Job, plan.job_id).status == JobStatus.PARTIAL
    assert session.get(Job, live_career.job_id).status == JobStatus.QUEUED
    assert session.get(Job, live_plan.job_id).status == JobStatus.QUEUED
    assert filtered(database, own) is None


@pytest.mark.parametrize(
    "options",
    [
        {"allowed_kinds": []},
        {"institution_ids": []},
        {"institution_ids": [uuid4()]},
    ],
)
def test_empty_or_foreign_scope_does_not_claim_any_job(database, session, options):
    own = synthetic_programme(session, count=1)
    run = enqueue_analysis(session, own.id, AnalysisRequest(mode="offline"))
    assert run_once(database, settings(), **options) is None
    session.expire_all()
    assert session.get(Job, run.job_id).status == JobStatus.QUEUED


@pytest.mark.parametrize(
    "options",
    [{"allowed_kinds": ["UNSUPPORTED_JOB"]}, {"institution_ids": ["invalid-identity"]}],
)
def test_invalid_filters_fail_before_claim(database, session, options):
    own = synthetic_programme(session, count=1)
    run = enqueue_analysis(session, own.id, AnalysisRequest(mode="offline"))
    with pytest.raises(ValueError):
        run_once(database, settings(), **options)
    session.expire_all()
    assert session.get(Job, run.job_id).status == JobStatus.QUEUED


def test_missing_or_inconsistent_analysis_mode_is_not_claimed(database, session):
    own = synthetic_programme(session, count=1)
    orphan = Job(
        institution_id=own.institution_id,
        kind="PROGRAMME_ANALYSIS",
        is_synthetic=True,
    )
    session.add(orphan)
    session.commit()
    inconsistent = enqueue_analysis(session, own.id, AnalysisRequest(mode="offline"))
    record = session.get(AnalysisRun, inconsistent.id)
    record.request_json = {**record.request_json, "mode": "live"}
    session.commit()
    assert filtered(database, own) is None
    session.expire_all()
    assert session.get(Job, orphan.id).status == JobStatus.QUEUED
    assert session.get(Job, inconsistent.job_id).status == JobStatus.QUEUED


def test_scoped_worker_extracts_actual_pdf_without_discovery_or_provider_calls(
    database,
    session,
    upload_context,  # noqa: F811
):
    client, configured, programme_id = upload_context
    programme = session.get(Programme, programme_id)
    response = upload(upload_context, content())
    assert response.status_code == 202
    job_id = response.json()["id"]
    completed = run_once(
        database,
        configured,
        allowed_kinds=PUBLIC_KINDS,
        institution_ids=[programme.institution_id],
        offline_analysis_only=True,
    )
    assert str(completed) == job_id
    assert client.get(f"/api/v1/catalogue/jobs/{job_id}").json()["status"] == "SUCCEEDED"
    session.expire_all()
    programme = session.get(Programme, programme_id)
    courses = session.scalars(
        select(Course).where(Course.programme_revision_id == programme.active_revision_id)
    ).all()
    assert len(courses) == 2
    assert all(
        not course.is_verified and not course.detailed_syllabus_available for course in courses
    )
