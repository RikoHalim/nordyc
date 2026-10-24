"""Bounded discovery of registered originals; search text is never admitted evidence."""

import hashlib
import json
import re
import time
from collections import Counter
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shiftos.db.base import utc_now
from shiftos.models.analysis import ResearchCache
from shiftos.models.evidence import Dataset, DatasetVersion, EvidenceReference
from shiftos.repositories.evidence import MODELS
from shiftos.services.analysis.providers import BraveSearch, ProviderError
from shiftos.services.evidence.acquisition import DatasetFetcher
from shiftos.services.evidence.pipeline import AcquisitionRule, run_ingestion
from shiftos.services.evidence.registry import read_registry
from shiftos.services.ingestion.fetcher import FetchError

GAP_FAMILIES = {
    "missing_occupations": "occupations",
    "missing_skills": "occupations",
    "missing_standards": "standards",
    "missing_workforce": "workforce",
    "missing_ai": "ai",
    "currentness_review_required": "currentness",
    "classification_bridge_unreviewed": "classification",
    "occupations": "occupations",
    "skills": "occupations",
    "standards": "standards",
    "workforce": "workforce",
    "ai": "ai",
    "currentness": "currentness",
    "classification": "classification",
}
CATEGORIES = {
    "occupations": {"C"},
    "standards": {"B"},
    "workforce": {"D"},
    "ai": {"E"},
    "classification": {"C"},
    "currentness": {"B", "C", "D", "E"},
}


class ResearchPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=100)
    registry_path: Path = Path("data/dataset_registry.csv")
    acquisition_policy_path: Path = Path("data/evidence_acquisition.json")
    allowed_dataset_ids: list[str] = Field(max_length=100)
    disciplines: dict[str, str]
    aliases: dict[str, str] = Field(default_factory=dict)
    queries: dict[str, list[str]]
    queries_per_gap: int = Field(default=2, ge=1, le=2)
    max_documents: int = Field(default=10, ge=1, le=10)
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    negative_cache_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    search_result_storage_allowed: bool = False


def _canonical_url(value: str) -> str | None:
    try:
        url = urlsplit(value)
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            return None
        # Full origin/path/query match; a matching hostname alone is not approval.
        return urlunsplit(
            (
                "https",
                url.netloc.lower(),
                url.path.rstrip("/") or "/",
                urlencode(sorted(parse_qsl(url.query, keep_blank_values=True))),
                "",
            )
        )
    except (TypeError, ValueError):
        return None


class _DeadlineClient:
    """Keep the existing pinned/robots-aware transport, bounding each stream and wait."""

    def __init__(self, client, check):
        self.client, self.check = client, check

    @contextmanager
    def stream(self, *args, **kwargs):
        kwargs["timeout"] = min(20, self.check())
        with self.client.stream(*args, **kwargs) as response:
            original = response.iter_bytes

            def bounded_bytes(*args, **kwargs):
                for chunk in original(*args, **kwargs):
                    self.check()
                    yield chunk

            response.iter_bytes = bounded_bytes
            yield response

    def close(self):
        self.client.close()


