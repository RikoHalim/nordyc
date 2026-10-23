"""Transactional catalogue imports and durable queue operations.

No network access occurs in enqueue/import functions. The worker owns retrieval.
"""

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shiftos.core.enums import ContentStatus, DocumentFormat, DocumentKind, ExtractionStatus
from shiftos.core.errors import DomainError
from shiftos.models import (
    Course,
    Document,
    DocumentAnchor,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
)
from shiftos.repositories.catalogue import (
    canonical_url,
    digest,
    find_programme,
    lock_institution,
    source_version,
)
from shiftos.schemas.ingestion import CatalogueImport, CoverageRead, ProgrammeManifest
from shiftos.services.academic import require_programme


def check_origin(institution: Institution, url: str) -> None:
    source = urlsplit(url)
    base = urlsplit(institution.website_url or "")
    if (
        source.scheme != "https"
        or source.username is not None
        or source.password is not None
        or source.port not in (None, 443)
        or not base.hostname
        or (source.hostname or "").removeprefix("www.").lower()
        != base.hostname.removeprefix("www.").lower()
    ):
        raise DomainError(
            "VALIDATION_ERROR",
            "Catalogue source must be an HTTPS URL on the institution's official host",
            422,
        )


def validate_import(
    session: Session, institution_id: UUID, data: CatalogueImport, target_id: UUID | None = None
) -> Institution:
    institution = lock_institution(session, institution_id)
    if data.is_synthetic != institution.is_synthetic:
        raise DomainError(
            "CONFLICT", "Real and synthetic catalogue lanes must use separate institutions", 409
        )
    identities = [canonical_url(str(p.canonical_url)) for p in data.programmes]
    if len(set(identities)) != len(identities):
        raise DomainError("CONFLICT", "Manifest contains repeated programme identities", 409)
    for manifest in data.programmes:
        check_origin(institution, str(manifest.canonical_url))
        check_origin(institution, str(manifest.source_url))
    if target_id:
        target = require_programme(session, target_id)
        if target.institution_id != institution_id or len(data.programmes) != 1:
            raise DomainError("CONFLICT", "Programme import target does not match institution", 409)
        manifest = data.programmes[0]
        if target.canonical_url and canonical_url(target.canonical_url) != canonical_url(
            str(manifest.canonical_url)
        ):
            raise DomainError("CONFLICT", "Import URL does not match the target programme", 409)
        if not target.canonical_url and target.name.casefold() != manifest.name.casefold():
            raise DomainError("CONFLICT", "Import name does not match the target programme", 409)
    return institution


