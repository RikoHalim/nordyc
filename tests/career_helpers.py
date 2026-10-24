"""Labelled fictional source records for Phase 5; never live academic evidence."""

import csv
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from shiftos.core.config import Settings
from shiftos.core.enums import CourseType, DocumentFormat, DocumentKind, EvidenceClass
from shiftos.models import (
    Course,
    Dataset,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Institution,
    Occupation,
    OccupationSkill,
    Programme,
    ProgrammeRevision,
    Skill,
    Source,
)
from shiftos.schemas.career import CareerRequest
from shiftos.services.evidence.pipeline import run_ingestion
from shiftos.services.evidence.registry import REGISTRY_COLUMNS

FIXTURE = Path(__file__).resolve().parents[1] / "examples/career_alignment.synthetic.json"
TOKEN = "SYNTHETIC-CAREER-OPERATOR"


def career_settings(**overrides):
    values = dict(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        analysis_model_provider="replit_claude",
        claude_enabled=False,
        gemini_enabled=False,
        research_enabled=False,
        analysis_external_processing_allowed=False,
        analysis_write_token=TOKEN,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


def seed_career(session):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["is_synthetic"] is True
    # Relative dates keep the fixture current without relabelling a real publication.
    now = datetime.now(UTC) - timedelta(minutes=5)
    reviewed_at = now - timedelta(hours=1)
    collected = now - timedelta(days=1)

    def identity(key):
        return uuid5(NAMESPACE_URL, f"{data['fixture_id']}:{key}")

    university_source = Source(
        id=identity("curriculum-source"),
        publisher=data["institution"],
        title="Synthetic curriculum passages and explicit audit",
        url="https://example.invalid/synthetic-curriculum",
        evidence_class=EvidenceClass.SYNTHETIC_DEMO,
        is_synthetic=True,
        collected_at=collected,
        content_hash=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        license_status="synthetic fixture permission",
    )
    institution = Institution(
        id=identity("institution"), name=data["institution"], is_synthetic=True
    )
    session.add_all([university_source, institution])
    session.flush()
    programme = Programme(
        id=identity("programme"),
        institution_id=institution.id,
        name=data["programme"],
        discipline_key=data["discipline"],
        is_synthetic=True,
    )
    session.add(programme)
    session.flush()
    revision = ProgrammeRevision(
        id=identity("revision"),
        programme_id=programme.id,
        version_label="synthetic-complete-1",
        is_synthetic=True,
        fixture_id=data["fixture_id"],
        fixture_sha256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        metadata_json={"label": data["label"], "inventory_scope": "all four fictional courses"},
    )
    session.add(revision)
    session.flush()
    programme.active_revision_id = revision.id
    courses, anchors, documents = {}, {}, {}
    permissions = dict(
        internal_analysis_allowed=True,
        external_model_allowed=True,
        excerpt_output_allowed=True,
        basis="Explicit labelled synthetic fixture content and review permission",
    )
    for item in data["courses"]:
        key = item["key"]
        course = Course(
            id=identity(f"course:{key}"),
            programme_revision_id=revision.id,
            course_name=item["title"],
            course_type=CourseType.COMPULSORY,
            is_synthetic=True,
            source_id=university_source.id,
            source_locator=f"synthetic:course:{key}",
            detailed_syllabus_available=bool(item["quote"]),
        )
        session.add(course)
        session.flush()
        courses[key] = course
        if item["quote"]:
            document = Document(
                id=identity(f"document:{key}"),
                programme_revision_id=revision.id,
                course_id=course.id,
                filename=f"synthetic-{key}.json",
                document_kind=DocumentKind.SYLLABUS,
                format=DocumentFormat.JSON,
                content_sha256=hashlib.sha256(item["quote"].encode()).hexdigest(),
                parser_version="synthetic-reviewed-1",
                uploaded_at=collected,
                is_synthetic=True,
                metadata_json={
                    "content_reviewed": True,
                    "demonstration_reviewed": item.get("demonstration_reviewed", False),
                    "analysis_permissions": permissions,
                },
            )
            session.add(document)
            session.flush()
            anchor = DocumentAnchor(
                id=identity(f"anchor:{key}"),
                document_id=document.id,
                locator=f"synthetic:{key}:outcome",
                excerpt=item["quote"],
                is_synthetic=True,
            )
            session.add(anchor)
            session.flush()
            anchors[key] = anchor
            documents[key] = document
    taxonomy_source = Source(
        id=identity("taxonomy-source"),
        publisher="Fictional Occupation Benchmark Authority",
        title="Synthetic occupational requirements",
        url="https://example.invalid/synthetic-taxonomy",
        evidence_class=EvidenceClass.SYNTHETIC_DEMO,
        is_synthetic=True,
        collected_at=collected,
        license_status="synthetic fixture permission",
    )
    dataset = Dataset(
        id=identity("dataset"),
        registry_key="SYNTHETIC-CAREER-REQUIREMENTS",
        name="Synthetic occupation requirements",
        category="occupation",
        is_synthetic=True,
    )
    session.add_all([taxonomy_source, dataset])
    session.flush()
    version = DatasetVersion(
        id=identity("version"),
        dataset_id=dataset.id,
        source_id=taxonomy_source.id,
        content_sha256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        parser_version="synthetic-career-1",
        retrieved_at=collected,
        publication_date=collected.date().isoformat(),
        artifact_url=taxonomy_source.url,
        metadata_json={
            "edition": "synthetic-1",
            "language": "en",
            "geography": "fictional",
            "analysis_permissions": permissions,
        },
        is_synthetic=True,
    )
    session.add(version)
    session.flush()
    references = {}

    def referenced(key, excerpt):
        ref = EvidenceReference(
            id=identity(f"evidence:{key}"),
            version_id=version.id,
            locator=f"synthetic:{key}",
            excerpt=excerpt,
            review_status="reviewed",
            is_synthetic=True,
        )
        session.add(ref)
        session.flush()
        references[key] = ref
        return dict(
            id=identity(key),
            version_id=version.id,
            evidence_id=ref.id,
            external_id=key,
            is_synthetic=True,
            metadata_json={
                "related_disciplines": ["computing"],
                "reviewed": True,
                "analysis_permissions": permissions,
            },
        )

    skills, occupations, relationships = {}, {}, {}
    for item in data["skills"]:
        row = Skill(
            taxonomy=data["taxonomy"],
            label=item["label"],
            **referenced(f"skill:{item['key']}", f"Fictional competency: {item['label']}."),
        )
        session.add(row)
        session.flush()
        skills[item["key"]] = row
    for item in data["occupations"]:
        key = item["key"]
        row = Occupation(
            taxonomy=data["taxonomy"],
            label=item["label"],
            description=f"Fictional reviewed computing occupation {key} for tests only.",
            **referenced(f"occupation:{key}", f"Fictional computing occupation: {item['label']}."),
        )
        session.add(row)
        session.flush()
        occupations[key] = row
        for skill, relation in item["requirements"].items():
            link = OccupationSkill(
                occupation_id=row.id,
                skill_id=skills[skill].id,
                relationship=relation,
                **referenced(
                    f"relation:{key}:{skill}",
                    f"{item['label']} has the fictional {relation} requirement "
                    f"{skills[skill].label}.",
                ),
            )
            session.add(link)
            session.flush()
            relationships[(key, skill)] = link
    audit = Document(
        id=identity("audit-document"),
        programme_revision_id=revision.id,
        filename="synthetic-whole-programme-audit.json",
        document_kind=DocumentKind.SUPPORTING,
        format=DocumentFormat.JSON,
        content_sha256=hashlib.sha256(data["gap"]["quote"].encode()).hexdigest(),
        parser_version="synthetic-audit-1",
        uploaded_at=collected,
        is_synthetic=True,
        metadata_json={
            "content_reviewed": True,
            "gap_reviewed": True,
            "negative_skill_ids": [str(skills[data["gap"]["skill"]].id)],
            "analysis_permissions": permissions,
        },
    )
    session.add(audit)
    session.flush()
    audit_anchor = DocumentAnchor(
        id=identity("audit-anchor"),
        document_id=audit.id,
        locator="synthetic:all-course-audit",
        excerpt=data["gap"]["quote"],
        is_synthetic=True,
    )
    session.add(audit_anchor)
    session.flush()
    review = {
        "reviewed": True,
        "basis": data["review_basis"],
        "reviewer_reference": "synthetic-academic-reviewer",
        "reviewed_at": reviewed_at,
    }
    request = CareerRequest(
        revision_id=revision.id,
        mode="offline",
        as_of=now,
        mappings=[
            dict(
                occupation_id=row.id,
                taxonomy=row.taxonomy,
                external_id=row.external_id,
                discipline="computing",
                malaysia_applicability=data["malaysia_applicability"],
                requirements_complete=True,
                **review,
            )
            for row in occupations.values()
        ],
        assertions=[
            dict(
                skill_id=skills[item["skill"]].id,
                course_id=courses[item["course"]].id,
                anchor_id=anchors[item["course"]].id,
                quote=anchors[item["course"]].excerpt,
                support=item["support"],
                extent=item["extent"],
                **review,
            )
            for item in data["support"]
        ],
        gaps=[
            dict(
                skill_id=skills[data["gap"]["skill"]].id,
                anchor_id=audit_anchor.id,
                quote=audit_anchor.excerpt,
                covered_course_ids=[row.id for row in courses.values()],
                completeness_confirmed=True,
                **review,
            )
        ],
    )
    session.commit()
    return SimpleNamespace(
        data=data,
        now=now,
        request=request,
        programme=programme,
        revision=revision,
        institution=institution,
        courses=courses,
        anchors=anchors,
        documents=documents,
        skills=skills,
        occupations=occupations,
        relationships=relationships,
        references=references,
        version=version,
        dataset=dataset,
        taxonomy_source=taxonomy_source,
        university_source=university_source,
        audit=audit,
        audit_anchor=audit_anchor,
    )


def import_synthetic_taxonomy(database, fixture, tmp_path):
    """Exercise the existing reviewed source ETL, then map only its imported identities."""
    records = []

    def record(kind, key, data, quote):
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

    taxonomy = fixture.data["taxonomy"]
    for item in fixture.data["skills"]:
        record(
            "skill",
            f"skill:{item['key']}",
            {"taxonomy": taxonomy, "label": item["label"]},
            f"Fictional competency: {item['label']}.",
        )
    skill_names = {item["key"]: item["label"] for item in fixture.data["skills"]}
    for item in fixture.data["occupations"]:
        key = item["key"]
        record(
            "occupation",
            f"occupation:{key}",
            {
                "taxonomy": taxonomy,
                "label": item["label"],
                "description": f"Fictional computing occupation {key}.",
                "metadata_json": {"related_disciplines": ["computing"]},
            },
            f"Fictional computing occupation: {item['label']}.",
        )
        for skill, relation in item["requirements"].items():
            record(
                "occupation_skill",
                f"relation:{key}:{skill}",
                {
                    "occupation_external_id": f"occupation:{key}",
                    "skill_external_id": f"skill:{skill}",
                    "relationship": relation,
                },
                f"{item['label']} has fictional {relation} requirement {skill_names[skill]}.",
            )
    source_path = tmp_path / "synthetic-reviewed-career-records.json"
    source_path.write_text(json.dumps({"reviewed": True, "records": records}), encoding="utf-8")
    registry_path = tmp_path / "synthetic-registry.csv"
    registry_entry = dict.fromkeys(REGISTRY_COLUMNS, "")
    dataset_id = "SYNTHETIC-CAREER-PIPELINE"
    registry_entry.update(
        id=dataset_id,
        category="C",
        priority="P1",
        name="Explicitly fictional career requirements",
        publisher="Synthetic Fixture Generator",
        source_url="https://example.invalid/fictional-career",
        download_api_url="https://example.invalid/fictional-career.json",
        format="JSON",
        evidence_class="synthetic_demo",
        verification_status="Verified",
        verified_on=fixture.now.date().isoformat(),
        latest_verified_publication_date=(fixture.now - timedelta(days=2)).date().isoformat(),
        licence="Entirely synthetic fixture",
        rights_status="Synthetic fixture reuse permitted",
        acquired_into_backend="No",
    )
    with registry_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTRY_COLUMNS)
        writer.writeheader()
        writer.writerow(registry_entry)
    policy_path = tmp_path / "synthetic-acquisition.json"
    policy_path.write_text(
        json.dumps(
            {
                dataset_id: {
                    "adapter": "reviewed_json",
                    "format": "json",
                    "reuse_reviewed": True,
                    "instructions": "Fictional university and taxonomy test records only.",
                }
            }
        ),
        encoding="utf-8",
    )
    options = dict(
        registry_path=registry_path,
        policy_path=policy_path,
        dataset_ids=[dataset_id],
        local_path=source_path,
        retrieved_at=fixture.now - timedelta(days=1),
        is_synthetic=True,
    )
    report = run_ingestion(database, **options)[0]
    assert report["status"] == "SUCCEEDED", report
    assert report["records_imported"] == len(records)
    repeated = run_ingestion(database, **options)[0]
    assert repeated["status"] == "UNCHANGED" and repeated["records_imported"] == 0
    with database.session_factory() as session:
        dataset = session.scalar(select(Dataset).where(Dataset.registry_key == dataset_id))
        imported = session.scalar(
            select(DatasetVersion).where(DatasetVersion.dataset_id == dataset.id)
        )
        new_skills = {
            row.external_id.removeprefix("skill:"): row
            for row in session.scalars(select(Skill).where(Skill.version_id == imported.id))
        }
        new_occupations = {
            row.external_id.removeprefix("occupation:"): row
            for row in session.scalars(
                select(Occupation).where(Occupation.version_id == imported.id)
            )
        }
        old_skill_names = {row.id: key for key, row in fixture.skills.items()}
        old_occupation_names = {row.id: key for key, row in fixture.occupations.items()}
        request = fixture.request.model_copy(deep=True)
        for mapping in request.mappings:
            row = new_occupations[old_occupation_names[mapping.occupation_id]]
            mapping.occupation_id, mapping.external_id, mapping.taxonomy = (
                row.id,
                row.external_id,
                row.taxonomy,
            )
        for assertion in request.assertions:
            assertion.skill_id = new_skills[old_skill_names[assertion.skill_id]].id
        request.gaps[0].skill_id = new_skills["security"].id
        audit = session.get(Document, fixture.audit.id)
        audit.metadata_json = {
            **audit.metadata_json,
            "negative_skill_ids": [str(new_skills["security"].id)],
        }
        session.commit()
        fixture.skills, fixture.occupations, fixture.version = new_skills, new_occupations, imported
        fixture.request = request
    return report
