"""Offline research controls. Mock search replies are synthetic discovery metadata.

The two small CSV golden rows are published CC BY 4.0 OpenDOSM observations:
https://storage.dosm.gov.my/labour/employment_sector.csv (observed 24 October 2026).
No test performs live discovery or claims a live source import.
"""

import json
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from shiftos.core.config import Settings
from shiftos.db.base import utc_now
from shiftos.models.analysis import ResearchCache
from shiftos.models.evidence import DatasetVersion, EvidenceReference
from shiftos.services.analysis.providers import ProviderError
from shiftos.services.analysis.research import ResearchService
from shiftos.services.evidence.pipeline import run_ingestion

ROOT = Path(__file__).resolve().parents[1]
DATASET = "D-EMPLOYMENT-SECTOR"
SOURCE = "https://storage.dosm.gov.my/labour/employment_sector.csv"


@pytest.fixture
def research_setup(tmp_path):
    original = json.loads((ROOT / "data/research_policy.json").read_text())
    original.update(
        registry_path=str(ROOT / "data/dataset_registry.csv"),
        acquisition_policy_path=str(tmp_path / "acquisition.json"),
        allowed_dataset_ids=[DATASET],
        queries_per_gap=1,
        search_result_storage_allowed=False,
    )
    policy = tmp_path / "research.json"
    policy.write_text(json.dumps(original))
    acquisition = {
        DATASET: {
            "adapter": "employment_sector",
            "format": "csv",
            "access_reviewed": True,
            "reuse_reviewed": True,
            "retain_raw": False,
            "instructions": "Offline golden-source fixture.",
        }
    }
    (tmp_path / "acquisition.json").write_text(json.dumps(acquisition))
    permissions = tmp_path / "permissions.json"
    permissions.write_text(
        json.dumps(
            {
                "sources": {
                    DATASET: {
                        "internal_analysis_allowed": True,
                        "external_model_allowed": False,
                        "excerpt_output_allowed": False,
                        "basis": "Source CC BY4.0",
                    }
                }
            }
        )
    )
    fixture = tmp_path / "employment.csv"
    fixture.write_text(
        "date,sector,sex,proportion\n2001-01-01,agriculture,both,15.1\n2002-01-01,agriculture,both,14.9\n"
    )
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        research_enabled=True,
        analysis_research_policy=policy,
        analysis_permissions_path=permissions,
    )
    return settings, fixture, policy, permissions


