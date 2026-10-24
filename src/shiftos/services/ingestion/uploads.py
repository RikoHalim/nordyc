"""Private PDF uploads; extraction runs in the existing separate catalogue worker."""

import hashlib
import os
import stat
from uuid import UUID

from sqlalchemy import select

from shiftos.core.enums import ContentStatus, DocumentFormat, DocumentKind
from shiftos.core.errors import DomainError
from shiftos.db.base import utc_now
from shiftos.models import Course, Document, DocumentAnchor, Institution
from shiftos.schemas.ingestion import CatalogueResult, ProgrammeOutcome
from shiftos.services.academic import require_programme
from shiftos.services.ingestion.catalogue import (
    check_origin,
    coverage,
    import_programme,
    queue_job,
)
from shiftos.services.ingestion.pdf import (
    PDF_PARSER_VERSION,
    PdfCourseRegion,
    detect_brochure_regions,
    prepare_brochure_import,
)


def upload_path(settings, digest, institution_id=None):
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise DomainError("INVALID_UPLOAD", "Invalid stored document identity", 422)
    configured = settings.curriculum_upload_dir.absolute()
    if configured.is_symlink():
        raise DomainError("UPLOAD_STORAGE_ERROR", "Private upload storage is unsafe", 409)
    root = configured.resolve()
    if institution_id is not None:
        root = root / str(UUID(str(institution_id)))
        if root.is_symlink():
            raise DomainError("UPLOAD_STORAGE_ERROR", "Private upload storage is unsafe", 409)
    path = root / f"{digest}.pdf"
    if path.is_symlink():
        raise DomainError("UPLOAD_STORAGE_ERROR", "Private upload storage is unsafe", 409)
    return path