def queue_job(
    session: Session,
    institution_id: UUID,
    kind: str,
    payload: dict[str, Any],
    key: str | None,
    *,
    target_id: UUID | None = None,
) -> Job:
    institution = lock_institution(session, institution_id)
    if key:
        existing = session.scalar(
            select(Job).where(
                Job.institution_id == institution_id, Job.kind == kind, Job.idempotency_key == key
            )
        )
        if existing:
            if existing.payload_json != payload:
                raise DomainError(
                    "CONFLICT", "Idempotency key was already used for a different request", 409
                )
            return existing
    job = Job(
        institution_id=institution_id,
        programme_revision_id=None,
        kind=kind,
        payload_json={**payload, **({"target_id": str(target_id)} if target_id else {})},
        idempotency_key=key,
        is_synthetic=institution.is_synthetic,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def enqueue_import(
    session: Session, institution_id: UUID, data: CatalogueImport, target_id: UUID | None = None
) -> Job:
    validate_import(session, institution_id, data, target_id)
    payload = data.model_dump(mode="json", exclude={"idempotency_key"})
    if target_id:
        payload["target_id"] = str(target_id)
    return queue_job(session, institution_id, "CURRICULUM_IMPORT", payload, data.idempotency_key)


def ensure_programme(session: Session, institution: Institution, name: str, url: str) -> Programme:
    programme = find_programme(session, institution, url, name)
    if programme and programme.is_synthetic != institution.is_synthetic:
        raise DomainError("CONFLICT", "Programme identity has inconsistent synthetic lineage", 409)
    if programme is None:
        programme = Programme(
            institution_id=institution.id,
            name=name,
            canonical_url=url,
            ingestion_key=digest(canonical_url(url)),
            level="undergraduate",
            is_synthetic=institution.is_synthetic,
        )
        session.add(programme)
        session.flush()
    else:
        programme.ingestion_key = digest(canonical_url(url))
    return programme


def import_programme(
    session: Session,
    institution_id: UUID,
    manifest: ProgrammeManifest,
    *,
    synthetic: bool,
    parser_version: str,
    acquisition_mode: str,
    target_id: UUID | None = None,
) -> dict:
    institution = validate_import(
        session,
        institution_id,
        CatalogueImport(is_synthetic=synthetic, programmes=[manifest]),
        target_id,
    )
    programme = ensure_programme(session, institution, manifest.name, str(manifest.canonical_url))
    if target_id and programme.id != target_id:
        raise DomainError("CONFLICT", "Programme identity resolves to a different record", 409)
    unique_courses = []
    seen = set()
    duplicate_count = 0
    for course in manifest.courses:
        identity = digest(course.model_dump(mode="json"))
        if identity in seen:
            duplicate_count += 1
            continue
        seen.add(identity)
        unique_courses.append(course)
    facts = manifest.model_dump(mode="json", exclude={"retrieved_at", "courses"})
    facts["courses"] = [c.model_dump(mode="json") for c in unique_courses]
    fingerprint = digest(
        {
            "facts": facts,
            "parser_version": parser_version,
            "synthetic": synthetic,
            "acquisition_mode": acquisition_mode,
        }
    )
    existing = session.scalar(
        select(ProgrammeRevision).where(
            ProgrammeRevision.programme_id == programme.id,
            ProgrammeRevision.import_fingerprint == fingerprint,
        )
    )
    if existing:
        # Old manifests are never silently reactivated over a newer snapshot.
        session.commit()
        return {
            "programme_id": str(programme.id),
            "revision_id": str(existing.id),
            "name": existing.metadata_json.get("programme_name", manifest.name),
            "status": "unchanged",
            "course_count": len(unique_courses),
            "duplicate_rows_skipped": duplicate_count,
            "active": programme.active_revision_id == existing.id,
        }

    source = source_version(
        session,
        publisher=institution.name,
        title=manifest.name,
        url=str(manifest.source_url),
        content_hash=manifest.content_hash or digest(facts),
        retrieved_at=manifest.retrieved_at,
        synthetic=synthetic,
        reviewed=manifest.reviewed,
        license_status=manifest.license_status,
    )
    current = (
        session.get(ProgrammeRevision, programme.active_revision_id)
        if programme.active_revision_id
        else None
    )
    historical = bool(
        current
        and current.metadata_json.get("retrieved_at")
        and datetime.fromisoformat(current.metadata_json["retrieved_at"]) > manifest.retrieved_at
    )
    notes = list(manifest.notes)
    if duplicate_count:
        notes.append(
            f"Skipped {duplicate_count} identical source occurrences; "
            "distinct year/group/locator occurrences retained"
        )
    metadata = {
        "programme_name": manifest.name,
        "canonical_url": str(manifest.canonical_url),
        "source_id": str(source.id),
        "source_url": str(manifest.source_url),
        "source_locator": manifest.source_locator,
        "retrieved_at": manifest.retrieved_at.isoformat(),
        "parser_version": parser_version,
        "acquisition_mode": acquisition_mode,
        "reviewed_assertion": manifest.reviewed,
        "evidence_level": "title_only",
        "graduation_curriculum_complete": False,
        "notes": notes,
        "duplicate_rows_skipped": duplicate_count,
        "course_count": len(unique_courses),
        "effective_cohort": None,
    }
    revision = ProgrammeRevision(
        programme_id=programme.id,
        version_label="catalogue-" + fingerprint,
        import_fingerprint=fingerprint,
        metadata_json=metadata,
        is_synthetic=synthetic,
    )
    session.add(revision)
    session.flush()
    document = Document(
        programme_revision_id=revision.id,
        filename="catalogue-manifest.json",
        document_kind=DocumentKind.PROGRAMME_STRUCTURE,
        format=DocumentFormat.JSON,
        content_sha256=digest(facts),
        parser_version=parser_version,
        content_status=ContentStatus.UPLOADED,
        metadata_json={
            "is_synthetic": synthetic,
            "source_id": str(source.id),
            "kind": "extracted_title_inventory",
            "raw_source_not_stored": True,
        },
        is_synthetic=synthetic,
    )
    session.add(document)
    session.flush()
    semantic_occurrences: dict[str, int] = {}
    for item in unique_courses:
        semantic = digest(
            item.model_dump(
                mode="json", exclude={"source_locator", "source_excerpt", "review_notes"}
            )
        )
        semantic_occurrences[semantic] = semantic_occurrences.get(semantic, 0) + 1
    locator_titles: dict[str, set[str]] = {}
    for item in unique_courses:
        locator_titles.setdefault(item.source_locator, set()).add(
            digest(item.model_dump(mode="json"))
        )
    for index, item in enumerate(unique_courses):
        warnings = list(item.review_notes)
        if len(locator_titles[item.source_locator]) > 1:
            warnings.append(
                "Conflicting facts share a source locator; manual confirmation required"
            )
        semantic = digest(
            item.model_dump(
                mode="json", exclude={"source_locator", "source_excerpt", "review_notes"}
            )
        )
        if semantic_occurrences[semantic] > 1:
            warnings.append(
                "Possible duplicate title at distinct source locators; retained for review"
            )
        anchor = DocumentAnchor(
            document_id=document.id,
            locator=f"/courses/{index}/source_excerpt",
            section_label="Validated catalogue manifest; official locator on course",
            excerpt=item.source_excerpt,
            is_synthetic=synthetic,
        )
        session.add(anchor)
        session.flush()
        values = item.model_dump(exclude={"source_excerpt", "review_notes"})
        extraction_warnings = [
            note for note in warnings if note not in {"title_only", "needs_syllabus_confirmation"}
        ]
        course = Course(
            **values,
            programme_revision_id=revision.id,
            source_id=source.id,
            source_url=str(manifest.source_url),
            inventory_source_anchor_id=anchor.id,
            review_notes=warnings,
            is_synthetic=synthetic,
            is_verified=manifest.reviewed and not synthetic and not extraction_warnings,
            extraction_status=ExtractionStatus.NEEDS_REVIEW
            if extraction_warnings or not manifest.reviewed
            else ExtractionStatus.INVENTORY_ONLY,
            detailed_syllabus_available=False,
        )
        session.add(course)
    if not historical:
        programme.active_revision_id = revision.id
        programme.name = manifest.name
        programme.canonical_url = str(manifest.canonical_url)
        programme.source_id = source.id
        programme.source_locator = manifest.source_locator
    session.commit()
    return {
        "programme_id": str(programme.id),
        "revision_id": str(revision.id),
        "name": manifest.name,
        "status": "historical" if historical else "imported",
        "course_count": len(unique_courses),
        "duplicate_rows_skipped": duplicate_count,
        "active": not historical,
    }


def coverage(session: Session, programme_id: UUID, revision_id: UUID | None = None) -> CoverageRead:
    programme = require_programme(session, programme_id)
    selected = revision_id or programme.active_revision_id
    revision = session.get(ProgrammeRevision, selected) if selected else None
    if revision_id and (revision is None or revision.programme_id != programme_id):
        raise DomainError("NOT_FOUND", "Programme revision not found", 404)
    query = select(Course).where(Course.programme_revision_id == selected)
    courses = session.scalars(query).all()
    return CoverageRead(
        programme_id=programme_id,
        programme_revision_id=selected,
        course_count=len(courses),
        verified_title_count=sum(c.is_verified for c in courses),
        needs_review_count=sum(
            c.extraction_status == ExtractionStatus.NEEDS_REVIEW for c in courses
        ),
        title_only_count=sum(not c.detailed_syllabus_available for c in courses),
        is_synthetic=programme.is_synthetic,
        metadata=revision.metadata_json
        if revision
        else {"notes": ["No curriculum snapshot imported"]},
    )


def require_job(session: Session, job_id: UUID) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise DomainError("NOT_FOUND", "Catalogue job not found", 404)
    return job


def revision_list(session: Session, programme_id: UUID, limit: int, offset: int) -> dict:
    require_programme(session, programme_id)
    query = select(ProgrammeRevision).where(ProgrammeRevision.programme_id == programme_id)
    return {
        "items": session.scalars(
            query.order_by(ProgrammeRevision.created_at, ProgrammeRevision.id)
            .limit(limit)
            .offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }
