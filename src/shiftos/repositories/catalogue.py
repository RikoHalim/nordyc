import hashlib
import json
from urllib.parse import urlsplit, urlunsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from shiftos.core.enums import EvidenceClass
from shiftos.core.errors import DomainError
from shiftos.models import Institution, Programme, Source


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return urlunsplit(("https", host, parsed.path.rstrip("/") or "/", parsed.query, ""))


def lock_institution(session: Session, institution_id: UUID) -> Institution:
    institution = session.scalar(
        select(Institution).where(Institution.id == institution_id).with_for_update()
    )
    if institution is None:
        raise DomainError("NOT_FOUND", "Institution not found", 404)
    return institution


def find_programme(
    session: Session, institution: Institution, url: str, name: str
) -> Programme | None:
    key = digest(canonical_url(url))
    # Include manually created records without an ingestion key; refuse ambiguous matches.
    candidates = session.scalars(
        select(Programme).where(Programme.institution_id == institution.id)
    ).all()
    matches = [
        p
        for p in candidates
        if p.ingestion_key == key
        or (p.canonical_url and canonical_url(p.canonical_url) == canonical_url(url))
    ]
    if not matches:
        matches = [
            p
            for p in candidates
            if p.canonical_url is None and p.name.strip().casefold() == name.strip().casefold()
        ]
    if len(matches) > 1:
        raise DomainError(
            "CONFLICT", "Ambiguous programme identity; manual reconciliation required", 409
        )
    return matches[0] if matches else None


def source_version(
    session: Session,
    *,
    publisher: str,
    title: str,
    url: str,
    content_hash: str,
    retrieved_at,
    synthetic: bool,
    reviewed: bool,
    license_status: str,
) -> Source:
    evidence_class = (
        EvidenceClass.SYNTHETIC_DEMO
        if synthetic
        else (EvidenceClass.VERIFIED_UNIVERSITY_FACT if reviewed else EvidenceClass.INFERENCE)
    )
    identity = (
        f"shiftos:curriculum:v2:{canonical_url(url)}:"
        f"{content_hash}:{evidence_class}:{license_status}"
    )
    source_id = uuid5(NAMESPACE_URL, identity)
    source = session.get(Source, source_id)
    if source is None:
        source = Source(
            id=source_id,
            publisher=publisher,
            title=title,
            url=url,
            content_hash=content_hash,
            collected_at=retrieved_at,
            observed_at=retrieved_at,
            source_kind="curriculum_catalogue",
            evidence_class=evidence_class,
            license_status=license_status,
            is_synthetic=synthetic,
        )
        session.add(source)
        session.flush()
    return source
