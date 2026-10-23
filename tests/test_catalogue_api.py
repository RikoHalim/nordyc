"""Phase 1 catalogue contracts. All values and reserved .invalid URLs are test data."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shiftos.services.ingestion.fixtures import import_fixture


def institution(client: TestClient, *, synthetic: bool = True) -> dict:
    response = client.post(
        "/api/v1/institutions",
        json={"name": "Test University (fictional)", "is_synthetic": synthetic},
    )
    assert response.status_code == 201
    return response.json()


def programme(client: TestClient, institution_id: str, **values) -> dict:
    response = client.post(
        f"/api/v1/institutions/{institution_id}/programmes",
        json={"name": "Test Programme (fictional)", **values},
    )
    assert response.status_code == 201
    return response.json()


def source(client: TestClient, **values) -> dict:
    response = client.post(
        "/api/v1/sources",
        json={
            "publisher": "Test Publisher (fictional)",
            "title": "Test Catalogue",
            "url": "https://catalogue.invalid/courses",
            **values,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_multiple_institutions_and_disciplines_have_separate_complete_inventories(
    client: TestClient,
):
    university = institution(client)
    other = institution(client)
    assert client.get(f"/api/v1/institutions/{university['id']}").json() == university
    programmes = []
    for discipline in ("computing", "business", "communication"):
        degree = programme(
            client,
            university["id"],
            name=f"Synthetic {discipline}",
            discipline_key=discipline,
            level="undergraduate",
        )
        programmes.append(degree)
        for year in (1, 2, None):
            response = client.post(
                f"/api/v1/programmes/{degree['id']}/courses",
                json={"course_name": "Research Methods (Synthetic)", "year": year},
            )
            assert response.status_code == 201
            course = response.json()
            assert course["year"] == year
            assert course["semester"] is None
            assert course["course_type"] == "UNKNOWN"
            assert course["source_id"] is None
            assert course["is_verified"] is False
            assert course["detailed_syllabus_available"] is False
            assert course["extraction_status"] == "INVENTORY_ONLY"
            assert course["data_quality"] == "synthetic"
            assert client.get(f"/api/v1/courses/{course['id']}").json() == course
    unrelated = programme(client, other["id"])
    listed = []
    for offset in range(3):
        page = client.get(
            f"/api/v1/institutions/{university['id']}/programmes?limit=1&offset={offset}"
        ).json()
        assert page["total"] == 3
        listed.extend(page["items"])
    assert {row["id"] for row in listed} == {row["id"] for row in programmes}
    assert unrelated["id"] not in {row["id"] for row in listed}
    for degree in programmes:
        page = client.get(f"/api/v1/programmes/{degree['id']}/courses").json()
        assert page["total"] == 3
        assert {row["programme_revision_id"] for row in page["items"]} == {
            degree["active_revision_id"]
        }


def test_minimal_nonsynthetic_records_are_explicitly_incomplete(client: TestClient):
    university = institution(client, synthetic=False)
    degree = programme(client, university["id"])
    response = client.post(
        f"/api/v1/programmes/{degree['id']}/courses", json={"course_name": "Test Title"}
    )
    assert response.status_code == 201
    for record in (university, degree, response.json()):
        assert record["data_quality"] == "incomplete"
        assert record["source_id"] is None
        assert record["is_synthetic"] is False


def test_source_dates_and_catalogue_assertion_are_traceable_without_claiming_syllabus(
    client: TestClient,
):
    origin = source(
        client,
        evidence_class="verified_university_fact",
        collected_at="2026-10-24T08:00:00+08:00",
        content_hash="a" * 64,
    )
    assert origin["published_at"] is None
    assert origin["observed_at"] is None
    assert origin["collected_at"] == "2026-10-24T00:00:00Z"
    assert client.get(f"/api/v1/sources/{origin['id']}").json() == origin
    university = client.post(
        "/api/v1/institutions",
        json={
            "name": "Fictional Source Test University",
            "source_id": origin["id"],
            "source_locator": "University heading",
            "website_url": "https://catalogue.invalid/",
        },
    ).json()
    degree = programme(
        client, university["id"], source_id=origin["id"], source_locator="Programme heading"
    )
    assert university["data_quality"] == degree["data_quality"] == "source_attributed"
    response = client.post(
        f"/api/v1/programmes/{degree['id']}/courses",
        json={
            "course_name": "Fictional Course",
            "source_id": origin["id"],
            "source_locator": "Year 2, row 4",
            "is_verified": True,
            "year": 2,
            "semester": 1,
            "course_type": "ELECTIVE",
            "credit_hours": "3.00",
        },
    )
    assert response.status_code == 201
    course = response.json()
    assert course["data_quality"] == "verified_catalogue"
    assert course["source_id"] == origin["id"]
    assert course["detailed_syllabus_available"] is False
    assert "learning_outcomes" not in course


@pytest.mark.parametrize(
    "payload",
    [
        {"url": None},
        {"url": "file:///private/data"},
        {"url": "not-a-url"},
        {"evidence_class": "synthetic_demo"},
        {"is_synthetic": True},
        {"evidence_class": "invented"},
        {"published_at": "2026-10-24T00:00:00"},
        {"content_hash": "x" * 64},
        {"publisher": " "},
    ],
)
def test_invalid_source_metadata_is_rejected_before_persistence(client: TestClient, payload: dict):
    response = client.post(
        "/api/v1/sources",
        json={
            "publisher": "Test",
            "title": "Test",
            "url": "https://source.invalid/",
            **payload,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get("/api/v1/sources").json()["total"] == 0


def test_synthetic_source_propagates_and_cannot_become_verified(client: TestClient):
    origin = source(client, url=None, is_synthetic=True, evidence_class="synthetic_demo")
    university = institution(client, synthetic=False)
    degree = programme(client, university["id"], source_id=origin["id"])
    assert degree["is_synthetic"] is True
    assert degree["active_revision"]["is_synthetic"] is True
    path = f"/api/v1/programmes/{degree['id']}/courses"
    response = client.post(
        path,
        json={
            "course_name": "Test",
            "source_id": origin["id"],
            "source_locator": "test-row",
            "is_verified": True,
        },
    )
    assert response.status_code == 409
    assert client.get(path).json()["total"] == 0
    response = client.post(path, json={"course_name": "Test", "source_id": origin["id"]})
    assert response.status_code == 201
    assert response.json()["is_synthetic"] is True


@pytest.mark.parametrize(
    "evidence_class",
    [
        "published_standard",
        "occupation_requirement",
        "dated_workforce_signal",
        "dated_ai_capability",
        "inference",
    ],
)
def test_benchmarks_cannot_verify_university_teaching(client: TestClient, evidence_class: str):
    origin = source(client, evidence_class=evidence_class)
    degree = programme(client, institution(client, synthetic=False)["id"])
    path = f"/api/v1/programmes/{degree['id']}/courses"
    response = client.post(
        path,
        json={
            "course_name": "Test",
            "source_id": origin["id"],
            "source_locator": "test-row",
            "is_verified": True,
        },
    )
    assert response.status_code == 409
    assert client.get(path).json()["total"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"year": 0},
        {"year": True},
        {"year": 2.5},
        {"semester": -1},
        {"course_name": " "},
        {"credit_hours": "-1"},
        {"course_type": "OBSOLETE"},
        {"is_verified": True},
        {"source_locator": " "},
        {"detailed_syllabus_available": True},
    ],
)
def test_course_validation_does_not_create_partial_rows(client: TestClient, payload: dict):
    degree = programme(client, institution(client)["id"])
    path = f"/api/v1/programmes/{degree['id']}/courses"
    response = client.post(path, json={"course_name": "Test", **payload})
    assert response.status_code == 422
    assert client.get(path).json()["total"] == 0


@pytest.mark.parametrize(
    "path",
    [
        "/institutions/{id}",
        "/institutions/{id}/programmes",
        "/courses/{id}",
        "/sources/{id}",
    ],
)
def test_new_read_routes_return_documented_missing_resource(client: TestClient, path: str):
    response = client.get("/api/v1" + path.format(id=uuid4()))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_missing_source_rejects_creation_and_rollback_allows_next_request(client: TestClient):
    degree = programme(client, institution(client)["id"])
    path = f"/api/v1/programmes/{degree['id']}/courses"
    response = client.post(path, json={"course_name": "Test", "source_id": str(uuid4())})
    assert response.status_code == 404
    assert client.get(path).json()["total"] == 0
    assert client.post(path, json={"course_name": "Valid Test"}).status_code == 201


def test_fixture_revisions_cannot_be_modified_by_course_api(
    client: TestClient,
    session: Session,
    fixture_path: Path,
):
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    import_fixture(session, fixture_path)
    session.commit()
    path = f"/api/v1/programmes/{fixture['programme']['id']}/courses"
    assert client.post(path, json={"course_name": "Additional Test"}).status_code == 409
    assert client.get(path).json()["total"] == len(fixture["courses"])
    assert import_fixture(session, fixture_path).created is False


def test_source_pagination_and_health_alias(client: TestClient):
    for _ in range(3):
        source(client, is_synthetic=True, evidence_class="synthetic_demo", url=None)
    pages = [client.get(f"/api/v1/sources?limit=2&offset={offset}").json() for offset in (0, 2)]
    assert all(page["total"] == 3 for page in pages)
    assert len({row["id"] for page in pages for row in page["items"]}) == 3
    assert client.get("/api/v1/sources?limit=101").status_code == 422
    assert client.get("/health").json() == {"status": "alive"}
