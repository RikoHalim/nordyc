"""Bounded synthetic administrative acceptance through existing APIs and workers.

This is an explicit test/development workflow, never an application startup hook.
It writes only labelled source inputs directly; every derived analysis, finding,
recommendation, pathway and review uses the established services and jobs. No
provider mocks, network enabling or persistent settings mutations live here.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from shiftos.core.enums import DocumentFormat, DocumentKind
from shiftos.models import (
    ActionPlanRun,
    AnalysisRun,
    CareerRun,
    Course,
    Dataset,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Occupation,
    SDGReference,
    Skill,
    Source,
)
from shiftos.services.evidence.pipeline import run_ingestion
from shiftos.services.evidence.registry import REGISTRY_COLUMNS
from shiftos.services.ingestion.worker import run_once

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "examples/system_integration.synthetic.json"
RIGHTS = {
    "internal_analysis_allowed": True,
    "external_model_allowed": True,
    "excerpt_output_allowed": True,
    "basis": "Explicit fictional source-input fixture permission; no real academic data.",
}


class IntegrationFailure(RuntimeError):
    """Safe stage-specific failure without raw provider bodies or secrets."""


class _Metrics:
    def __init__(self, engine):
        self.engine, self.stage = engine, "setup"
        self.counts, self.stages = Counter(), {}

    def query(self, *args):
        self.counts[self.stage] += 1

    @contextmanager
    def measure(self, stage):
        previous, self.stage = self.stage, stage
        started = time.perf_counter()
        try:
            yield
        finally:
            self.stages[stage] = {
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "sql_statements": self.counts[stage],
            }
            self.stage = previous


def fixture_for(discipline="computing", fixture=None):
    if fixture is not None:
        result = json.loads(json.dumps(fixture))
    else:
        collection = ROOT / "examples/evaluation/collection.v1.json"
        if collection.exists():
            payload = json.loads(collection.read_text(encoding="utf-8"))
            cases = payload.get("disciplines", {})
            result = cases.get(discipline)
        else:
            result = None
        if result is None and discipline == "computing":
            result = json.loads((ROOT / "examples/career_alignment.synthetic.json").read_text())
        if result is None:
            raise ValueError("Provide an explicitly synthetic fixture for this discipline")
    if result.get("is_synthetic") is not True or result.get("discipline") != discipline:
        raise ValueError("Integration fixture must label its exact synthetic discipline")
    return result


def _response(response, expected, stage):
    if response.status_code != expected:
        raise IntegrationFailure(f"{stage}: unexpected HTTP status {response.status_code}")
    return response.json()


def _worker(client, database, settings, queued, path, stage, worker):
    if worker(database, settings) != UUID(queued["job_id"] if "job_id" in queued else queued["id"]):
        raise IntegrationFailure(f"{stage}: worker did not claim the submitted job")
    result = _response(client.get(path), 200, stage)
    if result["status"] not in {"SUCCEEDED", "PARTIAL"}:
        raise IntegrationFailure(f"{stage}: job ended in {result['status']}")
    return result


def _curriculum(client, database, settings, spec, count, worker):
    institution = _response(
        client.post(
            "/api/v1/institutions",
            json={
                "name": spec["institution"],
                "website_url": "https://curriculum.example.invalid",
                "is_synthetic": True,
            },
        ),
        201,
        "institution",
    )
    inputs = [*spec["courses"]]
    while len(inputs) < count:
        number = len(inputs) + 1
        inputs.append(
            {
                "key": f"inventory-{number}",
                "title": f"Synthetic {spec['discipline']} Inventory Topic {number}",
                "quote": None,
            }
        )
    if len(inputs) > count:
        raise ValueError("Requested workload cannot omit existing fixture courses")
    manifest = {
        "name": spec["programme"],
        "canonical_url": "https://curriculum.example.invalid/programme",
        "source_url": "https://curriculum.example.invalid/programme",
        "source_locator": "synthetic:complete-inventory",
        "retrieved_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "reviewed": True,
        "license_status": "synthetic_fixture",
        "notes": ["Complete labelled synthetic inventory; no real university claim."],
        "courses": [
            {
                "course_name": row["title"],
                "course_code": f"SYN{index:03}",
                "course_type": "COMPULSORY",
                "year": 1 + index // 40,
                "source_locator": f"synthetic:inventory:{row['key']}",
                "source_excerpt": row["title"],
            }
            for index, row in enumerate(inputs, 1)
        ],
    }
    path = f"/api/v1/institutions/{institution['id']}/imports"
    request = {
        "is_synthetic": True,
        "idempotency_key": "synthetic-system-curriculum-1",
        "programmes": [manifest],
    }
    queued = _response(client.post(path, json=request), 202, "curriculum_import")
    completed = _worker(
        client,
        database,
        settings,
        queued,
        f"/api/v1/catalogue/jobs/{queued['id']}",
        "curriculum_import",
        worker,
    )
    outcome = completed["result"]["entries"][0]
    programme_id, revision_id = outcome["programme_id"], outcome["revision_id"]
    courses = []
    for offset in range(0, count, 100):
        courses.extend(
            _response(
                client.get(
                    f"/api/v1/programmes/{programme_id}/courses",
                    params={"limit": 100, "offset": offset},
                ),
                200,
                "course_retrieval",
            )["items"]
        )
    by_title = {row["course_name"]: row for row in courses}
    mapped = {row["key"]: by_title[row["title"]] for row in inputs}
    if len(courses) != count:
        raise IntegrationFailure(
            "curriculum_import: course coverage differs from submitted inventory"
        )
    return institution, programme_id, revision_id, mapped, inputs, request, completed


def _taxonomy(database, workdir, spec):
    """Use the existing reviewed source importer, with explicit synthetic facts."""
    records = []

    def add(kind, key, data, quote):
        records.append(
            {
                "kind": kind,
                "key": key,
                "data": data,
                "locator": f"synthetic:{key}",
                "excerpt": quote,
                "review_status": "reviewed",
            }
        )

    for skill in spec["skills"]:
        add(
            "skill",
            f"skill:{skill['key']}",
            {"taxonomy": spec["taxonomy"], "label": skill["label"]},
            f"Fictional competency requirement: {skill['label']}.",
        )
    skills = {row["key"]: row["label"] for row in spec["skills"]}
    for occupation in spec["occupations"]:
        key = occupation["key"]
        add(
            "occupation",
            f"occupation:{key}",
            {
                "taxonomy": spec["taxonomy"],
                "label": occupation["label"],
                "description": f"Explicitly fictional {spec['discipline']} occupation benchmark.",
                "metadata_json": {"related_disciplines": [spec["discipline"]]},
            },
            f"Fictional {spec['discipline']} occupation: {occupation['label']}.",
        )
        for skill, relation in occupation["requirements"].items():
            add(
                "occupation_skill",
                f"relation:{key}:{skill}",
                {
                    "occupation_external_id": f"occupation:{key}",
                    "skill_external_id": f"skill:{skill}",
                    "relationship": relation,
                },
                f"{occupation['label']} has the fictional {relation} requirement {skills[skill]}.",
            )
    add(
        "academic_standard",
        "programme-benchmark",
        {
            "discipline": spec["discipline"],
            "title": "Fictional reviewed bachelor benchmark",
            "statement": (
                f"Synthetic {spec['discipline']} benchmark for source-aware academic review."
            ),
            "metadata_json": {"mqf_level": 6, "related_disciplines": [spec["discipline"]]},
        },
        f"Fictional benchmark: review {spec['discipline']} disciplinary foundations "
        "against the admitted requirements. This is not university teaching evidence.",
    )
    years = spec.get("workforce_years", [2024, 2025])
    if len(years) != 2 or any(type(year) is not int for year in years):
        raise ValueError("Synthetic workforce comparison requires two labelled years")
    for year, value in zip(years, ("100", "110"), strict=True):
        add(
            "workforce",
            f"workforce:{year}",
            {
                "occupation_external_id": "occupation:analyst",
                "occupation_label": spec["occupations"][0]["label"],
                "geography": "MY",
                "period_start": f"{year}-01-01",
                "period_end": f"{year}-12-31",
                "indicator": "employment_count",
                "value": value,
                "unit": "persons",
                "limitations": (
                    "Invented controlled fixture values only; occupation counts "
                    "do not measure skill demand."
                ),
                "metadata_json": {
                    "population_level": "occupation",
                    "series_id": "synthetic-system-series",
                },
            },
            f"Fictional {year} occupation-level observation is {value} persons; "
            "not real Malaysian statistics.",
        )
    path = workdir / "source-inputs.synthetic.json"
    path.write_text(json.dumps({"reviewed": True, "records": records}), encoding="utf-8")
    registry = dict.fromkeys(REGISTRY_COLUMNS, "")
    registry.update(
        id="SYNTHETIC-SYSTEM-INPUTS",
        category="C",
        priority="P1",
        name=f"Fictional {spec['discipline']} inputs",
        publisher="Synthetic Integration Fixture Generator",
        source_url="https://source.example.invalid/synthetic",
        download_api_url="https://source.example.invalid/synthetic.json",
        format="JSON",
        evidence_class="synthetic_demo",
        verification_status="Verified",
        verified_on=datetime.now(UTC).date().isoformat(),
        latest_verified_publication_date=(datetime.now(UTC) - timedelta(days=1)).date().isoformat(),
        licence="Synthetic fixture",
        rights_status="Synthetic fixture permission",
        acquired_into_backend="No",
    )
    registry_path = workdir / "registry.synthetic.csv"
    with registry_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTRY_COLUMNS)
        writer.writeheader()
        writer.writerow(registry)
    policy_path = workdir / "acquisition.synthetic.json"
    policy_path.write_text(
        json.dumps(
            {
                registry["id"]: {
                    "adapter": "reviewed_json",
                    "format": "json",
                    "reuse_reviewed": True,
                    "instructions": "Only explicitly labelled synthetic source inputs.",
                }
            }
        ),
        encoding="utf-8",
    )
    report = run_ingestion(
        database,
        registry_path=registry_path,
        policy_path=policy_path,
        dataset_ids=[registry["id"]],
        local_path=path,
        retrieved_at=datetime.now(UTC) - timedelta(hours=1),
        is_synthetic=True,
    )[0]
    if report["status"] != "SUCCEEDED":
        raise IntegrationFailure("source_admission: synthetic reviewed importer failed")
    with database.session_factory() as session:
        version = session.get(DatasetVersion, UUID(report["version_id"]))
        occupations = {
            row.external_id.removeprefix("occupation:"): str(row.id)
            for row in session.scalars(
                select(Occupation).where(Occupation.version_id == version.id)
            )
        }
        skill_ids = {
            row.external_id.removeprefix("skill:"): str(row.id)
            for row in session.scalars(select(Skill).where(Skill.version_id == version.id))
        }
    return occupations, skill_ids, report


def _curriculum_passages(database, spec, revision_id, courses, inputs, skills):
    """Record reviewed fictional input passages; never write derived findings."""
    anchors = {}
    with database.session_factory() as session:
        for item in inputs:
            if not item.get("quote"):
                continue
            course = session.get(Course, UUID(courses[item["key"]]["id"]))
            course.detailed_syllabus_available = True
            document = Document(
                programme_revision_id=UUID(revision_id),
                course_id=course.id,
                filename=f"synthetic-{item['key']}.json",
                document_kind=DocumentKind.SYLLABUS,
                format=DocumentFormat.JSON,
                content_sha256=hashlib.sha256(item["quote"].encode()).hexdigest(),
                parser_version="synthetic-reviewed-input-1",
                uploaded_at=datetime.now(UTC) - timedelta(minutes=1),
                is_synthetic=True,
                metadata_json={
                    "content_reviewed": True,
                    "demonstration_reviewed": item.get("demonstration_reviewed", False),
                    "analysis_permissions": RIGHTS,
                },
            )
            session.add(document)
            session.flush()
            anchor = DocumentAnchor(
                document_id=document.id,
                locator=f"synthetic:reviewed:{item['key']}",
                excerpt=item["quote"],
                is_synthetic=True,
            )
            session.add(anchor)
            session.flush()
            anchors[item["key"]] = {"id": str(anchor.id), "quote": anchor.excerpt}
        audit = Document(
            programme_revision_id=UUID(revision_id),
            filename="synthetic-complete-scope-audit.json",
            document_kind=DocumentKind.SUPPORTING,
            format=DocumentFormat.JSON,
            content_sha256=hashlib.sha256(spec["gap"]["quote"].encode()).hexdigest(),
            parser_version="synthetic-reviewed-audit-1",
            uploaded_at=datetime.now(UTC) - timedelta(minutes=1),
            is_synthetic=True,
            metadata_json={
                "content_reviewed": True,
                "gap_reviewed": True,
                "negative_skill_ids": [skills[spec["gap"]["skill"]]],
                "analysis_permissions": RIGHTS,
            },
        )
        session.add(audit)
        session.flush()
        anchor = DocumentAnchor(
            document_id=audit.id,
            locator="synthetic:all-imported-course-audit",
            excerpt=spec["gap"]["quote"],
            is_synthetic=True,
        )
        session.add(anchor)
        session.flush()
        anchors["audit"] = {"id": str(anchor.id), "quote": anchor.excerpt}
        session.commit()
    return anchors


def _career_request(spec, revision_id, courses, skills, occupations, anchors, mode):
    review = {
        "reviewed": True,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "basis": spec["review_basis"],
        "reviewer_reference": "explicit-synthetic-operator-input",
    }
    return {
        "revision_id": revision_id,
        "mode": mode,
        "mappings": [
            {
                "occupation_id": identifier,
                "taxonomy": spec["taxonomy"],
                "external_id": f"occupation:{key}",
                "discipline": spec["discipline"],
                "malaysia_applicability": spec["malaysia_applicability"],
                "requirements_complete": True,
                **review,
            }
            for key, identifier in occupations.items()
        ],
        "assertions": [
            {
                "skill_id": skills[item["skill"]],
                "course_id": courses[item["course"]]["id"],
                "anchor_id": anchors[item["course"]]["id"],
                "quote": anchors[item["course"]]["quote"],
                "support": item["support"],
                "extent": item["extent"],
                **review,
            }
            for item in spec["support"]
        ],
        "gaps": [
            {
                "skill_id": skills[spec["gap"]["skill"]],
                "anchor_id": anchors["audit"]["id"],
                "quote": anchors["audit"]["quote"],
                "covered_course_ids": [row["id"] for row in courses.values()],
                "completeness_confirmed": True,
                **review,
            }
        ],
    }


def _resource_inputs(database, spec, skills):
    resources = []
    with database.session_factory() as session:
        for key in ("model", "security"):
            label = next(row["label"] for row in spec["skills"] if row["key"] == key)
            title = f"Fictional {label} review workbook"
            url = f"https://resource.example.invalid/{spec['discipline']}/{key}"
            quote = (
                f"Synthetic original: proposed practical review of {label}. "
                + (
                    "Provider learning effort is 3 hours; assessment and calendar time "
                    "are unspecified."
                    if key == "model"
                    else "Duration and prerequisites are not specified."
                )
                + " Access and cost are unknown; no actual training offer exists."
            )
            source = Source(
                publisher="Synthetic Integration Fixture Generator",
                title=title,
                url=url,
                evidence_class="synthetic_demo",
                is_synthetic=True,
                collected_at=datetime.now(UTC) - timedelta(minutes=1),
            )
            dataset = Dataset(
                registry_key=f"SYNTHETIC-SYSTEM-RESOURCE-{key.upper()}",
                name=title,
                category="learning_resource",
                is_synthetic=True,
            )
            session.add_all([source, dataset])
            session.flush()
            version = DatasetVersion(
                dataset_id=dataset.id,
                source_id=source.id,
                content_sha256=hashlib.sha256(quote.encode()).hexdigest(),
                parser_version="synthetic-original-resource-1",
                retrieved_at=datetime.now(UTC) - timedelta(minutes=1),
                publication_date=datetime.now(UTC).date().isoformat(),
                artifact_url=url,
                is_synthetic=True,
                metadata_json={"analysis_permissions": RIGHTS},
            )
            session.add(version)
            session.flush()
            facts = {
                "name": title,
                "resource_type": "synthetic_workbook",
                "url": url,
                "related_skill_ids": [skills[key]],
                "prerequisite_skill_ids": [],
                "access_status": "unknown",
                "cost_status": "unknown",
                "cost_amount": None,
                "cost_currency": None,
                "verified_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                "licence_limitations": (
                    "Synthetic original-resource fixture only; no actual provider "
                    "availability or endorsement."
                ),
            }
            if key == "model":
                facts.update(duration_hours=3, duration_component="learning")
            reference = EvidenceReference(
                version_id=version.id,
                locator=f"synthetic:resource:{key}",
                excerpt=quote,
                review_status="reviewed",
                is_synthetic=True,
                metadata_json={"learning_resource": facts, "analysis_permissions": RIGHTS},
            )
            session.add(reference)
            session.flush()
            resources.append({"key": key, "id": str(reference.id), "quote": quote})
        session.commit()
    return resources


def _sdgs(database):
    path = ROOT / "data/reference_packs/un-sdg-resolution.reviewed.json"
    original = json.loads(path.read_text(encoding="utf-8"))["metadata"]["original_retrieved_at"]
    report = run_ingestion(
        database,
        registry_path=ROOT / "data/dataset_registry.csv",
        policy_path=ROOT / "data/evidence_acquisition.json",
        dataset_ids=["F-UN-SDG-RES70-1"],
        local_path=path,
        retrieved_at=datetime.fromisoformat(original),
    )[0]
    if report["status"] not in {"SUCCEEDED", "UNCHANGED"}:
        raise IntegrationFailure("source_admission: official UN pack import failed")
    with database.session_factory() as session:
        target = session.scalar(
            select(SDGReference).where(
                SDGReference.code == "4.4", SDGReference.is_synthetic.is_(False)
            )
        )
        return str(target.id), report


def _plan_request(career, recommendations, phase4_id, resources, skills, target, mode):
    by_skill = {row["result_json"]["skill_id"]: row for row in recommendations}
    pointers = {row["id"]: row for row in career["result_json"]["evidence"]}
    reviewed = datetime.now(UTC).isoformat()
    mappings = []
    for key in ("model", "security"):
        recommendation = by_skill[skills[key]]
        if recommendation["result_json"]["category"] in {"request_review", "no_change"}:
            continue
        citations = [
            row
            for row in recommendation["result_json"]["citations"]
            if pointers[row["reference_id"]]["facts"].get("skill_id") == skills[key]
        ]
        mappings.append(
            {
                "recommendation_id": recommendation["id"],
                "sdg_reference_id": target,
                "mechanism": "assessed_competency_access",
                "rationale": (
                    "Explicit fictional review: a proposed assessed technical competency "
                    "activity may contribute to relevant skills preparation under target 4.4; "
                    "no achieved SDG outcome, employment or proficiency is claimed."
                ),
                "citations": citations[-1:],
                "reviewed": True,
                "reviewed_at": reviewed,
            }
        )
    model = next(row for row in resources if row["key"] == "model")
    return {
        "mode": mode,
        "phase4_analysis_id": phase4_id,
        "recommendation_ids": [row["id"] for row in recommendations],
        "resources": [
            {
                "reference_id": row["id"],
                "skill_id": skills[row["key"]],
                "reviewed": True,
                "reviewed_at": reviewed,
                "basis": "Explicit fictional source-resource-to-competency review.",
            }
            for row in resources
        ],
        "durations": [
            {
                "recommendation_id": by_skill[skills["model"]]["id"],
                "step_key": "practice",
                "hours": 3,
                "component": "learning",
                "basis_type": "source",
                "reference_id": f"learning_resource:{model['id']}",
                "quote": model["quote"],
                "basis": "Synthetic provider effort only; other durations remain unknown.",
                "reviewed": True,
                "reviewed_at": reviewed,
            }
        ]
        if by_skill[skills["model"]]["result_json"]["category"]
        not in {"request_review", "no_change"}
        else [],
        "sdg_mappings": mappings,
    }


def _independent_read(database, plan_id, phase4_id, career_id, schema):
    if database.engine.dialect.name != "postgresql":
        return {"status": "UNIT_SQLITE_ONLY", "postgresql_verified": False}
    with database.engine.connect() as connection:
        quoted = connection.dialect.identifier_preparer.quote(schema)
        connection.exec_driver_sql(f"SET search_path TO {quoted}")
        with Session(bind=connection) as session:
            plan, career, phase4 = (
                session.get(ActionPlanRun, UUID(plan_id)),
                session.get(CareerRun, UUID(career_id)),
                session.get(AnalysisRun, UUID(phase4_id)),
            )
            if (
                not all((plan, career, phase4))
                or not plan.result_json
                or not career.result_json
                or not phase4.fingerprint
            ):
                raise IntegrationFailure(
                    "independent_persistence: committed predecessor/result missing"
                )
            return {
                "status": "PASS",
                "postgresql_verified": True,
                "plan_fingerprint": plan.fingerprint,
                "career_fingerprint": career.fingerprint,
                "phase4_fingerprint": phase4.fingerprint,
                "programme_revision_id": str(plan.programme_revision_id),
            }


def run_synthetic_system(
    database,
    settings,
    *,
    workdir: Path,
    course_count=6,
    discipline="computing",
    mode="offline",
    worker: Callable = run_once,
    fixture=None,
    input_transform=None,
    include_replay=True,
):
    """Run committed cross-phase acceptance; callers explicitly provide mocked mode.

    The caller owns the disposable database/schema. The default performs no model
    call. ``mode='live'`` is reserved for an explicitly installed mock harness;
    it does not authorise a real paid request. This helper never enables gates.
    """
    from fastapi.testclient import TestClient

    from shiftos.main import create_app

    if (
        settings.app_env != "test"
        or mode not in {"offline", "live"}
        or not 6 <= course_count <= 200
    ):
        raise ValueError("Integration requires test settings and 6–200 synthetic courses")
    if (
        settings.research_enabled
        or settings.gemini_enabled
        or settings.analysis_gemini_fallback_enabled
    ):
        raise ValueError("Synthetic integration requires research and Gemini disabled")
    if mode == "live" and not getattr(worker, "synthetic_mock_only", False):
        raise ValueError("Mocked mode requires an explicitly marked non-network worker harness")
    spec = fixture_for(discipline, fixture)
    spec["gap"]["quote"] = spec["gap"]["quote"].replace(
        "all four listed courses", f"all {course_count} imported courses"
    )
    if input_transform is not None:
        input_transform(spec)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    metrics = _Metrics(database.engine)
    event.listen(database.engine, "before_cursor_execute", metrics.query)
    started, responses = time.perf_counter(), {}
    try:
        with database.session_factory() as session:
            schema = (
                session.scalar(text("SELECT current_schema()"))
                if database.engine.dialect.name == "postgresql"
                else None
            )
        headers = {}
        if settings.analysis_write_token:
            headers["X-Analysis-Token"] = settings.analysis_write_token.get_secret_value()
        if settings.catalogue_write_token:
            headers["X-Catalogue-Token"] = settings.catalogue_write_token.get_secret_value()
        with TestClient(create_app(settings=settings, database=database)) as client:
            client.headers.update(headers)
            with metrics.measure("curriculum_import"):
                institution, programme, revision, courses, inputs, import_body, curriculum = (
                    _curriculum(client, database, settings, spec, course_count, worker)
                )
                responses["curriculum"] = curriculum
            with metrics.measure("source_admission"):
                occupations, skills, source_report = _taxonomy(database, workdir, spec)
                anchors = _curriculum_passages(database, spec, revision, courses, inputs, skills)
                resources = _resource_inputs(database, spec, skills)
                target, sdg_report = _sdgs(database)
            with metrics.measure("phase4"):
                queued = _response(
                    client.post(
                        f"/api/v1/programmes/{programme}/analyses",
                        json={"mode": mode, "research": False},
                    ),
                    202,
                    "phase4",
                )
                phase4 = _worker(
                    client,
                    database,
                    settings,
                    queued,
                    f"/api/v1/analyses/{queued['id']}",
                    "phase4",
                    worker,
                )
                responses["phase4"] = phase4
                phase4_courses = {"items": [], "total": 0, "limit": 100, "offset": 0}
                for offset in range(0, course_count, 100):
                    page = _response(
                        client.get(
                            f"/api/v1/analyses/{phase4['id']}/courses",
                            params={"limit": 100, "offset": offset},
                        ),
                        200,
                        "phase4_course_results",
                    )
                    phase4_courses["items"].extend(page["items"])
                    phase4_courses["total"] = page["total"]
                responses["phase4_courses"] = phase4_courses
            with metrics.measure("career"):
                predecessor_ids = {row["course_id"] for row in phase4_courses["items"]}
                if phase4["programme_revision_id"] != revision or predecessor_ids != {
                    row["id"] for row in courses.values()
                }:
                    raise IntegrationFailure("career: committed Phase 4 course lineage disagrees")
                # Consume the committed screening inventory, while competency truth
                # still comes from independently reviewed original source passages.
                consumed_courses = {
                    key: row for key, row in courses.items() if row["id"] in predecessor_ids
                }
                career_body = _career_request(
                    spec, revision, consumed_courses, skills, occupations, anchors, mode
                )
                queued = _response(
                    client.post(
                        f"/api/v1/programmes/{programme}/career-analyses", json=career_body
                    ),
                    202,
                    "career",
                )
                career = _worker(
                    client,
                    database,
                    settings,
                    queued,
                    f"/api/v1/career-analyses/{queued['id']}",
                    "career",
                    worker,
                )
                responses["career"] = career
                recommendations = _response(
                    client.get(
                        f"/api/v1/career-analyses/{career['id']}/recommendations",
                        params={"limit": 100},
                    ),
                    200,
                    "recommendations",
                )["items"]
                responses["recommendations"] = recommendations
            with metrics.measure("recommendation_review"):
                review_receipts = []
                for row in recommendations:
                    category = row["result_json"]["category"]
                    decision = (
                        "no_change_required"
                        if category == "no_change"
                        else "under_review"
                        if category == "request_review"
                        else "approved"
                    )
                    review_receipts.append(
                        _response(
                            client.post(
                                f"/api/v1/career-recommendations/{row['id']}/reviews",
                                json={
                                    "decision": decision,
                                    "reason": (
                                        "Explicit fictional authenticated operator consideration "
                                        "for acceptance only; no real academic approval."
                                    ),
                                    "expected_recommendation_version": row["version_sha256"],
                                },
                            ),
                            201,
                            "recommendation_review",
                        )
                    )
                responses["recommendation_reviews"] = review_receipts
            with metrics.measure("action_plan"):
                plan_body = _plan_request(
                    career, recommendations, phase4["id"], resources, skills, target, mode
                )
                plan_body["idempotency_key"] = "synthetic-system-plan-1"
                plan_path = f"/api/v1/career-analyses/{career['id']}/action-plans"
                queued = _response(client.post(plan_path, json=plan_body), 202, "action_plan")
                plan = _worker(
                    client,
                    database,
                    settings,
                    queued,
                    f"/api/v1/action-plans/{queued['id']}",
                    "action_plan",
                    worker,
                )
                responses["plan"] = plan
            with metrics.measure("plan_review"):
                responses["plan_review"] = _response(
                    client.post(
                        f"/api/v1/action-plans/{plan['id']}/reviews",
                        json={
                            "decision": "under_review",
                            "reason": (
                                "Explicit fictional operator review; implementation is not "
                                "authorised and no named academic identity is asserted."
                            ),
                            "expected_plan_fingerprint": plan["fingerprint"],
                        },
                    ),
                    201,
                    "plan_review",
                )
            replay = {}
            if include_replay:
                with metrics.measure("idempotent_replay"):
                    repeated = _response(
                        client.post(plan_path, json=plan_body), 202, "idempotent_replay"
                    )
                    unchanged = (
                        repeated["id"] == plan["id"]
                        and repeated["fingerprint"] == plan["fingerprint"]
                    )
                    if not unchanged:
                        raise IntegrationFailure(
                            "idempotent_replay: prior job/result identity changed"
                        )
                    replay["repeat_consistency"] = {
                        "status": "pass",
                        "observed": (
                            "Identical API request returned the same job, plan ID and fingerprint."
                        ),
                    }
                with metrics.measure("assumption_replay"):
                    changed = json.loads(json.dumps(plan_body))
                    changed["idempotency_key"] = "synthetic-system-plan-assumption-2"
                    changed["previous_plan_id"] = plan["id"]
                    changed["durations"][0].update(
                        hours=2,
                        basis_type="planning_assumption",
                        reference_id=None,
                        quote=None,
                        basis=(
                            "Explicit fictional changed workload assumption; "
                            "not an original-provider fact."
                        ),
                    )
                    queued = _response(
                        client.post(plan_path, json=changed), 202, "assumption_replay"
                    )
                    revised = _worker(
                        client,
                        database,
                        settings,
                        queued,
                        f"/api/v1/action-plans/{queued['id']}",
                        "assumption_replay",
                        worker,
                    )
                    historical = _response(
                        client.get(f"/api/v1/action-plans/{plan['id']}"), 200, "historical_read"
                    )
                    replay.update(
                        {
                            "assumption": revised["result_json"]["reassessment"],
                            "previous_fingerprint_unchanged": historical["fingerprint"]
                            == plan["fingerprint"],
                            "new_plan_id": revised["id"],
                            "approval_transferred": bool(
                                _response(
                                    client.get(f"/api/v1/action-plans/{revised['id']}/reviews"),
                                    200,
                                    "new_plan_reviews",
                                )["items"]
                            ),
                        }
                    )
                    responses["replayed_plan"] = revised
            with metrics.measure("api_retrieval"):
                responses["courses"] = _response(
                    client.get(f"/api/v1/programmes/{programme}/courses", params={"limit": 100}),
                    200,
                    "api_retrieval",
                )
                responses["pathways"] = _response(
                    client.get(f"/api/v1/action-plans/{plan['id']}/pathways"), 200, "api_retrieval"
                )
                responses["scenarios"] = _response(
                    client.get(f"/api/v1/action-plans/{plan['id']}/scenarios"), 200, "api_retrieval"
                )
                responses["sdg"] = _response(
                    client.get(f"/api/v1/action-plans/{plan['id']}/sdg"), 200, "api_retrieval"
                )
            with metrics.measure("independent_persistence"):
                persistence = _independent_read(
                    database, plan["id"], phase4["id"], career["id"], schema
                )
        packet_ids = set(plan["result_json"]["overview"]["course_ids"])
        if (
            packet_ids != {row["id"] for row in courses.values()}
            or plan["result_json"]["overview"]["phase4_context"]["status"] != "linked_same_revision"
        ):
            raise IntegrationFailure(
                "lineage: action plan lost imported courses or exact Phase 4 predecessor"
            )
        return {
            "fixture_id": "phase7-system-integration-1",
            "is_synthetic": True,
            "provider_execution": "mocked" if mode == "live" else "offline",
            "live_requests": 0,
            "observed_cost": None,
            "course_count": course_count,
            "discipline": discipline,
            "status": "PASS",
            "labels": {
                "institution_id": institution["id"],
                "programme_id": programme,
                "revision_id": revision,
                "courses": {key: row["id"] for key, row in courses.items()},
                "skills": skills,
                "occupations": occupations,
                "anchors": anchors,
            },
            "lineage": {
                "curriculum_job_id": curriculum["id"],
                "phase4_id": phase4["id"],
                "phase4_fingerprint": phase4["fingerprint"],
                "career_id": career["id"],
                "career_fingerprint": career["fingerprint"],
                "plan_id": plan["id"],
                "plan_fingerprint": plan["fingerprint"],
                "revision_id": revision,
                "same_revision": phase4["programme_revision_id"]
                == career["programme_revision_id"]
                == plan["programme_revision_id"]
                == revision,
                "career_consumed_phase4_course_ids": sorted(predecessor_ids),
                "shared_source_version_ids": sorted(
                    {row["version_id"] for row in phase4["manifest_json"]["packet"]["references"]}
                    & {row["version_id"] for row in career["result_json"]["evidence"]}
                ),
            },
            "requests": {"curriculum": import_body, "career": career_body, "plan": plan_body},
            "responses": responses,
            "validated": {
                "phase4": {
                    **phase4["summary_json"],
                    "courses": [row["result_json"] for row in phase4_courses["items"]],
                },
                "career": career["result_json"],
                "plan": plan["result_json"],
            },
            "source_admission": {"synthetic": source_report, "official_un": sdg_report},
            "persistence": persistence,
            "replay": replay,
            "metrics": {
                "stages": metrics.stages,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "sql_statements": sum(metrics.counts.values()),
                "plan_response_bytes": len(json.dumps(plan).encode()),
                "python_peak_bytes": None,
            },
            "limitations": [
                "Synthetic software consistency, not real academic accuracy "
                "or named-reviewer identity.",
                "Model calls are mocked/offline; no real token, network latency "
                "or billing observation.",
                "Brave original-source admission remains PARTIAL; "
                "no external research is attempted.",
            ],
        }
    finally:
        event.remove(database.engine, "before_cursor_execute", metrics.query)


def verify_change_replay(database, settings, receipt, operation):
    """One explicitly selected synthetic mutation against a fresh eligible plan.

    The caller creates a fresh case per operation: previous invalidation cannot
    count as proof that a second change independently invalidated the same plan.
    No model or research request is made. Original derived results stay immutable.
    """
    from fastapi.testclient import TestClient

    from shiftos.main import create_app

    if settings.app_env != "test" or receipt.get("is_synthetic") is not True:
        raise ValueError("Change replay requires an explicitly synthetic test receipt")
    if operation not in {
        "source_withdrawn",
        "source_changed",
        "review_rejected",
        "curriculum_revision",
    }:
        raise ValueError("Choose a bounded documented change replay operation")
    plan_id = receipt["lineage"]["plan_id"]
    with database.session_factory() as session:
        stored = session.get(ActionPlanRun, UUID(plan_id))
        if (
            stored is None
            or not stored.is_synthetic
            or stored.fingerprint != receipt["lineage"]["plan_fingerprint"]
        ):
            raise ValueError("Change replay does not own this synthetic plan identity")
    headers = {"X-Analysis-Token": settings.analysis_write_token.get_secret_value()}
    if settings.catalogue_write_token:
        headers["X-Catalogue-Token"] = settings.catalogue_write_token.get_secret_value()
    with TestClient(create_app(settings=settings, database=database)) as client:
        client.headers.update(headers)
        original = _response(client.get(f"/api/v1/action-plans/{plan_id}"), 200, operation)
        if original["needs_evidence_revalidation"]:
            raise ValueError("Each causal replay requires a fresh eligible original plan")
        if operation in {"source_withdrawn", "source_changed"}:
            pointer = next(
                row
                for row in original["result_json"]["evidence"]
                if row["kind"] == "learning_resource" and row["is_synthetic"]
            )
            with database.session_factory() as session:
                if operation == "source_withdrawn":
                    version = session.get(DatasetVersion, UUID(pointer["version_id"]))
                    version.metadata_json = {**version.metadata_json, "rights_withdrawn": True}
                else:
                    reference = session.get(
                        EvidenceReference, UUID(pointer["evidence_reference_id"])
                    )
                    reference.excerpt += (
                        " Synthetic source correction: require renewed original review."
                    )
                session.commit()
        elif operation == "review_rejected":
            recommendation = next(
                row
                for row in receipt["responses"]["recommendations"]
                if row["result_json"]["skill_id"] == receipt["labels"]["skills"]["security"]
            )
            _response(
                client.post(
                    f"/api/v1/career-recommendations/{recommendation['id']}/reviews",
                    json={
                        "decision": "rejected",
                        "reason": (
                            "Fictional latest consideration decision rejects this proposal."
                        ),
                        "expected_recommendation_version": recommendation["version_sha256"],
                    },
                ),
                201,
                operation,
            )
        else:
            body = json.loads(json.dumps(receipt["requests"]["curriculum"]))
            body["idempotency_key"] = "synthetic-system-curriculum-revised-2"
            course = body["programmes"][0]["courses"][-1]
            course["course_name"] += " Revised"
            course["source_excerpt"] = course["course_name"]
            queued = _response(
                client.post(
                    f"/api/v1/institutions/{receipt['labels']['institution_id']}/imports", json=body
                ),
                202,
                operation,
            )
            _worker(
                client,
                database,
                settings,
                queued,
                f"/api/v1/catalogue/jobs/{queued['id']}",
                operation,
                run_once,
            )
        invalidated = _response(client.get(f"/api/v1/action-plans/{plan_id}"), 200, operation)
        attempted = client.post(
            f"/api/v1/action-plans/{plan_id}/reviews",
            json={
                "decision": "approved",
                "reason": "Synthetic stale approval must be rejected.",
                "expected_plan_fingerprint": original["fingerprint"],
            },
        )
        with database.session_factory() as session:
            stored = session.get(ActionPlanRun, UUID(plan_id))
            preserved = (
                stored.fingerprint == original["fingerprint"]
                and stored.result_json == original["result_json"]
            )
        passed = (
            invalidated["needs_evidence_revalidation"]
            and attempted.status_code == 409
            and preserved
        )
        return {
            "status": "pass" if passed else "fail",
            "observed": (
                f"Fresh eligible synthetic plan followed by {operation}: current disclosure/"
                "review invalidated; immutable historical fingerprint/result preserved."
            ),
            "api_status": invalidated["status"],
            "approval_http_status": attempted.status_code,
            "historical_result_preserved": preserved,
        }


def replay_curriculum_revision(database, settings, receipt):
    """Commit a new inventory and all downstream jobs without copying old approvals.

    The revised curriculum starts title-only. Old reviewed passages/assertions and
    occupation mappings are deliberately not transferred to its new revision.
    The resulting explicit insufficiency is the supported outcome, not a failure.
    """
    from fastapi.testclient import TestClient

    from shiftos.main import create_app

    if settings.app_env != "test" or receipt.get("is_synthetic") is not True:
        raise ValueError("Revision replay requires a synthetic test receipt")
    old_plan_id = receipt["lineage"]["plan_id"]
    with database.session_factory() as session:
        original = session.get(ActionPlanRun, UUID(old_plan_id))
        if original is None or not original.is_synthetic:
            raise ValueError("Revision replay does not own this synthetic plan")
        old_result, old_fingerprint = original.result_json, original.fingerprint
    headers = {"X-Analysis-Token": settings.analysis_write_token.get_secret_value()}
    if settings.catalogue_write_token:
        headers["X-Catalogue-Token"] = settings.catalogue_write_token.get_secret_value()
    with TestClient(create_app(settings=settings, database=database)) as client:
        client.headers.update(headers)
        body = json.loads(json.dumps(receipt["requests"]["curriculum"]))
        body["idempotency_key"] = "synthetic-positive-revision-2"
        course = body["programmes"][0]["courses"][-1]
        course["course_name"] += " Revised"
        course["source_excerpt"] = course["course_name"]
        queued = _response(
            client.post(
                f"/api/v1/institutions/{receipt['labels']['institution_id']}/imports", json=body
            ),
            202,
            "revision_import",
        )
        imported = _worker(
            client,
            database,
            settings,
            queued,
            f"/api/v1/catalogue/jobs/{queued['id']}",
            "revision_import",
            run_once,
        )
        revision = imported["result"]["entries"][0]["revision_id"]
        programme = receipt["labels"]["programme_id"]
        queued = _response(
            client.post(
                f"/api/v1/programmes/{programme}/analyses",
                json={"revision_id": revision, "mode": "offline", "research": False},
            ),
            202,
            "revision_phase4",
        )
        phase4 = _worker(
            client,
            database,
            settings,
            queued,
            f"/api/v1/analyses/{queued['id']}",
            "revision_phase4",
            run_once,
        )
        queued = _response(
            client.post(
                f"/api/v1/programmes/{programme}/career-analyses",
                json={
                    "revision_id": revision,
                    "mode": "offline",
                    "mappings": [],
                    "assertions": [],
                    "gaps": [],
                },
            ),
            202,
            "revision_career",
        )
        career = _worker(
            client,
            database,
            settings,
            queued,
            f"/api/v1/career-analyses/{queued['id']}",
            "revision_career",
            run_once,
        )
        queued = _response(
            client.post(
                f"/api/v1/career-analyses/{career['id']}/action-plans",
                json={"mode": "offline", "phase4_analysis_id": phase4["id"]},
            ),
            202,
            "revision_plan",
        )
        plan = _worker(
            client,
            database,
            settings,
            queued,
            f"/api/v1/action-plans/{queued['id']}",
            "revision_plan",
            run_once,
        )
        reviews = _response(
            client.get(f"/api/v1/action-plans/{plan['id']}/reviews"), 200, "revision_review_history"
        )
        wrong_approval = client.post(
            f"/api/v1/action-plans/{plan['id']}/reviews",
            json={
                "decision": "approved",
                "reason": "A historical fingerprint must not approve a new plan.",
                "expected_plan_fingerprint": old_fingerprint,
            },
        )
        historical = _response(
            client.get(f"/api/v1/action-plans/{old_plan_id}"), 200, "revision_historical_read"
        )
    with database.session_factory() as session:
        original = session.get(ActionPlanRun, UUID(old_plan_id))
        preserved = original.fingerprint == old_fingerprint and original.result_json == old_result
    result = plan["result_json"]
    same_revision = (
        phase4["programme_revision_id"]
        == career["programme_revision_id"]
        == plan["programme_revision_id"]
        == revision
    )
    new_course_ids = set(result["overview"]["course_ids"])
    account_for_all = len(new_course_ids) == receipt["course_count"] and new_course_ids == set(
        career["result_json"]["course_ids"]
    )
    passed = (
        same_revision
        and revision != receipt["lineage"]["revision_id"]
        and account_for_all
        and preserved
        and historical["needs_evidence_revalidation"]
        and wrong_approval.status_code == 409
        and not reviews["items"]
        and result["review"]["academic_approval"] is False
    )
    return {
        "status": "pass" if passed else "fail",
        "observed": (
            "New curriculum, Phase 4, career and plan jobs committed for a new exact "
            "revision; title-only unknowns and manual review retained."
        ),
        "revision_id": revision,
        "phase4": phase4,
        "career": career,
        "plan": plan,
        "all_courses_accounted_for": account_for_all,
        "same_revision": same_revision,
        "historical_result_preserved": preserved,
        "previous_plan_requires_revalidation": historical["needs_evidence_revalidation"],
        "old_fingerprint_approval_http_status": wrong_approval.status_code,
        "new_review_count": reviews["total"],
        "manual_academic_review_required": not result["review"]["academic_approval"],
    }
