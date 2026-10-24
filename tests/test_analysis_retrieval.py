"""Offline retrieval fixtures are fictional, including nonsynthetic-flag simulations."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import event

from shiftos.core.enums import DocumentFormat, DocumentKind, EvidenceClass
from shiftos.models import (
    AcademicStandard,
    AIImpactEvidence,
    Course,
    Dataset,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Institution,
    Occupation,
    Programme,
    ProgrammeRevision,
    Source,
)
from shiftos.services.analysis.retrieval import (
    discipline_for,
    freeze_packet,
    retrieve_evidence,
)
from shiftos.services.evidence.pipeline import run_ingestion


def make_programme(session, discipline="accounting", *, synthetic=True):
    institution = Institution(name="Fictional Analysis University", is_synthetic=synthetic)
    session.add(institution)
    session.flush()
    programme = Programme(
        institution_id=institution.id,
        name=f"Bachelor of Synthetic {discipline}",
        discipline_key=discipline,
        is_synthetic=synthetic,
    )
    session.add(programme)
    session.flush()
    revision = ProgrammeRevision(
        programme_id=programme.id, version_label="synthetic-1", is_synthetic=synthetic
    )
    session.add(revision)
    session.flush()
    programme.active_revision_id = revision.id
    name = {
        "accounting": "Financial Accounting",
        "computing": "Software Testing",
        "biotechnology": "Molecular Biotechnology",
    }.get(discipline, "Unlabelled Foundation")
    courses = [
        Course(
            programme_revision_id=revision.id,
            course_name=f"Synthetic {name}",
            year=year,
            is_synthetic=synthetic,
        )
        for year in (1, 2)
    ]
    session.add_all(courses)
    session.commit()
    return programme, revision, courses


def make_evidence(
    session,
    kind="standard",
    *,
    discipline="accounting",
    synthetic=True,
    published=None,
    retrieved=None,
    review="reviewed",
    metadata=None,
    source_class=None,
):
    now = datetime.now(UTC)
    published = published or (now.date() - timedelta(days=10)).isoformat()
    retrieved = retrieved or now - timedelta(days=1)
    source = Source(
        publisher="Synthetic Evidence Authority",
        title=f"Synthetic {discipline} reference",
        url="https://example.invalid/synthetic",
        is_synthetic=synthetic,
        evidence_class=EvidenceClass.SYNTHETIC_DEMO
        if synthetic
        else source_class
        or (
            EvidenceClass.PUBLISHED_STANDARD
            if kind == "standard"
            else EvidenceClass.DATED_AI_CAPABILITY
            if kind == "ai"
            else EvidenceClass.OCCUPATION_REQUIREMENT
        ),
        collected_at=retrieved,
    )
    dataset = Dataset(
        registry_key=f"SYNTHETIC-{uuid4()}", name="Synthetic dataset", category="test"
    )
    session.add_all([source, dataset])
    session.flush()
    version = DatasetVersion(
        dataset_id=dataset.id,
        source_id=source.id,
        content_sha256=hashlib.sha256(str(uuid4()).encode()).hexdigest(),
        parser_version="synthetic-test",
        retrieved_at=retrieved,
        publication_date=published,
        artifact_url=source.url,
        is_synthetic=synthetic,
        metadata_json={},
    )
    session.add(version)
    session.flush()
    reference = EvidenceReference(
        version_id=version.id,
        locator="Synthetic paragraph 1",
        excerpt=(
            f"Synthetic {discipline} evidence describes a documented benchmark for source review."
        ),
        review_status=review,
        is_synthetic=synthetic,
    )
    session.add(reference)
    session.flush()
    kwargs = dict(
        version_id=version.id,
        evidence_id=reference.id,
        external_id=str(uuid4()),
        metadata_json=metadata or {},
        is_synthetic=synthetic,
    )
    if kind == "standard":
        row = AcademicStandard(
            discipline=discipline,
            title="Synthetic bachelor benchmark",
            statement=f"Synthetic {discipline} programme benchmark",
            **kwargs,
        )
    elif kind == "occupation":
        row = Occupation(
            taxonomy="Synthetic taxonomy", label=f"Synthetic {discipline} professional", **kwargs
        )
    else:
        row = AIImpactEvidence(
            occupation_label=f"Synthetic {discipline} professional",
            statement=f"Synthetic {discipline} AI observation",
            task=f"Synthetic {discipline} professional task",
            capability="Synthetic assisted task capability",
            impact_type="observed_practice",
            limitations="Synthetic task context only",
            study_period="Synthetic study period",
            **kwargs,
        )
    session.add(row)
    session.commit()
    return row, version, reference, source, dataset


@pytest.mark.parametrize("discipline", ["accounting", "computing", "biotechnology"])
def test_multidisciplinary_retrieval_preserves_every_course_and_exact_benchmark(
    session, discipline
):
    _, revision, courses = make_programme(session, discipline)
    row, version, reference, source, _ = make_evidence(
        session, discipline=discipline, metadata={"mqf_level": 6}
    )
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert packet.discipline == discipline
    assert {course.id for course in packet.courses} == {course.id for course in courses}
    assert len(packet.references) == 1
    item = packet.references[0]
    assert item.record_id == row.id and item.version_id == version.id
    assert item.evidence_reference_id == reference.id and item.source_id == source.id
    assert all(
        course.needs_syllabus_confirmation and not course.is_verified for course in packet.courses
    )
    assert all(item.id in course.reference_ids for course in packet.courses)
    assert packet.manifest_hash == freeze_packet(packet.model_copy(deep=True)).manifest_hash


def test_unknown_discipline_has_no_software_default_and_no_unrelated_benchmark(session):
    _, revision, _ = make_programme(session, "unknown arts")
    make_evidence(session, discipline="computing", metadata={"mqf_level": 6})
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert packet.discipline == "unknown"
    assert "unknown_discipline" in packet.gaps
    assert not packet.references


def test_irrelevant_evidence_does_not_change_frozen_accounting_manifest(session):
    _, revision, _ = make_programme(session)
    make_evidence(session, metadata={"mqf_level": 6})
    cutoff = datetime.now(UTC)
    before = retrieve_evidence(session, revision.id, cutoff)
    make_evidence(session, discipline="biotechnology", metadata={"mqf_level": 6})
    after = retrieve_evidence(session, revision.id, cutoff)
    assert before.manifest_hash == after.manifest_hash


def test_real_rights_are_explicit_unknown_denies_and_internal_only_text_never_leaks(session):
    _, revision, _ = make_programme(session, synthetic=False)
    _, _, _, _, dataset = make_evidence(session, synthetic=False, metadata={"mqf_level": 6})
    default = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert not default.references[0].internal_eligible
    policy = {
        dataset.registry_key: {
            "internal_analysis_allowed": True,
            "external_model_allowed": False,
            "excerpt_output_allowed": False,
            "basis": "Explicit internal research only",
        }
    }
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC), permitted_sources=policy)
    assert packet.references[0].internal_eligible
    assert not packet.references[0].model_eligible
    assert packet.references[0].excerpt == ""
    assert packet.references[0].facts == {}
    assert "rights_review_required" in packet.gaps


def test_explicit_record_deny_overrides_supplied_source_permission(session):
    _, revision, _ = make_programme(session)
    _, _, _, _, dataset = make_evidence(
        session,
        metadata={
            "mqf_level": 6,
            "analysis_permissions": {
                "external_model_allowed": False,
                "basis": "Record-specific denial",
            },
        },
    )
    policy = {
        dataset.registry_key: {
            "internal_analysis_allowed": True,
            "external_model_allowed": True,
            "excerpt_output_allowed": True,
            "basis": "Synthetic broad permission",
        }
    }
    item = retrieve_evidence(
        session, revision.id, datetime.now(UTC), permitted_sources=policy
    ).references[0]
    assert not item.model_eligible and not item.excerpt


@pytest.mark.parametrize("scope", ["version", "reference"])
def test_version_or_evidence_pointer_deny_overrides_source_policy(session, scope):
    _, revision, _ = make_programme(session)
    _, version, reference, _, _ = make_evidence(session, metadata={"mqf_level": 6})
    target = version if scope == "version" else reference
    target.metadata_json = {
        "analysis_permissions": {
            "internal_analysis_allowed": False,
            "basis": "Synthetic withdrawal for this evidence pointer",
        }
    }
    session.commit()
    item = retrieve_evidence(session, revision.id, datetime.now(UTC)).references[0]
    assert not item.internal_eligible and not item.model_eligible
    assert not item.excerpt and item.facts == {}


@pytest.mark.parametrize("late", ["retrieval", "publication"])
def test_historical_cutoff_excludes_later_known_or_published_evidence(session, late):
    _, revision, _ = make_programme(session)
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=100)
    make_evidence(
        session,
        metadata={"mqf_level": 6},
        retrieved=now - timedelta(days=1 if late == "retrieval" else 200),
        published=(now.date() - timedelta(days=200 if late == "retrieval" else 1)).isoformat(),
    )
    assert not retrieve_evidence(session, revision.id, cutoff).references


def test_old_ai_experiment_retains_historical_context_and_no_identity_claim(session):
    _, revision, _ = make_programme(session)
    make_evidence(session, kind="ai", published="2020-01-01")
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert packet.references[0].historical_context_only
    assert not packet.references[0].identity_reviewed
    assert "currentness_review_required" in packet.gaps


def test_rejected_reference_and_wrong_qualification_are_ineligible(session):
    _, revision, _ = make_programme(session)
    make_evidence(session, review="rejected", metadata={"mqf_level": 6})
    make_evidence(session, metadata={"mqf_level": 8})
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert not any(item.model_eligible or item.internal_eligible for item in packet.references)


@pytest.mark.parametrize("candidate_location", ["record", "reference"])
def test_raw_pdf_page_candidates_do_not_become_normalized_claims(session, candidate_location):
    _, revision, _ = make_programme(session)
    row, _, reference, _, _ = make_evidence(
        session, discipline="accounting", metadata={"mqf_level": 6}
    )
    target = row if candidate_location == "record" else reference
    target.metadata_json = {
        **target.metadata_json,
        "extraction_candidate": {"text": "Synthetic accounting pseudo claim"},
    }
    session.commit()
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert not any(item.model_eligible or item.internal_eligible for item in packet.references)
    assert not any(item.excerpt for item in packet.references)
    assert "missing_standards" in packet.gaps


def test_synthetic_and_real_evidence_lanes_do_not_mix(session):
    _, revision, _ = make_programme(session)
    make_evidence(session, synthetic=False, metadata={"mqf_level": 6})
    assert not retrieve_evidence(session, revision.id, datetime.now(UTC)).references


def test_retrieval_bound_is_explicit_and_no_course_is_lost(session, monkeypatch):
    import shiftos.services.analysis.retrieval as retrieval

    _, revision, courses = make_programme(session)
    for _ in range(3):
        make_evidence(session, metadata={"mqf_level": 6})
    monkeypatch.setattr(retrieval, "MAX_REFERENCES", 1)
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert packet.truncated and "retrieval_truncated" in packet.gaps
    assert len(packet.references) == 1
    assert len(packet.courses) == len(courses)


def test_inconsistent_synthetic_lineage_rejected(session):
    _, revision, courses = make_programme(session)
    courses[0].is_synthetic = False
    session.commit()
    with pytest.raises(ValueError, match="synthetic curriculum"):
        retrieve_evidence(session, revision.id, datetime.now(UTC))


def test_scope_helpers_never_translate_or_default_unknown_programmes():
    assert discipline_for("Bachelor of Marine Biotechnology") == "biotechnology"
    assert discipline_for("Bachelor of Software Engineering") == "computing"
    assert discipline_for("Bachelor of Chinese Studies") == "languages"
    assert discipline_for("Unspecified programme") == "unknown"


def test_other_discipline_standard_cannot_be_admitted_by_generic_lexical_overlap(session):
    _, revision, courses = make_programme(session, "accounting")
    courses[0].course_name = "Synthetic Financial Accounting Computing Applications"
    session.commit()
    make_evidence(session, discipline="computing", metadata={"mqf_level": 6})
    assert not retrieve_evidence(session, revision.id, datetime.now(UTC)).references


def test_unknown_programme_qualification_cannot_establish_bachelor_standard_applicability(session):
    programme, revision, _ = make_programme(session)
    programme.name = "Synthetic Accounting Programme"
    programme.level = None
    session.commit()
    make_evidence(session, metadata={"mqf_level": 6})
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    assert not packet.references[0].model_eligible
    assert "qualification_applicability_unconfirmed" in packet.references[0].exclusion_reasons


@pytest.mark.parametrize(
    "variant,expected",
    [
        ("reviewed", True),
        ("unreviewed", False),
        ("supporting_document", False),
        ("denied", False),
        ("anchor_wrong_lane", False),
        ("real_without_basis", False),
    ],
)
def test_syllabus_upgrade_requires_linked_reviewed_content_and_explicit_rights(
    session, variant, expected
):
    synthetic = variant != "real_without_basis"
    _, revision, courses = make_programme(session, synthetic=synthetic)
    _, _, _, source, _ = make_evidence(
        session, synthetic=synthetic, source_class=EvidenceClass.VERIFIED_UNIVERSITY_FACT
    )
    course = courses[0]
    course.source_id = source.id
    course.source_locator = "Synthetic course link"
    course.is_verified = not synthetic
    course.detailed_syllabus_available = True
    permission = {
        "internal_analysis_allowed": True,
        "external_model_allowed": variant != "denied",
        "excerpt_output_allowed": True,
    }
    document = Document(
        programme_revision_id=revision.id,
        course_id=course.id,
        filename="synthetic-syllabus.json",
        document_kind=DocumentKind.SUPPORTING
        if variant == "supporting_document"
        else DocumentKind.SYLLABUS,
        format=DocumentFormat.JSON,
        content_sha256="a" * 64,
        parser_version="synthetic-content-fixture",
        metadata_json={
            "content_reviewed": variant != "unreviewed",
            "analysis_permissions": permission,
        },
        uploaded_at=datetime.now(UTC) - timedelta(days=1),
        is_synthetic=synthetic,
    )
    session.add(document)
    session.flush()
    session.add(
        DocumentAnchor(
            document_id=document.id,
            locator="Synthetic syllabus paragraph 1",
            excerpt="Synthetic syllabus documents accounting assessments for review.",
            is_synthetic=False if variant == "anchor_wrong_lane" else synthetic,
        )
    )
    session.commit()
    packet = retrieve_evidence(session, revision.id, datetime.now(UTC))
    result = next(item for item in packet.courses if item.id == course.id)
    assert (result.evidence_level == "detailed_syllabus") is expected
    assert result.needs_syllabus_confirmation is not expected


def test_source_lineage_queries_are_bounded_per_family_not_per_record(database, session):
    _, revision, _ = make_programme(session)
    for _ in range(20):
        make_evidence(session, metadata={"mqf_level": 6, "related_disciplines": None})
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    session.expire_all()
    revision_id = revision.id
    event.listen(database.engine, "before_cursor_execute", capture)
    try:
        packet = retrieve_evidence(session, revision_id, datetime.now(UTC))
    finally:
        event.remove(database.engine, "before_cursor_execute", capture)
    assert len(packet.references) == 20
    assert len(statements) <= 15


def test_genuine_legacy_esco_pack_retrieves_exact_source_ids_and_context_limits(database):
    """Genuine ESCO subset plus a fictional programme; no live acquisition or mapping claim."""
    root = Path(__file__).resolve().parents[1]
    path = root / "data/reference_packs/esco-v1.0.3.subset.reviewed.json"
    pack = json.loads(path.read_text(encoding="utf-8"))
    report = run_ingestion(
        database,
        dataset_ids=["C-ESCO-V103"],
        registry_path=root / "data/dataset_registry.csv",
        policy_path=root / "data/evidence_acquisition.json",
        local_path=path,
        retrieved_at=datetime.fromisoformat(pack["metadata"]["original_retrieved_at"]),
    )[0]
    assert report["status"] == "SUCCEEDED" and report["records_imported"] == 87
    with database.session_factory() as session:
        _, revision, courses = make_programme(session, "engineering", synthetic=False)
        courses[0].course_name = "Fictional Irrigation Systems"
        courses[1].course_name = "Fictional Water Engineering"
        session.commit()
        policy = {
            "C-ESCO-V103": {
                "internal_analysis_allowed": True,
                "external_model_allowed": True,
                "excerpt_output_allowed": True,
                "basis": pack["metadata"]["rights_basis"],
            }
        }
        packet = retrieve_evidence(
            session, revision.id, datetime.now(UTC), permitted_sources=policy
        )
    assert {item.kind for item in packet.references} >= {"occupation", "skill", "occupation_skill"}
    occupation = next(item for item in packet.references if item.kind == "occupation")
    assert occupation.facts["external_id"] == (
        "http://data.europa.eu/esco/occupation/13331bd9-0599-47c0-9812-29650c218de3"
    )
    assert occupation.facts["label"] == "water engineering technician"
    assert occupation.facts["taxonomy"] == "ESCO:v1.0.3"
    assert occupation.language == "en"
    assert occupation.historical_context_only and not occupation.identity_reviewed
    assert not packet.is_synthetic and all(not item.is_synthetic for item in packet.references)
    assert all(course.needs_syllabus_confirmation for course in packet.courses)