class ResearchService:
    def __init__(
        self,
        database,
        settings,
        search_factory=BraveSearch,
        ingestion_runner=run_ingestion,
        *,
        monotonic=time.monotonic,
        sleep=time.sleep,
    ):
        self.database, self.settings = database, settings
        self.search_factory, self.ingestion_runner = search_factory, ingestion_runner
        self.monotonic, self.sleep = monotonic, sleep
        self._source_last_request = {}
        self._last_search_at = None

    def _configuration(self):
        raw = self.settings.analysis_research_policy.read_bytes()
        policy = ResearchPolicy.model_validate_json(raw)
        registry_bytes = policy.registry_path.read_bytes()
        acquisition_bytes = policy.acquisition_policy_path.read_bytes()
        permission_bytes = self.settings.analysis_permissions_path.read_bytes()
        entries = read_registry(policy.registry_path)
        rules = {
            key: AcquisitionRule.model_validate(value)
            for key, value in json.loads(acquisition_bytes).items()
        }
        permissions = json.loads(permission_bytes).get("sources", {})
        policy_hash = hashlib.sha256(
            b"\0".join([raw, registry_bytes, acquisition_bytes, permission_bytes])
        ).hexdigest()
        if not isinstance(permissions, dict):
            raise ValueError("Invalid source permissions")
        if any(
            not isinstance(value, dict)
            or not isinstance(value.get("internal_analysis_allowed"), bool)
            or not isinstance(value.get("basis"), str)
            for value in permissions.values()
        ):
            raise ValueError("Source permissions require explicit boolean decisions and basis")
        return policy, entries, rules, permissions, policy_hash

    def _read_cache(self, key, policy_hash):
        with self.database.session_factory() as session:
            row = session.scalar(
                select(ResearchCache).where(
                    ResearchCache.cache_key == key,
                    ResearchCache.policy_sha256 == policy_hash,
                    ResearchCache.expires_at > utc_now(),
                    ResearchCache.is_synthetic.is_(False),
                )
            )
            return dict(row.response_json) if row else None

    def _write_cache(self, key, policy_hash, value, seconds):
        with self.database.session_factory() as session:
            row = session.scalar(select(ResearchCache).where(ResearchCache.cache_key == key))
            if row is None:
                row = ResearchCache(
                    cache_key=key,
                    policy_sha256=policy_hash,
                    response_json=value,
                    expires_at=utc_now() + timedelta(seconds=seconds),
                    is_synthetic=False,
                )
                session.add(row)
            else:
                row.policy_sha256, row.response_json = policy_hash, value
                row.expires_at = utc_now() + timedelta(seconds=seconds)
            try:
                session.commit()
            except IntegrityError:
                # A concurrent identical research job may already have stored the metadata.
                session.rollback()

    def _verified_version(self, version_id, dataset_key):
        try:
            version_id = UUID(str(version_id))
        except (TypeError, ValueError):
            return None
        with self.database.session_factory() as session:
            row = session.scalar(
                select(DatasetVersion)
                .join(Dataset)
                .where(
                    DatasetVersion.id == version_id,
                    Dataset.registry_key == dataset_key,
                    DatasetVersion.is_synthetic.is_(False),
                    DatasetVersion.retrieved_at <= utc_now(),
                )
            )
            if row is None:
                return None
            facts = sum(
                session.scalar(
                    select(func.count())
                    .select_from(model)
                    .join(EvidenceReference, model.evidence_id == EvidenceReference.id)
                    .where(
                        model.version_id == row.id,
                        model.is_synthetic.is_(False),
                        EvidenceReference.review_status != "rejected",
                    )
                )
                or 0
                for model in MODELS.values()
            )
            return {
                "version_id": str(row.id),
                "facts": facts,
                "retrieved_at": row.retrieved_at.isoformat(),
                "publication_date": row.publication_date,
            }

    def _fetcher(self, deadline):
        def check():
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                raise FetchError(
                    "research_deadline", "The bounded research deadline was exhausted."
                )
            return remaining

        def bounded_sleep(delay):
            if delay >= check():
                raise FetchError(
                    "research_deadline", "The bounded research deadline was exhausted."
                )
            self.sleep(delay)

        def factory(*args, **kwargs):
            kwargs.update(sleep=bounded_sleep, timeout=min(20, check()), monotonic=self.monotonic)
            fetcher = DatasetFetcher(*args, **kwargs)
            # Separate dataset imports still share the same publisher rate-limit history.
            fetcher._last_request = self._source_last_request
            fetcher._client = _DeadlineClient(fetcher._client, check)
            return fetcher

        return factory

    def run(self, discipline: str, gaps: list[str], is_synthetic: bool = False) -> dict:
        result = {
            "attempts": [],
            "version_ids": [],
            "outcomes": [],
            "status": "INSUFFICIENT_EVIDENCE",
            "requires_sufficiency_recheck": True,
        }
        if is_synthetic:
            return {
                **result,
                "status": "OFFLINE_SYNTHETIC",
                "outcomes": [{"code": "synthetic_external_research_disabled"}],
            }
        if not gaps:
            return {**result, "status": "NOT_REQUIRED"}
        if not self.settings.research_enabled:
            return {**result, "status": "DISABLED", "outcomes": [{"code": "research_disabled"}]}
        try:
            policy, entries, rules, permissions, policy_hash = self._configuration()
        except (OSError, ValueError, TypeError):
            return {
                **result,
                "status": "POLICY_UNAVAILABLE",
                "outcomes": [{"code": "research_policy_invalid"}],
            }
        normalized = (
            re.sub(r"[\s-]+", "_", discipline.strip().casefold())
            if isinstance(discipline, str)
            else ""
        )
        canonical = policy.aliases.get(normalized, normalized)
        terms = policy.disciplines.get(canonical)
        if not terms or not re.fullmatch(r"[A-Za-z0-9 ,&()\-]{1,120}", terms):
            return {**result, "outcomes": [{"code": "unsupported_or_private_discipline"}]}
        families = list(
            dict.fromkeys(GAP_FAMILIES[gap] for gap in gaps[:30] if gap in GAP_FAMILIES)
        )
        if not families:
            return {
                **result,
                "status": "MANUAL_REQUIRED",
                "outcomes": [{"code": "gap_requires_source_or_academic_review"}],
            }
        deadline = self.monotonic() + self.settings.research_timeout_seconds
        search = self.search_factory(self.settings)
        if isinstance(search, BraveSearch):
            search.deadline = deadline
        attempted_datasets, documents, query_count = set(), 0, 0
        result["policy_sha256"] = policy_hash
        entries_by_id = {entry.id: entry for entry in entries}
        matched_urls = {}
        for entry in entries:
            if entry.id not in policy.allowed_dataset_ids:
                continue
            for value in [entry.source_url, entry.download_api_url]:
                if value and (url := _canonical_url(value)):
                    matched_urls.setdefault(url, []).append(entry.id)
        for family in families:
            for template in policy.queries.get(family, [])[: policy.queries_per_gap]:
                if (
                    query_count >= self.settings.research_max_queries
                    or self.monotonic() >= deadline
                ):
                    result["outcomes"].append({"code": "research_budget_exhausted"})
                    break
                try:
                    query = template.format(discipline=terms)
                except (KeyError, ValueError, IndexError):
                    result["outcomes"].append({"code": "invalid_query_template"})
                    continue
                query_count += 1
                key = hashlib.sha256(
                    json.dumps(
                        ["brave", canonical, family, query, "MY", "en", policy_hash]
                    ).encode()
                ).hexdigest()
                cached = self._read_cache(key, policy_hash)
                attempt = {
                    "query": query,
                    "family": family,
                    "provider": "brave",
                    "cached": cached is not None,
                }
                result["attempts"].append(attempt)
                candidates = []
                if cached is not None:
                    if cached.get("status") == "provider_unavailable":
                        attempt["status"], attempt["code"] = "UNAVAILABLE", cached.get("code")
                        continue
                    # Reuse own original-source ingestion outcomes, not unlicensed search text.
                    for previous in cached.get("verified_imports", []):
                        dataset_key = previous.get("dataset")
                        permission = permissions.get(dataset_key, {})
                        rule = rules.get(dataset_key)
                        if (
                            not permission.get("internal_analysis_allowed")
                            or not rule
                            or not rule.reuse_reviewed
                        ):
                            continue
                        verified = self._verified_version(previous.get("version_id"), dataset_key)
                        if verified and verified["facts"] > 0:
                            result["version_ids"].append(verified["version_id"])
                            result["outcomes"].append(
                                {
                                    "dataset": dataset_key,
                                    "status": "CACHED_VERIFIED_VERSION",
                                    **verified,
                                }
                            )
                        else:
                            result["outcomes"].append(
                                {
                                    "dataset": dataset_key,
                                    "status": "CACHED_VERSION_INADMISSIBLE",
                                    "code": "cached_source_rejected_or_missing",
                                }
                            )
                    if policy.search_result_storage_allowed:
                        candidates = cached.get("pointers", [])[:10]
                    else:
                        attempt["status"] = "CACHED_OPERATIONAL_METADATA"
                        continue
                else:
                    try:
                        if self._last_search_at is not None:
                            delay = max(0.0, 1.0 - (self.monotonic() - self._last_search_at))
                            if self.monotonic() + delay >= deadline:
                                result["outcomes"].append({"code": "research_budget_exhausted"})
                                break
                            self.sleep(delay)
                        candidates = search.search(query)
                        if not isinstance(candidates, list):
                            raise ProviderError("provider_response_invalid")
                        attempt["status"] = "SEARCHED"
                    except ProviderError as exc:
                        attempt["status"], attempt["code"] = "UNAVAILABLE", exc.code
                        self._write_cache(
                            key,
                            policy_hash,
                            {"status": "provider_unavailable", "code": exc.code},
                            policy.negative_cache_ttl_seconds,
                        )
                        continue
                    finally:
                        self._last_search_at = self.monotonic()
                # Persist only minimal pointers when the plan explicitly permits result storage.
                cache = {"status": "discovered", "verified_imports": []}
                if policy.search_result_storage_allowed:
                    cache["pointers"] = [
                        {"title": str(row.get("title", ""))[:300], "url": row.get("url", "")}
                        for row in candidates[:10]
                        if isinstance(row, dict)
                    ]
                matches = []
                unknown_count = 0
                for pointer in candidates[:10]:
                    if not isinstance(pointer, dict):
                        continue
                    ids = matched_urls.get(_canonical_url(pointer.get("url", "")), [])
                    if not ids:
                        unknown_count += 1
                    for dataset_key in ids:
                        entry = entries_by_id[dataset_key]
                        if entry.category in CATEGORIES[family] and dataset_key not in matches:
                            matches.append(dataset_key)
                if unknown_count:
                    result["outcomes"].append(
                        {
                            "code": "unregistered_sources_require_operator_policy",
                            "candidate_count": unknown_count,
                        }
                    )
                for dataset_key in matches:
                    if dataset_key in attempted_datasets:
                        continue
                    if documents >= policy.max_documents or self.monotonic() >= deadline:
                        result["outcomes"].append({"code": "research_budget_exhausted"})
                        break
                    attempted_datasets.add(dataset_key)
                    rule, entry = rules.get(dataset_key), entries_by_id[dataset_key]
                    permission = permissions.get(dataset_key, {})
                    if (
                        not rule
                        or not rule.access_reviewed
                        or not rule.reuse_reviewed
                        or not permission.get("internal_analysis_allowed")
                        or not permission.get("basis")
                        or entry.verification_status == "Unverified"
                    ):
                        result["outcomes"].append(
                            {
                                "dataset": dataset_key,
                                "status": "MANUAL_REQUIRED",
                                "code": "source_access_or_use_not_approved",
                            }
                        )
                        continue
                    documents += 1
                    try:
                        reports = self.ingestion_runner(
                            self.database,
                            registry_path=policy.registry_path,
                            policy_path=policy.acquisition_policy_path,
                            dataset_ids=[dataset_key],
                            enabled=True,
                            is_synthetic=False,
                            fetcher_factory=self._fetcher(deadline),
                        )
                    except Exception:
                        result["outcomes"].append(
                            {
                                "dataset": dataset_key,
                                "status": "FAILED",
                                "code": "source_ingestion_unavailable",
                            }
                        )
                        continue
                    report = reports[0] if reports else {}
                    verified = self._verified_version(report.get("version_id"), dataset_key)
                    if report.get("status") in {"SUCCEEDED", "UNCHANGED"} and verified:
                        if verified["facts"] > 0:
                            result["version_ids"].append(verified["version_id"])
                            cache["verified_imports"].append(
                                {"dataset": dataset_key, "version_id": verified["version_id"]}
                            )
                        result["outcomes"].append(
                            {
                                "dataset": dataset_key,
                                "status": "IMPORTED_AND_QUERIED"
                                if verified["facts"]
                                else "CANDIDATES_ONLY",
                                **verified,
                            }
                        )
                    else:
                        result["outcomes"].append(
                            {
                                "dataset": dataset_key,
                                "status": "FAILED",
                                "code": "source_import_not_verified",
                            }
                        )
                seconds = (
                    policy.cache_ttl_seconds
                    if cache["verified_imports"]
                    else policy.negative_cache_ttl_seconds
                )
                self._write_cache(key, policy_hash, cache, seconds)
        result["version_ids"] = sorted(set(result["version_ids"]))
        result["query_count"], result["documents_attempted"] = query_count, documents
        if result["version_ids"]:
            result["status"] = "VERIFIED_IMPORTS_AVAILABLE"
        elif any(row.get("status") == "UNAVAILABLE" for row in result["attempts"]):
            result["status"] = "PROVIDER_UNAVAILABLE"
        result["outcome_counts"] = dict(
            Counter(row.get("status", row.get("code")) for row in result["outcomes"])
        )
        return result
