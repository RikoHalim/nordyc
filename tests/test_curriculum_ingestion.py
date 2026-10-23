"""Offline ingestion contracts: every institution, page and course is fictional.

Tests deliberately exercise both synthetic and nonsynthetic flags in an isolated
database. Nonsynthetic test flags simulate reviewed public provenance; they do
not represent real university collection. No test makes external HTTP requests.
"""

import copy
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shiftos.core.enums import JobStatus
from shiftos.db.session import Database
from shiftos.models import (
    Course,
    Document,
    DocumentAnchor,
    Job,
    Programme,
    ProgrammeRevision,
    Source,
)
from shiftos.services.ingestion import worker
from shiftos.services.ingestion.fetcher import FetchedPage, FetchError
from shiftos.services.ingestion.parsers import XmumCurriculumParser

BASE = "https://www.example.invalid"
FIXTURES = Path(__file__).parent / "fixtures" / "curriculum"


def _institution(client: TestClient, *, synthetic: bool = True, host: str = BASE) -> dict:
    response = client.post(
        "/api/v1/institutions",
        json={
            "name": "Fictional Curriculum Test University",
            "website_url": host,
            "is_synthetic": synthetic,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _course(title: str = "Synthetic Foundations", **changes) -> dict:
    return {
        "course_name": title,
        "year": 1,
        "source_locator": "#curriculum > ul > li:nth-of-type(1)",
        "source_excerpt": title,
        **changes,
    }


def _manifest(**changes) -> dict:
    return {
        "name": "Bachelor of Synthetic Studies",
        "canonical_url": f"{BASE}/courses/synthetic-studies",
        "source_url": f"{BASE}/courses/synthetic-studies",
        "source_locator": "#curriculum",
        "retrieved_at": "2026-10-20T00:00:00Z",
        "reviewed": True,
        "courses": [_course()],
        **changes,
    }


def _enqueue(client: TestClient, institution: dict, manifest: dict, *, key=None) -> dict:
    body = {"is_synthetic": institution["is_synthetic"], "programmes": [manifest]}
    if key is not None:
        body["idempotency_key"] = key
    response = client.post(f"/api/v1/institutions/{institution['id']}/imports", json=body)
    assert response.status_code == 202, response.text
    return response.json()


def _run(client: TestClient, database: Database, job: dict, **options) -> dict:
    assert worker.run_once(database, client.app.state.settings, **options) == UUID(job["id"])
    response = client.get(f"/api/v1/catalogue/jobs/{job['id']}")
    assert response.status_code == 200, response.text
    return response.json()


def _import(client: TestClient, database: Database, institution: dict, manifest: dict) -> dict:
    job = _run(client, database, _enqueue(client, institution, manifest))
    assert job["status"] == "SUCCEEDED", job
    return job["result"]["entries"][0]


def _counts(database: Database) -> dict:
    with database.session_factory() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (Programme, ProgrammeRevision, Course, Source, Document, DocumentAnchor)
        }


def _courses(client: TestClient, programme_id: str, revision_id: str | None = None) -> dict:
    path = f"/api/v1/programmes/{programme_id}"
    if revision_id:
        path += f"/revisions/{revision_id}"
    response = client.get(path + "/courses")
    assert response.status_code == 200, response.text
    return response.json()


def test_synthetic_import_queues_then_worker_persists_and_fastapi_retrieves(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    queued = _enqueue(client, institution, _manifest())
    assert queued["status"] == "QUEUED"
    assert queued["started_at"] is None
    assert _counts(database)["courses"] == 0
    finished = _run(client, database, queued)
    assert finished["status"] == "SUCCEEDED"
    assert finished["started_at"] is not None and finished["completed_at"] is not None
    assert finished["is_synthetic"] is True
    outcome = finished["result"]["entries"][0]
    page = _courses(client, outcome["programme_id"])
    assert page["total"] == 1
    course = page["items"][0]
    assert course["is_synthetic"] is True
    assert course["is_verified"] is False
    assert course["course_type"] == "UNKNOWN"
    assert course["semester"] is None
    assert course["source_url"] == _manifest()["source_url"]
    assert course["evidence_level"] == "title_only"
    assert "syllabus" in course["missing_fields"]
    assert client.get(f"/api/v1/courses/{course['id']}").json() == course
    programmes = client.get(f"/api/v1/institutions/{institution['id']}/programmes").json()
    assert programmes["total"] == 1
    assert programmes["items"][0]["id"] == outcome["programme_id"]
    coverage = client.get(f"/api/v1/programmes/{outcome['programme_id']}/coverage").json()
    assert coverage["course_count"] == coverage["title_only_count"] == 1
    assert coverage["verified_title_count"] == 0
    assert coverage["graduation_curriculum_complete"] is False
    assert coverage["metadata"]["retrieved_at"].startswith("2026-10-20")
    sources = client.get("/api/v1/sources").json()
    assert sources["items"][0]["evidence_class"] == "synthetic_demo"


@pytest.mark.parametrize("synthetic", [False, True])
def test_legacy_syllabus_availability_keeps_real_and_synthetic_labels_distinct(
    client: TestClient, database: Database, synthetic: bool
) -> None:
    institution = _institution(client, synthetic=synthetic)
    outcome = _import(client, database, institution, _manifest())
    course = _courses(client, outcome["programme_id"])["items"][0]
    with database.session_factory() as session:
        stored = session.get(Course, UUID(course["id"]))
        stored.detailed_syllabus_available = True
        session.commit()
    refreshed = client.get(f"/api/v1/courses/{course['id']}").json()
    assert refreshed["evidence_level"] == ("synthetic_detail" if synthetic else "detailed_syllabus")


@pytest.mark.parametrize("reviewed", [False, True])
def test_manual_review_assertion_is_distinct_from_syllabus_evidence(
    client: TestClient, database: Database, reviewed: bool
) -> None:
    institution = _institution(client, synthetic=False)
    course = _course(review_notes=["title_only", "needs_syllabus_confirmation"])
    outcome = _import(client, database, institution, _manifest(reviewed=reviewed, courses=[course]))
    stored = _courses(client, outcome["programme_id"])["items"][0]
    assert stored["is_verified"] is reviewed
    assert stored["detailed_syllabus_available"] is False
    assert stored["extraction_status"] == ("INVENTORY_ONLY" if reviewed else "NEEDS_REVIEW")
    source = client.get(f"/api/v1/sources/{stored['source_id']}").json()
    assert source["evidence_class"] == ("verified_university_fact" if reviewed else "inference")


def test_exact_duplicate_rows_skip_but_distinct_year_and_elective_groups_survive(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    original = _course()
    next_year = _course(year=2, source_locator="#year2 > li")
    elective_a = _course(
        course_type="ELECTIVE", elective_group="Choose A", source_locator="#pool-a > li"
    )
    elective_b = _course(
        course_type="ELECTIVE", elective_group="Choose B", source_locator="#pool-b > li"
    )
    outcome = _import(
        client,
        database,
        institution,
        _manifest(courses=[original, copy.deepcopy(original), next_year, elective_a, elective_b]),
    )
    assert outcome["course_count"] == 4
    assert outcome["duplicate_rows_skipped"] == 1
    courses = _courses(client, outcome["programme_id"])["items"]
    assert sorted(item["year"] for item in courses) == [1, 1, 1, 2]
    assert {item["elective_group"] for item in courses} == {None, "Choose A", "Choose B"}


def test_reimport_does_not_duplicate_sources_revisions_courses_or_anchors(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    manifest = _manifest()
    initial = _import(client, database, institution, manifest)
    counts = _counts(database)
    manifest["retrieved_at"] = "2026-10-21T00:00:00Z"
    repeated = _import(client, database, institution, manifest)
    assert repeated["status"] == "unchanged"
    assert repeated["revision_id"] == initial["revision_id"]
    assert _counts(database) == counts


def test_idempotency_key_reuses_job_and_rejects_conflicting_request(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    initial = _enqueue(client, institution, _manifest(), key="offline-import-1")
    repeated = _enqueue(client, institution, _manifest(), key="offline-import-1")
    assert repeated["id"] == initial["id"]
    changed = _manifest(courses=[_course("Synthetic Different Title")])
    response = client.post(
        f"/api/v1/institutions/{institution['id']}/imports",
        json={"is_synthetic": True, "programmes": [changed], "idempotency_key": "offline-import-1"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    _run(client, database, initial)
    assert _enqueue(client, institution, _manifest(), key="offline-import-1")["id"] == initial["id"]
    assert worker.run_once(database, client.app.state.settings) is None


def test_new_snapshot_preserves_old_revision_and_replay_does_not_reactivate_old_data(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    original = _manifest()
    first = _import(client, database, institution, original)
    changed = _manifest(
        retrieved_at="2026-10-21T00:00:00Z", courses=[_course("Synthetic Revised Foundations")]
    )
    second = _import(client, database, institution, changed)
    assert second["programme_id"] == first["programme_id"]
    assert second["revision_id"] != first["revision_id"]
    assert (
        _courses(client, first["programme_id"])["items"][0]["course_name"]
        == "Synthetic Revised Foundations"
    )
    historical = _courses(client, first["programme_id"], first["revision_id"])
    assert historical["items"][0]["course_name"] == "Synthetic Foundations"
    replay = _import(client, database, institution, original)
    assert replay["status"] == "unchanged" and replay["active"] is False
    degree = client.get(f"/api/v1/programmes/{first['programme_id']}").json()
    assert degree["active_revision_id"] == second["revision_id"]
    revisions = client.get(f"/api/v1/programmes/{first['programme_id']}/revisions").json()
    assert revisions["total"] == 2
    forbidden = client.post(
        f"/api/v1/programmes/{first['programme_id']}/courses",
        json={"course_name": "Synthetic Attempted Mutation"},
    )
    assert forbidden.status_code == 409


def test_older_newly_supplied_manifest_is_historical_and_cannot_roll_back_active_snapshot(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    current = _import(client, database, institution, _manifest())
    older = _manifest(
        retrieved_at="2026-10-19T00:00:00Z", courses=[_course("Synthetic Archived Foundations")]
    )
    historical = _import(client, database, institution, older)
    assert historical["status"] == "historical" and historical["active"] is False
    degree = client.get(f"/api/v1/programmes/{current['programme_id']}").json()
    assert degree["active_revision_id"] == current["revision_id"]
    archived = _courses(client, current["programme_id"], historical["revision_id"])
    assert archived["items"][0]["course_name"] == "Synthetic Archived Foundations"


def test_exact_maximum_locator_survives_while_anchor_explicitly_points_to_manifest(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    locator = "x" * 500
    outcome = _import(
        client, database, institution, _manifest(courses=[_course(source_locator=locator)])
    )
    course = _courses(client, outcome["programme_id"])["items"][0]
    assert course["source_locator"] == locator
    with database.session_factory() as session:
        anchor = session.get(DocumentAnchor, UUID(course["inventory_source_anchor_id"]))
        assert anchor.excerpt == course["course_name"]
        assert anchor.locator == "/courses/0/source_excerpt"
        assert "manifest" in anchor.section_label


def test_conflicting_same_locator_and_same_title_at_distinct_locators_need_review(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client, synthetic=False)
    first = _course()
    conflict = _course("Synthetic Conflicting Title")
    repeated = _course(source_locator="#duplicate-copy > li")
    outcome = _import(client, database, institution, _manifest(courses=[first, conflict, repeated]))
    courses = _courses(client, outcome["programme_id"])["items"]
    assert len(courses) == 3
    assert all(item["is_verified"] is False for item in courses)
    assert all(item["extraction_status"] == "NEEDS_REVIEW" for item in courses)
    assert any("Conflicting facts" in note for item in courses for note in item["review_notes"])
    assert any("Possible duplicate" in note for item in courses for note in item["review_notes"])


@pytest.mark.parametrize(
    ("url", "status"),
    [
        ("https://untrusted.invalid/courses/synthetic", 422),
        ("http://www.example.invalid/courses/synthetic", 422),
        ("https://user:password@example.invalid/courses/synthetic", 422),
        ("https://www.example.invalid:8443/courses/synthetic", 422),
    ],
)
def test_foreign_or_unsafe_source_origin_is_rejected_without_queueing(
    client: TestClient, database: Database, url: str, status: int
) -> None:
    institution = _institution(client)
    response = client.post(
        f"/api/v1/institutions/{institution['id']}/imports",
        json={"is_synthetic": True, "programmes": [_manifest(source_url=url)]},
    )
    assert response.status_code == status
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_import_cannot_cross_real_synthetic_lane_or_ambiguous_programme_identity(
    client: TestClient,
) -> None:
    institution = _institution(client)
    path = f"/api/v1/institutions/{institution['id']}/imports"
    response = client.post(path, json={"is_synthetic": False, "programmes": [_manifest()]})
    assert response.status_code == 409
    duplicate_identity = _manifest(
        canonical_url="https://example.invalid/courses/synthetic-studies/"
    )
    response = client.post(
        path, json={"is_synthetic": True, "programmes": [_manifest(), duplicate_identity]}
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"courses": []},
        {"courses": [_course(year=True)]},
        {"courses": [_course(year=0)]},
        {"courses": [_course(semester=-1)]},
        {"courses": [_course(course_name="Not present in the actual excerpt")]},
        {"courses": [_course(source_locator="")]},
        {"courses": [_course(course_name="x" * 256, source_excerpt="x" * 256)]},
        {"courses": [_course(invented_syllabus="Unsupported")]},
        {"retrieved_at": "2026-10-20T00:00:00"},
        {"retrieved_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
        {"made_up_field": "Unsupported"},
    ],
)
def test_malformed_manifests_return_documented_validation_error(
    client: TestClient, changes: dict
) -> None:
    institution = _institution(client)
    response = client.post(
        f"/api/v1/institutions/{institution['id']}/imports",
        json={"is_synthetic": True, "programmes": [_manifest(**changes)]},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]


def test_programme_specific_import_validates_identity_and_revisions_cannot_cross_programmes(
    client: TestClient, database: Database
) -> None:
    institution = _institution(client)
    first = _import(client, database, institution, _manifest())
    other = _import(
        client,
        database,
        institution,
        _manifest(name="Bachelor of Synthetic Other", canonical_url=f"{BASE}/courses/other"),
    )
    response = client.post(
        f"/api/v1/programmes/{first['programme_id']}/imports",
        json={**_manifest(canonical_url=f"{BASE}/courses/other"), "is_synthetic": True},
    )
    assert response.status_code == 409
    for endpoint in (
        f"/api/v1/programmes/{first['programme_id']}/revisions/{other['revision_id']}/courses",
        f"/api/v1/programmes/{first['programme_id']}/coverage?revision_id={other['revision_id']}",
    ):
        assert client.get(endpoint).status_code == 404
    response = client.post(
        f"/api/v1/programmes/{first['programme_id']}/imports",
        json={**_manifest(), "is_synthetic": True, "idempotency_key": "specific-programme"},
    )
    assert response.status_code == 202
    assert _run(client, database, response.json())["status"] == "SUCCEEDED"


def _fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        worker.PROVIDERS,
        "xmum",
        {
            "name": "Fictional Offline Provider",
            "website_url": BASE + "/",
            "directory_url": BASE + "/undergraduate-programmes",
            "allowed_hosts": ("www.example.invalid", "example.invalid"),
            "parser": XmumCurriculumParser,
        },
    )


class _FixtureFetcher:
    """Explicit injected offline transport; never instantiate an HTTP client."""

    calls: list[str] = []
    fail_all = False

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def fetch_html(self, url: str) -> FetchedPage:
        self.calls.append(url)
        if self.fail_all:
            raise FetchError("NETWORK_ERROR", "Synthetic offline failure")
        filename = {
            "undergraduate-programmes": "directory.html",
            "bachelor-synthetic-commerce": "commerce.html",
            "bachelor-synthetic-literature": "literature.html",
            "bachelor-synthetic-marine-science": "science.html",
        }.get(url.rsplit("/", 1)[-1])
        if filename is None:
            raise FetchError("NETWORK_ERROR", "Synthetic unavailable programme page")
        html = (FIXTURES / filename).read_text(encoding="utf-8")
        return FetchedPage(
            url=url,
            html=html,
            sha256=hashlib.sha256(html.encode()).hexdigest(),
            retrieved_at=datetime(2026, 10, 20, tzinfo=UTC),
        )


def test_discovery_partial_failure_retains_all_discovered_programmes_and_reports_coverage(
    client: TestClient, database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_provider(monkeypatch)
    monkeypatch.setattr(_FixtureFetcher, "calls", [])
    institution = _institution(client, synthetic=False)
    response = client.post(f"/api/v1/institutions/{institution['id']}/discover", json={})
    assert response.status_code == 202
    assert _FixtureFetcher.calls == []
    completed = _run(client, database, response.json(), fetcher_factory=_FixtureFetcher)
    assert completed["status"] == "PARTIAL", completed
    assert completed["result"]["discovered_programmes"] == 4
    assert completed["result"]["imported_programmes"] == 3
    assert completed["result"]["failed_programmes"] == 1
    assert len(_FixtureFetcher.calls) == 5
    programmes = client.get(f"/api/v1/institutions/{institution['id']}/programmes").json()
    assert programmes["total"] == 4
    entries = completed["result"]["entries"]
    failed = next(entry for entry in entries if entry["status"] == "failed")
    failed_coverage = client.get(f"/api/v1/programmes/{failed['programme_id']}/coverage").json()
    assert failed_coverage["course_count"] == 0
    assert failed_coverage["programme_revision_id"] is None
    assert failed["error_code"] == "NETWORK_ERROR"
    assert "structured JSON" in failed["message"]
    for entry in entries:
        if entry["status"] == "imported":
            assert _courses(client, entry["programme_id"])["total"] > 0
    counts = _counts(database)
    response = client.post(f"/api/v1/institutions/{institution['id']}/discover", json={})
    repeated = _run(client, database, response.json(), fetcher_factory=_FixtureFetcher)
    assert repeated["status"] == "PARTIAL"
    assert repeated["result"]["unchanged_programmes"] == 3
    assert _counts(database) == counts


def test_discovery_network_failure_reports_manual_fallback_then_structured_import_succeeds(
    client: TestClient, database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_provider(monkeypatch)
    monkeypatch.setattr(_FixtureFetcher, "fail_all", True)
    institution = _institution(client, synthetic=False)
    response = client.post(f"/api/v1/institutions/{institution['id']}/discover", json={})
    assert response.status_code == 202
    failed = _run(client, database, response.json(), fetcher_factory=_FixtureFetcher)
    assert failed["status"] == "FAILED"
    assert "NETWORK_ERROR" in failed["error"]
    assert "structured JSON" in failed["error"]
    assert _counts(database)["courses"] == 0
    result = _import(client, database, institution, _manifest())
    assert _courses(client, result["programme_id"])["total"] == 1


def test_missing_resources_and_provider_lineage_return_documented_errors(
    client: TestClient,
) -> None:
    for endpoint in (
        f"/api/v1/catalogue/jobs/{uuid4()}",
        f"/api/v1/programmes/{uuid4()}/coverage",
        f"/api/v1/programmes/{uuid4()}/revisions",
    ):
        response = client.get(endpoint)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
    institution = _institution(client)
    response = client.post(f"/api/v1/institutions/{institution['id']}/discover", json={})
    assert response.status_code == 409


def test_stale_job_recovery_is_explicit_and_does_not_replay_completed_work(
    client: TestClient, database: Database, session: Session
) -> None:
    institution = _institution(client)
    queued = _enqueue(client, institution, _manifest())
    stored = session.get(Job, UUID(queued["id"]))
    stored.status = JobStatus.RUNNING
    stored.started_at = datetime.now(UTC) - timedelta(hours=2)
    session.commit()
    assert worker.run_once(database, client.app.state.settings) is None
    assert worker.fail_stale_jobs(database) == 1
    session.refresh(stored)
    assert stored.status == JobStatus.FAILED
    assert "STALE_WORKER" in stored.error
    assert worker.fail_stale_jobs(database) == 0
    assert _counts(database)["courses"] == 0
