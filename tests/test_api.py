import json
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from shiftos.db.session import Database
from shiftos.models import Course, ProgrammeRevision
from shiftos.services.ingestion.fixtures import import_fixture


def create_programme(client: TestClient) -> dict:
    institution = client.post(
        "/api/v1/institutions", json={"name": "Synthetic University", "is_synthetic": True}
    )
    assert institution.status_code == 201
    response = client.post(
        "/api/v1/programmes",
        json={
            "institution_id": institution.json()["id"],
            "name": "Synthetic Software Engineering",
            "programme_code": "DEMO-SE",
            "academic_year": "2026/2027",
            "version_label": "2026-demo",
            "effective_date": "2026-10-01",
            "is_synthetic": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health_and_openapi(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "alive"}
    readiness = client.get("/health/ready")
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready"}
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert paths["/api/v1/institutions"]["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert paths["/api/v1/programmes/{id}/courses"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert all("analyses" not in path and "documents" not in path for path in paths)


def test_liveness_is_independent_of_database_and_readiness_redacts_failure(
    client: TestClient, database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "do-not-disclose-database-credentials"

    def unavailable(*args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, RuntimeError(secret))

    monkeypatch.setattr(database.engine, "connect", unavailable)
    assert client.get("/health/live").status_code == 200
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert isinstance(response.json()["error"]["details"], list)
    assert secret not in response.text
    assert "SELECT 1" not in response.text


def test_create_list_and_read_programme(client: TestClient) -> None:
    programme = create_programme(client)
    UUID(programme["id"])
    assert programme["is_synthetic"] is True
    assert programme["active_revision_id"] == programme["active_revision"]["id"]
    assert programme["active_revision"]["programme_id"] == programme["id"]
    assert programme["active_revision"]["version_label"] == "2026-demo"
    assert programme["active_revision"]["effective_date"] == "2026-10-01"
    assert programme["active_revision"]["is_synthetic"] is True
    for field in ("created_at", "updated_at"):
        assert (
            datetime.fromisoformat(programme[field].replace("Z", "+00:00")).utcoffset() is not None
        )
    assert client.get(f"/api/v1/programmes/{programme['id']}").json() == programme

    institutions = client.get("/api/v1/institutions").json()
    assert institutions["total"] == 1
    assert institutions["items"][0]["country"] == "MY"
    assert institutions["items"][0]["id"] == programme["institution_id"]
    programmes = client.get("/api/v1/programmes?limit=1&offset=0").json()
    assert programmes["total"] == 1
    assert programmes["items"][0]["id"] == programme["id"]
    empty = client.get(f"/api/v1/programmes/{programme['id']}/courses").json()
    assert empty == {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0,
        "programme_revision_id": programme["active_revision_id"],
    }


def test_course_pages_include_entire_inventory_and_missing_syllabi(
    client: TestClient, session: Session, fixture_path: Path
) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    import_fixture(session, fixture_path)
    session.commit()
    programme_id = fixture["programme"]["id"]
    revision_id = UUID(fixture["programme"]["revision_id"])
    session.add_all(
        Course(
            programme_revision_id=revision_id,
            course_code=f"SYN-{number:03}",
            course_name=f"Synthetic Additional Course {number}",
            is_synthetic=True,
        )
        for number in range(101)
    )
    session.commit()
    expected_ids = {str(course.id) for course in session.scalars(select(Course))}
    assert len(expected_ids) > 100
    actual: dict[str, dict] = {}
    for offset in range(0, len(expected_ids), 7):
        response = client.get(f"/api/v1/programmes/{programme_id}/courses?limit=7&offset={offset}")
        assert response.status_code == 200
        page = response.json()
        assert page["total"] == len(expected_ids)
        assert page["programme_revision_id"] == str(revision_id)
        assert page["limit"] == 7
        assert page["offset"] == offset
        for course in page["items"]:
            assert course["id"] not in actual
            assert course["is_synthetic"] is True
            actual[course["id"]] = course
    assert set(actual) == expected_ids
    for course in fixture["courses"]:
        record = actual[course["id"]]
        assert record["course_type"] == course["course_type"]
        assert record["detailed_syllabus_available"] == course["detailed_syllabus_available"]
        assert record["inventory_source_anchor_id"] == course["inventory_anchor"]["id"]
        assert "relevance_score" not in record
        assert "learning_outcomes" not in record
    assert {item["course_type"] for item in actual.values()} >= {"COMPULSORY", "ELECTIVE"}
    beyond = client.get(
        f"/api/v1/programmes/{programme_id}/courses?offset={len(expected_ids)}"
    ).json()
    assert beyond["items"] == []
    assert beyond["total"] == len(expected_ids)


def test_course_inventory_uses_only_requested_programmes_active_revision(
    client: TestClient, session: Session
) -> None:
    first = create_programme(client)
    second = create_programme(client)
    historical = ProgrammeRevision(
        programme_id=UUID(first["id"]), version_label="historical-demo", is_synthetic=True
    )
    session.add(historical)
    session.flush()
    active_course = Course(
        programme_revision_id=UUID(first["active_revision_id"]),
        course_name="Synthetic Current Course",
        is_synthetic=True,
    )
    session.add_all(
        [
            active_course,
            Course(
                programme_revision_id=historical.id,
                course_name="Synthetic Historical Course",
                is_synthetic=True,
            ),
            Course(
                programme_revision_id=UUID(second["active_revision_id"]),
                course_name="Synthetic Other Programme Course",
                is_synthetic=True,
            ),
        ]
    )
    session.commit()
    response = client.get(f"/api/v1/programmes/{first['id']}/courses")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert {item["id"] for item in response.json()["items"]} == {str(active_course.id)}


def test_programme_accepts_incomplete_optional_metadata(client: TestClient) -> None:
    institution = client.post(
        "/api/v1/institutions", json={"name": "Synthetic Minimal University", "is_synthetic": True}
    ).json()
    response = client.post(
        "/api/v1/programmes",
        json={
            "institution_id": institution["id"],
            "name": "Synthetic Minimal Programme",
            "is_synthetic": True,
        },
    )
    assert response.status_code == 201
    programme = response.json()
    assert programme["programme_code"] is None
    assert programme["academic_year"] is None
    assert programme["active_revision"]["effective_date"] is None
    assert programme["active_revision"]["version_label"] == "initial"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/programmes/{id}",
        "/api/v1/programmes/{id}/courses",
    ],
)
def test_missing_programmes_are_not_found(client: TestClient, path: str) -> None:
    response = client.get(path.format(id=uuid4()))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert isinstance(response.json()["error"]["details"], list)


def test_programme_cannot_reference_missing_institution(client: TestClient) -> None:
    response = client.post(
        "/api/v1/programmes",
        json={"institution_id": str(uuid4()), "name": "Synthetic Programme"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert client.get("/api/v1/programmes").json()["total"] == 0


def test_programme_rejects_metadata_longer_than_database_limit(client: TestClient) -> None:
    institution = client.post(
        "/api/v1/institutions", json={"name": "Synthetic Length Test", "is_synthetic": True}
    ).json()
    response = client.post(
        "/api/v1/programmes",
        json={
            "institution_id": institution["id"],
            "name": "Synthetic Programme",
            "academic_year": "X" * 51,
            "is_synthetic": True,
        },
    )
    assert response.status_code == 422
    assert client.get("/api/v1/programmes").json()["total"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": "   "},
        {"name": "Synthetic University", "country": "US"},
        {"name": "Synthetic University", "budget": 5000},
        {"name": "Synthetic University", "competency_percentages": {"Python": 80}},
    ],
)
def test_onboarding_rejects_invalid_and_out_of_scope_inputs(
    client: TestClient, payload: dict
) -> None:
    response = client.post("/api/v1/institutions", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["error"]["details"], list)
    assert client.get("/api/v1/institutions").json()["total"] == 0


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=abc"])
def test_pagination_rejects_invalid_values(client: TestClient, query: str) -> None:
    programme = create_programme(client)
    for path in (
        "/api/v1/institutions",
        "/api/v1/programmes",
        f"/api/v1/programmes/{programme['id']}/courses",
    ):
        response = client.get(f"{path}?{query}")
        assert response.status_code == 422
        assert isinstance(response.json()["error"]["details"], list)


def test_validation_errors_do_not_echo_supplied_input(client: TestClient) -> None:
    secret = "private-input-that-must-not-be-echoed"
    response = client.post(
        "/api/v1/programmes", json={"institution_id": secret, "name": "Synthetic"}
    )
    assert response.status_code == 422
    assert secret not in response.text
    assert "input" not in response.json()["error"]["details"][0]
    malformed = client.get("/api/v1/programmes/not-a-uuid")
    assert malformed.status_code == 422
    assert isinstance(malformed.json()["error"]["details"], list)
