from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from pydantic import ValidationError

from shiftos.core.enums import CourseType
from shiftos.services.ingestion.parsers import (
    PARSER_VERSION,
    CurriculumParseError,
    ParsedCourse,
    XmumCurriculumParser,
    parse_directory,
    parse_programme,
)

FIXTURES = Path(__file__).parent / "fixtures" / "curriculum"
BASE = "https://www.example.invalid"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_directory_discovers_new_disciplines_and_deduplicates_urls() -> None:
    programmes = parse_directory(_fixture("directory.html"), f"{BASE}/undergraduate-programmes")
    assert len(programmes) == 4
    assert programmes[-1].name == "Bachelor of Synthetic New Discipline"
    assert programmes[0].canonical_url == f"{BASE}/courses/bachelor-synthetic-commerce"
    assert all("Foundation" not in item.name and "Master" not in item.name for item in programmes)
    assert all("untrusted.invalid" not in item.canonical_url for item in programmes)
    assert all("Navigation" not in item.name for item in programmes)


def test_directory_locators_refer_to_actual_official_link_nodes() -> None:
    html = _fixture("directory.html")
    soup = BeautifulSoup(html, "html.parser")
    for programme in parse_directory(html, f"{BASE}/undergraduate-programmes"):
        nodes = soup.select(programme.source_locator)
        assert len(nodes) == 1
        assert nodes[0].name == "a"


@pytest.mark.parametrize(
    "html", ["", "<h1>Maintenance</h1>", '<a href="/courses/master-test">Master</a>']
)
def test_empty_or_changed_directory_fails_visibly(html: str) -> None:
    with pytest.raises(CurriculumParseError, match="No explicit undergraduate") as error:
        parse_directory(html, f"{BASE}/undergraduate-programmes")
    assert error.value.code == "no_undergraduate_programmes"


def test_conflicting_directory_names_require_review() -> None:
    html = (
        '<a href="/courses/same">Bachelor of Synthetic One</a>'
        '<a href="/courses/same">Bachelor of Synthetic Two</a>'
    )
    with pytest.raises(CurriculumParseError) as error:
        parse_directory(html, BASE)
    assert error.value.code == "conflicting_programme_names"


def test_commerce_year_semester_explicit_classification_and_independent_choice_groups() -> None:
    programme = parse_programme(_fixture("commerce.html"), f"{BASE}/courses/synthetic-commerce")
    assert programme.name == "Bachelor of Synthetic Commerce"
    assert len(programme.courses) == 6
    introduction, wrapped, ethics, trade, services, practice = programme.courses
    assert introduction.year == 1
    assert introduction.semester is None
    assert introduction.course_type == CourseType.UNKNOWN
    assert wrapped.course_name == "Commerce and Community"
    assert ethics.year == 2
    assert ethics.semester == 1
    assert ethics.raw_year_label == "Year 2"
    assert ethics.raw_semester_label == "Semester 1"
    assert ethics.course_type == CourseType.COMPULSORY
    assert trade.course_type == services.course_type == practice.course_type == CourseType.ELECTIVE
    assert trade.elective_group == services.elective_group == "Major Elective (Choose any 2)"
    assert practice.elective_group == "Major Elective Group B (Choose 1)"
    assert all(course.course_code is None for course in programme.courses)
    assert all("needs_syllabus_confirmation" in course.review_notes for course in programme.courses)


@pytest.mark.parametrize("filename", ["commerce.html", "literature.html", "science.html"])
def test_only_main_courses_extracted_and_each_excerpt_has_an_exact_locator(filename: str) -> None:
    html = _fixture(filename)
    soup = BeautifulSoup(html, "html.parser")
    programme = parse_programme(html, f"{BASE}/courses/synthetic")
    assert all("Not a course" not in course.course_name for course in programme.courses)
    for course in programme.courses:
        nodes = soup.select(course.source_locator)
        assert len(nodes) in {1, 2}
        assert " ".join(node.get_text(" ", strip=True) for node in nodes) == course.source_excerpt
    assert "public_main_courses_not_certified_complete_curriculum" in programme.notes


def test_bilingual_bullets_are_preserved_as_one_appearance_and_quota_rows_are_not_courses() -> None:
    programme = parse_programme(_fixture("literature.html"), f"{BASE}/courses/synthetic-literature")
    assert len(programme.courses) == 4
    paired, inline, language, art = programme.courses
    assert paired.course_name == "Synthetic Literary History 虚构文学史"
    assert paired.year == inline.year == 1
    assert "bilingual_adjacent_bullets_paired_requires_confirmation" in paired.review_notes
    assert language.year is art.year is None
    assert language.semester is art.semester is None
    assert language.course_type == art.course_type == CourseType.ELECTIVE
    assert language.elective_group == "Major Elective Courses / 1. Synthetic Language"
    assert art.elective_group == "Major Elective Courses / 2. Synthetic Art"
    assert all("Choose any" not in course.course_name for course in programme.courses)


