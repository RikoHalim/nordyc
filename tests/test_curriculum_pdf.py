"""Offline fictional brochures; no synthetic course is attributed to a university."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from shiftos.core.enums import CourseType
from shiftos.services.ingestion import worker
from shiftos.services.ingestion.parsers import CurriculumParseError
from shiftos.services.ingestion.pdf import PdfCourseRegion, prepare_brochure_import


def _synthetic_pdf(pages: list[list[tuple[int, int, str]]]) -> bytes:
    """Small real PDF structure, Helvetica text; x/y use top-left points.

    Hand-written fixture avoids introducing a PDF-authoring runtime dependency.
    Every string used in these fixtures is explicitly fictional.
    """
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_ids = []
    for lines in pages:
        page_id = len(objects) + 1
        stream_id = page_id + 1
        page_ids.append(page_id)
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>"
            ).encode()
        )
        stream = b"\n".join(
            f"BT /F1 10 Tf 1 0 0 1 {x} {792 - y} Tm ({text}) Tj ET".encode() for x, y, text in lines
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects[1] = (
        f"<< /Type /Pages /Count {len(pages)} /Kids ["
        + " ".join(f"{page_id} 0 R" for page_id in page_ids)
        + "] >>"
    ).encode()
    result = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(result)
    result += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    result += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return result


def _prepare(content: bytes, regions: list[PdfCourseRegion]):
    return prepare_brochure_import(
        content,
        programme_name="Bachelor of Synthetic Brochure Studies",
        canonical_url="https://www.example.invalid/courses/synthetic",
        source_url="https://www.example.invalid/brochure.synthetic.pdf",
        retrieved_at=datetime(2026, 10, 20, tzinfo=UTC),
        regions=regions,
        is_synthetic=True,
    )


def _region(**changes) -> PdfCourseRegion:
    return PdfCourseRegion.model_validate(
        {"page": 1, "x0": 40, "top": 40, "x1": 280, "bottom": 300, **changes}
    )


def test_multicolumn_courses_keep_their_explicit_year_and_region() -> None:
    content = _synthetic_pdf(
        [
            [
                (50, 60, "Year 1"),
                (320, 60, "Year 2"),
                (50, 80, "- Synthetic Accounting"),
                (320, 80, "- Synthetic Marine Science"),
                (50, 100, "- Synthetic History"),
                (320, 100, "- Synthetic Laboratory"),
                (50, 350, "ENTRY REQUIREMENTS"),
                (50, 370, "- Not a course"),
            ]
        ]
    )
    manifest = _prepare(content, [_region(), _region(x0=310, x1=580)]).programmes[0]
    assert [(course.course_name, course.year) for course in manifest.courses] == [
        ("Synthetic Accounting", 1),
        ("Synthetic History", 1),
        ("Synthetic Marine Science", 2),
        ("Synthetic Laboratory", 2),
    ]
    assert all("PDF page 1; bbox" in course.source_locator for course in manifest.courses)
    assert all(course.course_type == CourseType.UNKNOWN for course in manifest.courses)
    assert manifest.reviewed is False
    assert manifest.content_hash == hashlib.sha256(content).hexdigest()


def test_wrapped_bullet_is_one_reviewable_course_and_excerpt_keeps_both_lines() -> None:
    content = _synthetic_pdf(
        [[(50, 60, "Year 1"), (50, 80, "- Synthetic Methods and"), (58, 92, "Data Analysis")]]
    )
    course = _prepare(content, [_region()]).programmes[0].courses[0]
    assert course.course_name == "Synthetic Methods and Data Analysis"
    assert course.source_excerpt == "- Synthetic Methods and\nData Analysis"
    assert "pdf_wrapped_title_join_requires_confirmation" in course.review_notes


def test_elective_pool_does_not_inherit_nearby_year() -> None:
    content = _synthetic_pdf(
        [
            [
                (50, 60, "Year 3"),
                (50, 80, "- Synthetic Capstone"),
                (50, 110, "Major Elective"),
                (50, 130, "y Synthetic History"),
            ]
        ]
    )
    courses = _prepare(content, [_region()]).programmes[0].courses
    assert courses[0].year == 3
    assert courses[1].year is None
    assert courses[1].course_type == CourseType.ELECTIVE
    assert "pdf_legacy_bullet_glyph_requires_confirmation" in courses[1].review_notes


def test_year_context_is_not_carried_to_another_region_or_page() -> None:
    content = _synthetic_pdf(
        [
            [(50, 60, "Year 1"), (50, 80, "- Synthetic Foundation")],
            [(50, 60, "- Synthetic Unlabelled")],
        ]
    )
    programme = _prepare(content, [_region(), _region(page=2)]).programmes[0]
    courses = programme.courses
    assert len(courses) == 1
    assert courses[0].course_name == "Synthetic Foundation"
    assert "Regions without labelled bullet candidates require manual review: 2" in programme.notes


def test_ambiguous_year_and_explicit_semester_remain_separate() -> None:
    content = _synthetic_pdf(
        [[(50, 60, "Year 2/3"), (50, 80, "Semester 1"), (50, 100, "- Synthetic Placement")]]
    )
    course = _prepare(content, [_region()]).programmes[0].courses[0]
    assert course.year is None
    assert course.raw_year_label == "Year 2/3"
    assert course.semester == 1


@pytest.mark.parametrize("content", [b"not a PDF", b"%PDF-1.7 corrupt"])
def test_missing_or_corrupt_pdf_fails_visibly(content: bytes) -> None:
    with pytest.raises(CurriculumParseError) as error:
        _prepare(content, [_region()])
    assert error.value.code in {"invalid_pdf", "pdf_extraction_failed"}


@pytest.mark.parametrize(
    "lines",
    [
        [],
        [(50, 60, "Year 1"), (50, 80, "Synthetic nonbulleted line")],
        [(50, 60, "- Synthetic unlabelled bullet")],
    ],
)
def test_scanned_empty_and_unsupported_layouts_require_manual_transcription(lines) -> None:
    with pytest.raises(CurriculumParseError) as error:
        _prepare(_synthetic_pdf([lines]), [_region()])
    assert error.value.code == "pdf_course_candidates_empty"


@pytest.mark.parametrize(
    ("regions", "code"),
    [
        ([], "pdf_regions_required"),
        ([_region(), _region(x0=50)], "pdf_regions_overlap"),
        ([_region(page=2)], "pdf_page_missing"),
        ([_region(x1=700)], "pdf_region_out_of_bounds"),
    ],
)
def test_region_validation_protects_against_missing_pages_duplicates_and_bad_crops(regions, code):
    content = _synthetic_pdf([[(50, 60, "Year 1"), (50, 80, "- Synthetic Course")]])
    with pytest.raises(CurriculumParseError) as error:
        _prepare(content, regions)
    assert error.value.code == code


@pytest.mark.parametrize("changes", [{"page": 0}, {"x1": 30}, {"x0": float("nan")}])
def test_coordinate_contract_rejects_invalid_region(changes) -> None:
    with pytest.raises(ValidationError):
        _region(**changes)


def test_pdf_candidates_use_existing_queue_persistence_and_remain_unverified(
    client, database
) -> None:
    content = _synthetic_pdf([[(50, 60, "Year 1"), (50, 80, "- Synthetic Course")]])
    data = _prepare(content, [_region()])
    institution = client.post(
        "/api/v1/institutions",
        json={
            "name": "Fictional PDF University",
            "website_url": "https://www.example.invalid",
            "is_synthetic": True,
        },
    ).json()
    response = client.post(
        f"/api/v1/institutions/{institution['id']}/imports", json=data.model_dump(mode="json")
    )
    assert response.status_code == 202, response.text
    assert worker.run_once(database, client.app.state.settings) == UUID(response.json()["id"])
    result = client.get(f"/api/v1/catalogue/jobs/{response.json()['id']}").json()
    assert result["status"] == "SUCCEEDED", result
    programme_id = result["result"]["entries"][0]["programme_id"]
    course = client.get(f"/api/v1/programmes/{programme_id}/courses").json()["items"][0]
    assert course["year"] == 1
    assert course["is_verified"] is False
    assert course["source_locator"].startswith("PDF page 1")
    assert course["source_url"] == "https://www.example.invalid/brochure.synthetic.pdf"
