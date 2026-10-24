"""Explicitly synthetic worker fixtures; no Gemini, Brave or live source calls."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.models import (
    AnalysisRun,
    Course,
    CourseFinding,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
)
from shiftos.repositories.analysis import enqueue_analysis
from shiftos.schemas.analysis import AnalysisRequest
from shiftos.services.analysis.orchestrator import process_analysis_job
from shiftos.services.ingestion.worker import run_once


def synthetic_programme(session, discipline="computing", count=3):
    institution = Institution(name="Synthetic Phase 4 worker university", is_synthetic=True)
    session.add(institution)
    session.flush()
    programme = Programme(
        institution_id=institution.id,
        name=f"Synthetic {discipline} programme",
        discipline_key=discipline,
        is_synthetic=True,
    )
    session.add(programme)
    session.flush()
    revision = ProgrammeRevision(
        programme_id=programme.id,
        version_label="synthetic-phase4-1",
        is_synthetic=True,
    )
    session.add(revision)
    session.flush()
    programme.active_revision_id = revision.id
    for index in range(count):
        session.add(
            Course(
                programme_revision_id=revision.id,
                course_name=f"Synthetic {discipline} course {index}",
                is_synthetic=True,
            )
        )
    session.commit()
    return programme


def settings():
    return Settings(_env_file=None, app_env="test", database_url="sqlite+pysqlite:///:memory:")


@pytest.mark.parametrize("discipline", ["computing", "business", "biotechnology"])
def test_offline_existing_worker_returns_every_course_without_network(
    database, session, monkeypatch, discipline
):
    programme = synthetic_programme(session, discipline)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(mode="offline"))
    from shiftos.services.analysis.providers import BraveSearch, GeminiProvider

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline execution must not call any provider")

    monkeypatch.setattr(GeminiProvider, "generate", forbidden)
    monkeypatch.setattr(BraveSearch, "search", forbidden)
    assert run_once(database, settings()) == run.job_id
    session.expire_all()
    job = session.get(Job, run.job_id)
    assert job.status == JobStatus.SUCCEEDED, job.error
    findings = session.scalars(select(CourseFinding).where(CourseFinding.run_id == run.id)).all()
    assert len(findings) == 3
    assert all(row.result_json["is_final_curriculum_verdict"] is False for row in findings)
    assert session.get(AnalysisRun, run.id).summary_json["is_synthetic"] is True
    assert session.get(AnalysisRun, run.id).fingerprint
    assert run_once(database, settings()) is None


def test_changed_inventory_fails_instead_of_silently_adding_courses(database, session):
    programme = synthetic_programme(session)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(mode="offline"))
    session.add(
        Course(
            programme_revision_id=run.programme_revision_id,
            course_name="Synthetic late course",
            is_synthetic=True,
        )
    )
    session.commit()
    run_once(database, settings())
    session.expire_all()
    assert session.get(Job, run.job_id).status == JobStatus.FAILED
    assert "CURRICULUM_CHANGED" in session.get(Job, run.job_id).error
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 0


def test_missing_live_model_persists_partial_all_course_insufficiency(database, session):
    programme = synthetic_programme(session)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(mode="live", research=False))
    run_once(database, settings())
    session.expire_all()
    job = session.get(Job, run.job_id)
    assert job.status == JobStatus.PARTIAL, job.error
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 3
    assert "model_disabled" in job.result_json["model_processing"]["reasons"]
    assert session.get(AnalysisRun, run.id).summary_json["result_mode"] != "live_model"


def test_invalid_model_output_repaired_once_then_abstains(database, session):
    programme = synthetic_programme(session)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(research=False))
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC)
    session.commit()
    calls = []

    class UnsupportedModel:
        def __init__(self, settings):
            pass

        def generate(self, packet, schema):
            calls.append(packet)
            return {"fabricated_score": 98, "courses": []}

    process_analysis_job(database, job, settings(), provider_factory=UnsupportedModel)
    session.expire_all()
    assert len(calls) == 2
    assert session.get(Job, job.id).status == JobStatus.PARTIAL
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 3
    assert "fabricated_score" not in str(session.get(AnalysisRun, run.id).summary_json)


def test_stale_worker_cannot_publish_after_operator_failure(database, session):
    programme = synthetic_programme(session)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(research=False))
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC)
    session.commit()

    class InterruptedModel:
        def __init__(self, settings):
            pass

        def generate(self, packet, schema):
            from shiftos.schemas.analysis import EvidencePacket
            from shiftos.services.analysis.validation import offline_result

            with database.session_factory() as operation:
                stopped = operation.get(Job, job.id)
                stopped.status, stopped.completed_at = JobStatus.FAILED, datetime.now(UTC)
                stopped.error = "Synthetic operator recovery"
                operation.commit()
            result = offline_result(EvidencePacket.model_validate(packet)).model_dump(mode="json")
            result["result_mode"] = "live_model"
            return result

    process_analysis_job(database, job, settings(), provider_factory=InterruptedModel)
    session.expire_all()
    assert session.get(Job, job.id).error == "Synthetic operator recovery"
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 0


def test_model_batches_preserve_complete_inventory_and_source_boundaries(database, session):
    """The fake provider returns safe synthetic statements; it is not live Gemini."""
    programme = synthetic_programme(session, count=45)
    run = enqueue_analysis(session, programme.id, AnalysisRequest(research=False))
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC)
    session.commit()
    batches = []

    class SyntheticStructuredModel:
        def __init__(self, settings):
            pass

        def generate(self, payload, schema):
            from shiftos.schemas.analysis import EvidencePacket
            from shiftos.services.analysis.validation import offline_result

            packet = EvidencePacket.model_validate(payload)
            batches.append([course.id for course in packet.courses])
            reference_ids = {item.id for item in packet.references if item.model_eligible}
            assert all(
                row["before_reference_id"] in reference_ids
                and row["after_reference_id"] in reference_ids
                for row in packet.radar
            )
            result = offline_result(packet).model_dump(mode="json")
            result["result_mode"] = "live_model"
            return result

    process_analysis_job(database, job, settings(), provider_factory=SyntheticStructuredModel)
    session.expire_all()
    stored = session.get(Job, job.id)
    assert stored.status == JobStatus.SUCCEEDED, stored.error
    assert list(map(len, batches)) == [20, 20, 5]
    assert len({course for batch in batches for course in batch}) == 45
    assert session.scalar(select(func.count()).select_from(CourseFinding)) == 45
    assert stored.result_json["summary"]["insufficient_evidence_count"] == 45
    assert stored.result_json["model_processing"]["validated_model_courses"] == 45
