"""Controlled brochure extraction into the existing reviewed-file import contract.

An operator selects course-list rectangles, one per column/block, using PDF
coordinates (points from the top-left). Selection is deliberate: reading a whole
multi-column brochure as one text stream can attach courses to the wrong year.
Output is always an unreviewed candidate inventory, never a syllabus assertion.
This module performs no downloading, OCR, or automatic interpretation of prose.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from io import BytesIO

import pdfplumber
from pydantic import BaseModel, ConfigDict, Field, model_validator

from shiftos.core.enums import CourseType
from shiftos.schemas.ingestion import CatalogueImport, ImportCourse, ProgrammeManifest
from shiftos.services.ingestion.parsers import CurriculumParseError

PDF_PARSER_VERSION = "brochure-regions-1"
_YEAR = re.compile(r"^years?\s+(\d+(?:\s*[/,&–-]\s*\d+)*)\s*:?$", re.I)
_SEMESTER = re.compile(r"^sem(?:ester)?\.?\s+(\d+)\s*:?$", re.I)
_ELECTIVE = re.compile(r"^(?:(?:major|open|language|shared)\s+)*electives?\b", re.I)
_CORE = re.compile(r"^(?:(?:major|common)\s+)?(?:core|compulsory)\s+courses?\s*:?$", re.I)
_BULLET = re.compile(r"^(?:[•●○▪◦·*\-]|[yl])\s+")
_STOP = re.compile(
    r"^(?:entry requirements?|career opportunities|programme highlights|contact(?: us)?)\s*:?$",
    re.I,
)


class PdfCourseRegion(BaseModel):
    """A manually selected course block, isolated from neighbouring columns."""

    model_config = ConfigDict(extra="forbid")
    page: int = Field(gt=0, le=50, strict=True)
    x0: float = Field(ge=0, allow_inf_nan=False)
    top: float = Field(ge=0, allow_inf_nan=False)
    x1: float = Field(gt=0, allow_inf_nan=False)
    bottom: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def positive_area(self) -> PdfCourseRegion:
        if self.x1 <= self.x0 or self.bottom <= self.top:
            raise ValueError("PDF region must have positive width and height")
        return self


def _label_number(label: str) -> int | None:
    return int(label) if label.isdigit() and 0 < int(label) <= 100 else None


def _region_courses(page, region: PdfCourseRegion) -> list[ImportCourse]:
    bbox = (region.x0, region.top, region.x1, region.bottom)
    if region.x1 > page.width or region.bottom > page.height:
        raise CurriculumParseError("pdf_region_out_of_bounds", "Region exceeds its PDF page")
    lines = page.crop(bbox).extract_text_lines(layout=False, strip=True, return_chars=True)
    courses: list[ImportCourse] = []
    year = None
    raw_year = None
    semester = None
    raw_semester = None
    course_type = CourseType.UNKNOWN
    elective_group = None
    active = False
    pending: dict | None = None

    def finish() -> None:
        nonlocal pending
        if pending is None:
            return
        name = " ".join(pending["parts"])
        if len(name) > 255:
            raise CurriculumParseError(
                "course_title_too_long", "PDF candidate exceeds the course title limit"
            )
        bounds = pending["bbox"]
        notes = ["title_only", "needs_syllabus_confirmation", "pdf_candidate_requires_review"]
        if len(pending["parts"]) > 1:
            notes.append("pdf_wrapped_title_join_requires_confirmation")
        if pending["legacy_bullet"]:
            notes.append("pdf_legacy_bullet_glyph_requires_confirmation")
        if raw_year and year is None:
            notes.append("ambiguous_year_label_requires_confirmation")
        if re.search(r"\b[IVX]+\s*(?:&|,|and)\s*[IVX]+\b", name):
            notes.append("composite_label_not_split")
        courses.append(
            ImportCourse(
                course_name=name,
                year=year,
                raw_year_label=raw_year,
                semester=semester,
                raw_semester_label=raw_semester,
                course_type=course_type,
                elective_group=elective_group,
                source_locator=(
                    f"PDF page {region.page}; bbox "
                    + ",".join(f"{value:.2f}" for value in bounds)
                    + " (points from top-left)"
                ),
                source_excerpt="\n".join(pending["excerpts"]),
                review_notes=notes,
            )
        )
        pending = None

    for line in lines:
        text = " ".join(line["text"].split())
        if not text:
            continue
        year_match = _YEAR.fullmatch(text)
        semester_match = _SEMESTER.fullmatch(text)
        if year_match or semester_match or _ELECTIVE.match(text) or _CORE.fullmatch(text):
            finish()
            active = True
            if year_match:
                year = _label_number(year_match[1])
                raw_year = text
                semester = raw_semester = None
                course_type = CourseType.UNKNOWN
                elective_group = None
            elif semester_match:
                semester = _label_number(semester_match[1])
                raw_semester = text
            elif _ELECTIVE.match(text):
                course_type = CourseType.ELECTIVE
                elective_group = text
                # A pool shown near Year 3 is not proof of each elective's year.
                year = raw_year = semester = raw_semester = None
            else:
                course_type = CourseType.COMPULSORY
                elective_group = None
            continue
        if _STOP.fullmatch(text):
            finish()
            active = False
            continue
        bullet = _BULLET.match(text)
        if bullet and active:
            finish()
            name = text[bullet.end() :].strip()
            if not name:
                continue
            chars = line.get("chars", [])
            title_x = next(
                (char["x0"] for char in chars if char["x0"] > line["x0"] + 3),
                line["x0"] + 8,
            )
            pending = {
                "parts": [name],
                "excerpts": [text],
                "bbox": [line["x0"], line["top"], line["x1"], line["bottom"]],
                "title_x": title_x,
                "height": line["bottom"] - line["top"],
                "legacy_bullet": text[0] in "yl",
            }
        elif pending:
            gap = line["top"] - pending["bbox"][3]
            if 0 <= gap <= pending["height"] * 0.9 and abs(line["x0"] - pending["title_x"]) <= 6:
                pending["parts"].append(text)
                pending["excerpts"].append(text)
                pending["bbox"][2] = max(pending["bbox"][2], line["x1"])
                pending["bbox"][3] = line["bottom"]
            else:
                finish()
    finish()
    return courses


def prepare_brochure_import(
    content: bytes,
    *,
    programme_name: str,
    canonical_url: str,
    source_url: str,
    retrieved_at: datetime,
    regions: list[PdfCourseRegion],
    is_synthetic: bool = False,
    license_status: str = "rights_unconfirmed",
) -> CatalogueImport:
    """Prepare candidates for review and existing ``import-curriculum`` ingestion.

    Regions must include the explicit year/elective heading and complete bullets.
    They must not overlap. Context is reset per region: no guessed relationship
    across columns or pages. OCR/scanned brochures and non-bulleted layouts require
    the existing manual transcription fallback. Callers must acquire files lawfully.
    """
    if len(content) > 20_000_000:
        raise CurriculumParseError("pdf_too_large", "Brochure exceeds the 20 MB limit")
    if not content.startswith(b"%PDF-"):
        raise CurriculumParseError("invalid_pdf", "Source does not have a PDF signature")
    if not regions or len(regions) > 50:
        raise CurriculumParseError("pdf_regions_required", "Select between 1 and 50 course regions")
    for index, first in enumerate(regions):
        for second in regions[index + 1 :]:
            if (
                first.page == second.page
                and max(first.x0, second.x0) < min(first.x1, second.x1)
                and max(first.top, second.top) < min(first.bottom, second.bottom)
            ):
                raise CurriculumParseError("pdf_regions_overlap", "Course regions must not overlap")
    courses: list[ImportCourse] = []
    empty_regions: list[int] = []
    try:
        with pdfplumber.open(BytesIO(content)) as document:
            if len(document.pages) > 50:
                raise CurriculumParseError("pdf_page_limit", "Brochure exceeds the 50-page limit")
            for index, region in enumerate(regions, 1):
                if region.page > len(document.pages):
                    raise CurriculumParseError("pdf_page_missing", "Selected PDF page is absent")
                candidates = _region_courses(document.pages[region.page - 1], region)
                courses.extend(candidates)
                if not candidates:
                    empty_regions.append(index)
    except CurriculumParseError:
        raise
    except Exception as error:
        raise CurriculumParseError(
            "pdf_extraction_failed",
            "PDF is unreadable, encrypted or unsupported; transcribe manually",
        ) from error
    if not courses:
        raise CurriculumParseError(
            "pdf_course_candidates_empty",
            "No text bullets below explicit year/elective headings; inspect regions or transcribe",
        )
    return CatalogueImport(
        is_synthetic=is_synthetic,
        programmes=[
            ProgrammeManifest(
                name=programme_name,
                canonical_url=canonical_url,
                source_url=source_url,
                source_locator="PDF manually selected course-list regions",
                retrieved_at=retrieved_at,
                content_hash=hashlib.sha256(content).hexdigest(),
                license_status=license_status,
                reviewed=False,
                notes=[
                    f"parser_version:{PDF_PARSER_VERSION}",
                    "Manually selected PDF regions; inspect every candidate against the brochure",
                    "No year context carried across columns/pages; elective years stay unknown",
                    "Public course lists are not certified complete graduation curricula",
                ]
                + (
                    [
                        "Regions without labelled bullet candidates require manual review: "
                        + ",".join(map(str, empty_regions))
                    ]
                    if empty_regions
                    else []
                ),
                courses=courses,
            )
        ],
    )


def detect_brochure_regions(content: bytes) -> list[PdfCourseRegion]:
    """Conservative horizontal YEAR columns below an explicit MAIN COURSES heading.

    This is candidate layout detection, not verification. Other layouts must supply
    reviewed regions; page-wide text order never supplies course-year assignments.
    """
    if not content.startswith(b"%PDF-") or len(content) > 20_000_000:
        raise CurriculumParseError("invalid_pdf", "Provide a bounded PDF document")
    regions = []
    try:
        with pdfplumber.open(BytesIO(content)) as document:
            if len(document.pages) > 50:
                raise CurriculumParseError("pdf_page_limit", "Brochure exceeds the 50-page limit")
            for page in document.pages:
                words = page.extract_words()
                main = [
                    line
                    for line in page.extract_text_lines()
                    if re.fullmatch(r"MAIN\s+COURSES", line["text"], re.I)
                ]
                if len(main) != 1:
                    continue
                headings = []
                for index, word in enumerate(words[:-1]):
                    following = words[index + 1]
                    if (
                        word["text"].upper() == "YEAR"
                        and following["text"].isdigit()
                        and abs(word["top"] - following["top"]) < 3
                        and 0 <= following["x0"] - word["x1"] < 15
                        and word["top"] > main[0]["bottom"]
                        and word["top"] - main[0]["bottom"] < 100
                    ):
                        headings.append((word, int(following["text"])))
                if not 2 <= len(headings) <= 5:
                    continue
                headings.sort(key=lambda item: item[0]["x0"])
                if [number for _, number in headings] != list(range(1, len(headings) + 1)) or max(
                    w["top"] for w, _ in headings
                ) - min(w["top"] for w, _ in headings) > 4:
                    continue
                top = min(word["top"] for word, _ in headings) - 2
                stops = [
                    line["top"]
                    for line in page.extract_text_lines()
                    if line["top"] > top + 20
                    and (
                        _STOP.fullmatch(line["text"])
                        or line["text"].upper().startswith("XIAMEN UNIVERSITY MALAYSIA")
                    )
                ]
                bottom = min(stops, default=page.height - 10) - 2
                for index, (word, _) in enumerate(headings):
                    x0 = max(0, word["x0"] - 4)
                    x1 = (
                        headings[index + 1][0]["x0"] - 8
                        if index + 1 < len(headings)
                        else page.width - 5
                    )
                    if x1 - x0 < 70:
                        raise CurriculumParseError("pdf_layout_ambiguous", "Select course regions")
                    regions.append(
                        PdfCourseRegion(page=page.page_number, x0=x0, top=top, x1=x1, bottom=bottom)
                    )
    except CurriculumParseError:
        raise
    except Exception as exc:
        raise CurriculumParseError("pdf_extraction_failed", "PDF requires manual review") from exc
    if not regions:
        raise CurriculumParseError(
            "pdf_regions_required", "No supported labelled column layout; supply course regions"
        )
    return regions