class Search:
    def __init__(self, pointers=None, error=None):
        self.queries = []
        self.pointers = (
            pointers
            if pointers is not None
            else [{"title": "Synthetic discovery title", "url": SOURCE}]
        )
        self.error = error

    def search(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.pointers


def runner(fixture, seen):
    def import_original(database, **kwargs):
        seen.append(kwargs)
        return run_ingestion(database, **kwargs, local_path=fixture, retrieved_at=utc_now())

    return import_original


def test_real_parser_persistence_and_query_required_before_research_success(
    database, research_setup
):
    settings, fixture, _, _ = research_setup
    search, imports = Search(), []
    service = ResearchService(database, settings, lambda _: search, runner(fixture, imports))
    output = service.run("accounting", ["missing_workforce"])
    assert output["status"] == "VERIFIED_IMPORTS_AVAILABLE", output
    assert len(output["version_ids"]) == 1 and len(imports) == 1
    assert output["outcomes"][0]["facts"] == 2
    assert output["requires_sufficiency_recheck"] is True
    with database.session_factory() as session:
        version = session.scalar(select(DatasetVersion))
        assert str(version.id) == output["version_ids"][0]
        cache = session.scalar(select(ResearchCache))
        encoded = json.dumps(cache.response_json)
        assert "Synthetic discovery title" not in encoded and SOURCE not in encoded


def test_cached_own_ingestion_lineage_avoids_search_and_rechecks_review_state(
    database, research_setup
):
    settings, fixture, _, _ = research_setup
    search, imports = Search(), []
    service = ResearchService(database, settings, lambda _: search, runner(fixture, imports))
    first = service.run("accounting", ["missing_workforce"])
    second = service.run("accounting", ["missing_workforce"])
    assert (
        first["version_ids"] == second["version_ids"]
        and len(search.queries) == 1
        and len(imports) == 1
    )
    with database.session_factory() as session:
        for reference in session.scalars(select(EvidenceReference)):
            reference.review_status = "rejected"
        session.commit()
    third = service.run("accounting", ["missing_workforce"])
    assert third["version_ids"] == []


def test_source_success_report_without_persisted_records_is_rejected(database, research_setup):
    settings, _, _, _ = research_setup
    search = Search()
    service = ResearchService(
        database,
        settings,
        lambda _: search,
        lambda *a, **k: [
            {"status": "SUCCEEDED", "version_id": "00000000-0000-0000-0000-000000000000"}
        ],
    )
    output = service.run("accounting", ["workforce"])
    assert not output["version_ids"]
    assert output["outcomes"][0]["code"] == "source_import_not_verified"


def test_policy_withdrawal_invalidates_cache_and_denies_import(database, research_setup):
    settings, fixture, _, permissions = research_setup
    search, imports = Search(), []
    service = ResearchService(database, settings, lambda _: search, runner(fixture, imports))
    service.run("accounting", ["workforce"])
    permissions.write_text(
        json.dumps(
            {"sources": {DATASET: {"internal_analysis_allowed": False, "basis": "Withdrawn"}}}
        )
    )
    output = service.run("accounting", ["workforce"])
    assert not output["version_ids"] and len(imports) == 1
    assert output["outcomes"][0]["status"] == "MANUAL_REQUIRED"
    assert len(search.queries) == 2


def test_expired_cache_requires_new_search_but_idempotent_import(database, research_setup):
    settings, fixture, _, _ = research_setup
    search, imports = Search(), []
    service = ResearchService(database, settings, lambda _: search, runner(fixture, imports))
    first = service.run("accounting", ["workforce"])
    with database.session_factory() as session:
        session.scalar(select(ResearchCache)).expires_at = utc_now() - timedelta(seconds=1)
        session.commit()
    second = service.run("accounting", ["workforce"])
    assert first["version_ids"] == second["version_ids"] and len(search.queries) == 2
    with database.session_factory() as session:
        assert len(list(session.scalars(select(DatasetVersion)))) == 1


def test_unknown_source_never_fetches_or_caches_restricted_search_text(database, research_setup):
    settings, _, _, _ = research_setup
    search = Search(
        [
            {
                "title": "DO NOT RETAIN",
                "url": "https://unregistered.invalid/report",
                "description": "RESTRICTED SNIPPET",
            }
        ]
    )
    output = ResearchService(
        database,
        settings,
        lambda _: search,
        lambda *a, **k: pytest.fail("Unknown original must not be fetched"),
    ).run("engineering", ["missing_ai"])
    assert output["outcomes"][0]["code"] == "unregistered_sources_require_operator_policy"
    with database.session_factory() as session:
        cached = json.dumps(session.scalar(select(ResearchCache)).response_json)
    assert (
        "DO NOT RETAIN" not in cached
        and "unregistered.invalid" not in cached
        and "SNIPPET" not in cached
    )


def test_partial_url_or_domain_match_cannot_enable_original_fetch(database, research_setup):
    settings, _, _, _ = research_setup
    search = Search([{"title": "Synthetic", "url": SOURCE + "?unapproved=true"}])
    output = ResearchService(
        database,
        settings,
        lambda _: search,
        lambda *a, **k: pytest.fail("Exact registry URL match required"),
    ).run("accounting", ["workforce"])
    assert output["documents_attempted"] == 0


@pytest.mark.parametrize(
    "discipline", ["private course text secret@university.test", "unknown", "/private/path.pdf"]
)
def test_private_or_unknown_discipline_never_leaves_service(database, research_setup, discipline):
    settings, _, _, _ = research_setup
    output = ResearchService(
        database, settings, lambda _: pytest.fail("No search construction")
    ).run(discipline, ["missing_ai"])
    assert not output["attempts"]


def test_private_gap_text_is_not_used_in_queries(database, research_setup):
    settings, _, _, _ = research_setup
    output = ResearchService(database, settings, lambda _: pytest.fail("No private query")).run(
        "accounting", ["private uploaded text: ABC123"]
    )
    assert output["status"] == "MANUAL_REQUIRED" and output["attempts"] == []


def test_disabled_synthetic_and_no_gap_paths_make_no_external_request(database, research_setup):
    settings, _, _, _ = research_setup
    service = ResearchService(database, settings, lambda _: pytest.fail("No external request"))
    assert service.run("accounting", [])["status"] == "NOT_REQUIRED"
    assert service.run("accounting", ["missing_ai"], True)["status"] == "OFFLINE_SYNTHETIC"
    settings.research_enabled = False
    assert service.run("accounting", ["missing_ai"])["status"] == "DISABLED"


def test_provider_failure_is_sanitized_and_negatively_cached(database, research_setup):
    settings, _, _, _ = research_setup
    search = Search(error=ProviderError("search_not_configured"))
    service = ResearchService(database, settings, lambda _: search)
    first = service.run("accounting", ["missing_ai"])
    service.run("accounting", ["missing_ai"])
    assert first["status"] == "PROVIDER_UNAVAILABLE" and len(search.queries) == 1


def test_approved_result_storage_caches_only_titles_and_urls(database, research_setup):
    settings, _, policy_path, _ = research_setup
    policy = json.loads(policy_path.read_text())
    policy["search_result_storage_allowed"] = True
    policy_path.write_text(json.dumps(policy))
    search = Search(
        [
            {
                "title": "Synthetic pointer",
                "url": "https://unregistered.invalid/doc",
                "description": "NEVER STORE",
            }
        ]
    )
    ResearchService(database, settings, lambda _: search).run("accounting", ["missing_ai"])
    with database.session_factory() as session:
        cached = session.scalar(select(ResearchCache)).response_json
    assert cached["pointers"] == [
        {"title": "Synthetic pointer", "url": "https://unregistered.invalid/doc"}
    ]
    assert "NEVER STORE" not in json.dumps(cached)


def test_query_ceiling_is_enforced(database, research_setup):
    settings, _, _, _ = research_setup
    settings.research_max_queries = 2
    search = Search([])
    output = ResearchService(database, settings, lambda _: search).run(
        "engineering", ["missing_ai", "missing_standards", "missing_workforce"]
    )
    assert len(search.queries) == 2 and output["query_count"] == 2


def test_total_research_deadline_prevents_original_acquisition(database, research_setup):
    settings, _, _, _ = research_setup
    clock = [0]
    search = Search()
    original = search.search

    def slow_search(query):
        clock[0] = 181
        return original(query)

    search.search = slow_search
    output = ResearchService(
        database,
        settings,
        lambda _: search,
        lambda *a, **k: pytest.fail("No source acquisition after deadline"),
        monotonic=lambda: clock[0],
    ).run("accounting", ["workforce"])
    assert not output["version_ids"] and output["documents_attempted"] == 0
    assert any(x.get("code") == "research_budget_exhausted" for x in output["outcomes"])


def test_search_calls_respect_one_second_minimum_interval(database, research_setup):
    settings, _, policy_path, _ = research_setup
    policy = json.loads(policy_path.read_text())
    policy["queries_per_gap"] = 2
    policy_path.write_text(json.dumps(policy))
    clock = [0]
    seen = []

    class TimedSearch:
        def search(self, query):
            seen.append(clock[0])
            return []

    def sleep(seconds):
        clock[0] += seconds

    ResearchService(
        database, settings, lambda _: TimedSearch(), monotonic=lambda: clock[0], sleep=sleep
    ).run("accounting", ["missing_ai"])
    assert seen == [0, 1]


def test_permission_strings_are_not_truthy_approvals(database, research_setup):
    settings, _, _, permissions = research_setup
    permissions.write_text(
        json.dumps(
            {"sources": {DATASET: {"internal_analysis_allowed": "false", "basis": "Invalid type"}}}
        )
    )
    output = ResearchService(database, settings, lambda _: pytest.fail("No approved policy")).run(
        "accounting", ["workforce"]
    )
    assert output["status"] == "POLICY_UNAVAILABLE"


def test_ingestion_exception_is_sanitized(database, research_setup):
    settings, _, _, _ = research_setup

    def failing_runner(*args, **kwargs):
        raise ValueError("SYNTHETIC_SENSITIVE_ERROR_DATA")

    output = ResearchService(database, settings, lambda _: Search(), failing_runner).run(
        "accounting", ["workforce"]
    )
    assert output["outcomes"][0]["code"] == "source_ingestion_unavailable"
    assert "SYNTHETIC_SENSITIVE" not in json.dumps(output)