def test_composite_ambiguous_year_shared_pool_and_placeholders_remain_explicit() -> None:
    programme = parse_programme(_fixture("science.html"), f"{BASE}/courses/synthetic-science")
    laboratory, fieldwork, coastal, placeholder, truncated = programme.courses
    assert laboratory.course_name == "Synthetic Laboratory I & II"
    assert "composite_label_not_split" in laboratory.review_notes
    assert fieldwork.year is None
    assert fieldwork.raw_year_label == "Year 3/4"
    assert coastal.year is None
    assert coastal.course_type == CourseType.ELECTIVE
    assert placeholder.course_name == "Programming Elective II (1)"
    assert "unresolved_elective_placeholder" in placeholder.review_notes
    assert truncated.course_name == "Synthetic Truncated..."
    assert "possibly_truncated_title_requires_confirmation" in truncated.review_notes


def test_ambiguous_repeated_year_and_semester_labels_are_not_forced_to_one_number() -> None:
    html = (
        "<h1>Bachelor Synthetic</h1><h3>Main Courses</h3><h4>Year 2 &amp; Year 3</h4>"
        "<h5>Semester 1 / Semester 2</h5><ul><li>Synthetic Placement</li></ul>"
    )
    course = parse_programme(html, BASE).courses[0]
    assert course.year is None
    assert course.semester is None
    assert course.raw_year_label == "Year 2 & Year 3"
    assert course.raw_semester_label == "Semester 1 / Semester 2"


def test_explicit_year_columns_preserve_course_relationships() -> None:
    html = (
        "<h1>Bachelor Synthetic</h1><h3>Main Courses</h3><table>"
        "<tr><th>Year 1</th><th>Year 2</th></tr>"
        "<tr><td><ul><li>Synthetic Foundation</li></ul></td>"
        "<td><ul><li>Synthetic Specialisation</li></ul></td></tr></table>"
    )
    courses = parse_programme(html, BASE).courses
    assert [(course.course_name, course.year) for course in courses] == [
        ("Synthetic Foundation", 1),
        ("Synthetic Specialisation", 2),
    ]


def test_bold_course_label_does_not_reclassify_following_titles() -> None:
    html = (
        "<h1>Bachelor Synthetic</h1><h3>Main Courses</h3><h4>Year 1</h4>"
        "<ul><li><strong>Synthetic Elective Theory</strong></li>"
        "<li>Synthetic Introductory Methods</li></ul>"
    )
    courses = parse_programme(html, BASE).courses
    assert len(courses) == 2
    assert all(course.course_type == CourseType.UNKNOWN for course in courses)


def test_repeated_same_title_in_different_years_is_not_globally_deduplicated() -> None:
    html = (
        "<h1>Bachelor Synthetic</h1><h3>Main Courses</h3>"
        "<h4>Year 1</h4><ul><li>Synthetic Studio</li></ul>"
        "<h4>Year 2</h4><ul><li>Synthetic Studio</li></ul>"
    )
    courses = parse_programme(html, BASE).courses
    assert len(courses) == 2
    assert [course.year for course in courses] == [1, 2]
    assert courses[0].source_locator != courses[1].source_locator


@pytest.mark.parametrize(
    ("html", "code"),
    [
        ("<h3>Main Courses</h3><ul><li>Synthetic Course</li></ul>", "programme_title_missing"),
        ("<h1>Bachelor Synthetic</h1><ul><li>Career marketing</li></ul>", "main_courses_missing"),
        ("<h1>Bachelor Synthetic</h1><h3>Main Courses</h3><ul></ul>", "course_list_empty"),
        (
            "<h1>Bachelor Synthetic</h1><h3>Main Courses</h3><p>Temporarily unavailable</p>",
            "course_list_empty",
        ),
        (
            "<h1>Bachelor Synthetic</h1><h3>Main Courses</h3><ul><li>" + "x" * 256 + "</li></ul>",
            "course_title_too_long",
        ),
    ],
)
def test_unparseable_sources_fail_visibly(html: str, code: str) -> None:
    with pytest.raises(CurriculumParseError) as error:
        parse_programme(html, BASE)
    assert error.value.code == code


def test_parsed_contract_forbids_unrecognised_fields_and_oversized_names() -> None:
    data = {
        "course_name": "Synthetic Course",
        "source_locator": "li",
        "source_excerpt": "Synthetic Course",
    }
    with pytest.raises(ValidationError):
        ParsedCourse.model_validate({**data, "invented_syllabus": "Unsupported"})
    with pytest.raises(ValidationError):
        ParsedCourse.model_validate({**data, "course_name": "x" * 256})


def test_provider_interface_is_a_pure_wrapper_with_version() -> None:
    parser = XmumCurriculumParser()
    assert parser.version == PARSER_VERSION
    html = _fixture("commerce.html")
    assert parser.parse_programme(html, BASE) == parse_programme(html, BASE)
    directory = _fixture("directory.html")
    assert parser.parse_directory(directory, BASE) == parse_directory(directory, BASE)