def _read_private_pdf(path):
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stored:
            info = os.fstat(stored.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 20_000_000:
                raise OSError("Unsafe upload object")
            return stored.read(20_000_001)
    except OSError:
        raise DomainError("UPLOAD_STORAGE_ERROR", "Private upload storage is unsafe", 409) from None


def enqueue_pdf_upload(session, programme_id, content, settings, *, source_url=None, regions=None):
    programme = require_programme(session, programme_id)
    institution = session.get(Institution, programme.institution_id)
    if not programme.canonical_url:
        raise DomainError("CONFLICT", "Select a programme with an official origin URL", 409)
    source_url = source_url or programme.canonical_url
    check_origin(institution, source_url)
    if not content.startswith(b"%PDF-") or not 0 < len(content) <= 20_000_000:
        raise DomainError("INVALID_PDF", "Upload a PDF document up to 20 MB", 422)
    checksum = hashlib.sha256(content).hexdigest()
    scoped = getattr(settings, "api_access_mode", "legacy") == "scoped"
    path = upload_path(settings, checksum, institution.id if scoped else None)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        path.parent.chmod(0o700)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
    except FileExistsError:
        if hashlib.sha256(_read_private_pdf(path)).hexdigest() != checksum:
            raise DomainError(
                "UPLOAD_STORAGE_ERROR", "Stored document failed integrity check", 409
            ) from None
    return queue_job(
        session,
        institution.id,
        "CURRICULUM_PDF_UPLOAD",
        {
            "programme_id": str(programme_id),
            "content_sha256": checksum,
            "source_url": source_url,
            "source_url_is_programme_pointer": source_url == programme.canonical_url,
            "uploaded_at": utc_now().isoformat(),
            "storage_scope": "institution" if scoped else "legacy",
            "regions": [r.model_dump() for r in regions] if regions else None,
        },
        None,
    )


def process_pdf_upload(database, job, settings):
    # Import locally to avoid a module cycle: worker dispatches this function.
    from shiftos.services.ingestion.worker import lock_running_job

    payload = job.payload_json
    scope = payload.get("storage_scope", "legacy")
    if scope not in {"institution", "legacy"}:
        raise DomainError("UPLOAD_STORAGE_ERROR", "Invalid private storage scope", 409)
    path = upload_path(
        settings,
        payload["content_sha256"],
        job.institution_id if scope == "institution" else None,
    )
    if not path.exists() or path.stat().st_size > 20_000_000:
        raise DomainError("UPLOAD_UNAVAILABLE", "Stored upload unavailable; upload again", 422)
    content = _read_private_pdf(path)
    if hashlib.sha256(content).hexdigest() != payload["content_sha256"]:
        raise DomainError("UPLOAD_CHECKSUM_MISMATCH", "Stored upload integrity check failed", 422)
    from datetime import datetime

    uploaded_at = datetime.fromisoformat(payload["uploaded_at"])
    programme_id = UUID(payload["programme_id"])
    with database.session_factory() as session:
        programme = require_programme(session, programme_id)
        if programme.institution_id != job.institution_id:
            raise DomainError("CONFLICT", "Uploaded programme belongs to another institution", 409)
        name, canonical_url = programme.name, programme.canonical_url
    if scope == "institution" or getattr(settings, "api_access_mode", "legacy") == "scoped":
        from shiftos.services.ingestion.pdf_process import prepare_in_process

        data, raw_regions = prepare_in_process(
            content,
            regions=payload.get("regions"),
            metadata={
                "programme_name": name,
                "canonical_url": canonical_url,
                "source_url": payload["source_url"],
                "retrieved_at": uploaded_at.isoformat(),
                "is_synthetic": job.is_synthetic,
                "license_status": "private_uploaded_document_reuse_unconfirmed",
            },
        )
        regions = [PdfCourseRegion.model_validate(row) for row in raw_regions]
    else:
        # Preserve existing local queued uploads; deployed scoped uploads use isolation above.
        regions = (
            [PdfCourseRegion.model_validate(r) for r in payload["regions"]]
            if payload.get("regions")
            else detect_brochure_regions(content)
        )
        data = prepare_brochure_import(
            content,
            programme_name=name,
            canonical_url=canonical_url,
            source_url=payload["source_url"],
            retrieved_at=uploaded_at,
            regions=regions,
            is_synthetic=job.is_synthetic,
            license_status="private_uploaded_document_reuse_unconfirmed",
        )
    manifest = data.programmes[0]
    manifest.notes.extend(
        [
            "Upload time is collection time, not publication date; effective cohort unknown",
            "Private uploaded original retained by SHA256; no live source acquisition asserted",
        ]
    )
    if payload.get("source_url_is_programme_pointer"):
        manifest.notes.append(
            "Source URL is the programme pointer; exact origin is the uploaded PDF"
        )
    with database.session_factory() as session:
        lock_running_job(session, job.id)
        result = import_programme(
            session,
            job.institution_id,
            manifest,
            synthetic=job.is_synthetic,
            parser_version=PDF_PARSER_VERSION + ":upload-1",
            acquisition_mode="uploaded_pdf_candidate",
            target_id=programme_id,
            commit=False,
        )
        revision_id = UUID(result["revision_id"])
        document = session.scalar(
            select(Document).where(
                Document.programme_revision_id == revision_id,
                Document.format == DocumentFormat.PDF,
                Document.content_sha256 == payload["content_sha256"],
            )
        )
        if document is None:
            document = Document(
                programme_revision_id=revision_id,
                filename="uploaded-curriculum.pdf",
                document_kind=DocumentKind.PROGRAMME_STRUCTURE,
                format=DocumentFormat.PDF,
                content_sha256=payload["content_sha256"],
                parser_version=PDF_PARSER_VERSION,
                storage_path=str(path),
                content_status=ContentStatus.UPLOADED,
                is_synthetic=job.is_synthetic,
                metadata_json={
                    "uploaded_at": payload["uploaded_at"],
                    "source_url": payload["source_url"],
                    "reviewed": False,
                    "regions": [r.model_dump() for r in regions],
                    "publication_date": None,
                },
            )
            session.add(document)
            session.flush()
            courses = session.scalars(
                select(Course).where(Course.programme_revision_id == revision_id)
            ).all()
            for course in courses:
                candidate = next(
                    c for c in manifest.courses if c.source_locator == course.source_locator
                )
                anchor = DocumentAnchor(
                    document_id=document.id,
                    locator=course.source_locator,
                    excerpt=candidate.source_excerpt,
                    page_number=int(course.source_locator.split(";")[0].split()[-1]),
                    is_synthetic=job.is_synthetic,
                )
                session.add(anchor)
                session.flush()
                course.inventory_source_anchor_id = anchor.id
        stats = coverage(session, programme_id, revision_id)
        output = CatalogueResult(
            provider="uploaded_pdf",
            discovered_programmes=1,
            entries=[
                ProgrammeOutcome(
                    **result,
                    source_url=str(manifest.source_url),
                    verified_title_count=stats.verified_title_count,
                )
            ],
            limitations=[
                "PDF candidates require review; no syllabus or teaching content inferred",
                "Unknown layouts/scans require explicit course regions or manual JSON",
            ],
        )
        session.commit()
    return output
