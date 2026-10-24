"""Scoped preview capability discovery without named identity or network calls."""

import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from test_security_access import TOKENS, auth, policy, seed_owner

from shiftos.api.routers.analysis import FindingRead
from shiftos.core.config import Settings
from shiftos.main import create_app


@pytest.fixture
def context(session, database, tmp_path):
    own, other = seed_owner(session, "capability-A"), seed_owner(session, "capability-B")
    path = tmp_path / "private-test-access-policy.json"
    grants = policy(path, own.institution.id, other.institution.id)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        api_access_mode="scoped",
        api_access_policy_path=path,
        analysis_model_provider="replit_claude",
        claude_enabled=True,
        analysis_external_processing_allowed=False,
        research_enabled=False,
        replit_anthropic_api_key="PRIVATE-PROVIDER-SENTINEL",
        replit_anthropic_base_url="https://private-provider.invalid/anthropic",
    )
    with TestClient(create_app(settings=settings, database=database)) as client:
        yield SimpleNamespace(
            client=client, own=own, other=other, path=path, policy=grants, settings=settings
        )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong-synthetic-token-value-with-32-characters"},
        {"X-Analysis-Token": TOKENS["reader"]},
    ],
)
def test_access_context_requires_actual_scoped_bearer(context, headers):
    response = context.client.get("/api/v1/access-context", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"


@pytest.mark.parametrize(
    ("key", "permissions", "global_admin"),
    [
        ("reader", ["read"], False),
        ("reviewer", ["read", "review"], False),
        ("admin_read", ["read", "admin"], True),
    ],
)
def test_current_grants_are_exact_and_do_not_imply_write_or_named_identity(
    context, key, permissions, global_admin
):
    response = context.client.get("/api/v1/access-context", headers=auth(key))
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["access_mode"] == "scoped" and value["authenticated"] is True
    assert value["permissions"] == permissions
    assert value["operator_alias"] == key and value["identity_kind"] == "operator_grant"
    assert value["global_admin"] is global_admin
    assert value["institution_ids"] == ([] if global_admin else [str(context.own.institution.id)])
    assert value["execution"] == {
        "external_processing_allowed": False,
        "research_enabled": False,
        "claude_enabled": True,
    }
    assert response.headers["cache-control"] == "no-store"
    for secret in (
        str(context.path),
        "PRIVATE-PROVIDER-SENTINEL",
        "private-provider.invalid",
        *TOKENS.values(),
    ):
        assert secret not in response.text
    for token in TOKENS.values():
        assert hashlib.sha256(token.encode()).hexdigest() not in response.text


def test_write_only_grant_can_explain_capabilities_without_reading_institution_records(context):
    writer = next(row for row in context.policy["principals"] if row["principal_id"] == "writer")
    writer["permissions"] = ["write"]
    context.path.write_text(json.dumps(context.policy), encoding="utf-8")
    response = context.client.get("/api/v1/access-context", headers=auth("writer"))
    assert response.status_code == 200 and response.json()["permissions"] == ["write"]
    assert context.client.get("/api/v1/programmes", headers=auth("writer")).status_code == 403


def test_access_context_reloads_policy_and_fails_closed_on_revocation_or_invalid_policy(context):
    assert context.client.get("/api/v1/access-context", headers=auth("reader")).status_code == 200
    context.policy["principals"] = [
        row for row in context.policy["principals"] if row["principal_id"] != "reader"
    ]
    context.path.write_text(json.dumps(context.policy), encoding="utf-8")
    assert context.client.get("/api/v1/access-context", headers=auth("reader")).status_code == 401
    context.path.write_text('{"PRIVATE-INVALID-POLICY":', encoding="utf-8")
    response = context.client.get("/api/v1/access-context", headers=auth("admin"))
    assert response.status_code == 503
    assert "PRIVATE-INVALID-POLICY" not in response.text and str(context.path) not in response.text


def test_legacy_context_never_fabricates_effective_workspace_permissions(client):
    response = client.get("/api/v1/access-context")
    assert response.status_code == 200
    value = response.json()
    assert value["access_mode"] == "legacy"
    assert value["authenticated"] is value["global_admin"] is False
    assert value["permissions"] == value["institution_ids"] == []
    assert value["operator_alias"] is None
    assert value["identity_kind"] == "unconfigured_legacy"
    assert "configure scoped access" in value["limitations"][0]


def test_access_context_contract_is_typed_and_declares_bearer(context):
    schema = context.client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/access-context"]["get"]
    assert operation["security"] == [{"HTTPBearer": []}]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/AccessContext"
    )


def test_course_finding_schema_exposes_complete_contract_and_preserves_metadata_alternative(
    context,
):
    schema = context.client.get("/openapi.json").json()
    schemas = schema["components"]["schemas"]
    alternatives = schemas["FindingRead"]["properties"]["result_json"]["anyOf"]
    assert {"$ref": "#/components/schemas/CourseFindingResult"} in alternatives
    assert any(item.get("type") == "object" for item in alternatives)
    assert (
        set(
            (
                "foundational_relevance",
                "ai_transformation",
                "workforce_alignment",
                "curriculum_currency",
                "future_resilience",
                "needs_syllabus_confirmation",
            )
        )
        <= schemas["CourseFindingResult"]["properties"].keys()
    )
    adapter = TypeAdapter(FindingRead.model_fields["result_json"].annotation)
    for metadata in ({}, {"source_text_withheld": True, "revalidation_required": True}):
        assert adapter.validate_python(metadata) == metadata
