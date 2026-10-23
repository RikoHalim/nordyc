"""Pure, conservative curriculum parsing; fetching/access policy belongs to the provider.

These functions do not make network calls or claim that a marketing course list is
a complete degree curriculum. Unstated course metadata remains unknown.
"""

import re
from dataclasses import dataclass, replace
from typing import Annotated, Protocol
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, NavigableString, Tag
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from shiftos.core.enums import CourseType

PARSER_VERSION = "xmum-html-1"
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Locator = Annotated[str, StringConstraints(min_length=1, max_length=500)]


class CurriculumParseError(ValueError):
    """An unsupported/empty source must not appear to be a successful import."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ParserModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectoryProgramme(ParserModel):
    name: Name
    canonical_url: str
    source_locator: Locator


class ParsedCourse(ParserModel):
    course_name: Name
    course_code: str | None = None
    year: int | None = Field(default=None, gt=0)
    semester: int | None = Field(default=None, gt=0)
    course_type: CourseType = CourseType.UNKNOWN
    raw_year_label: str | None = None
    raw_semester_label: str | None = None
    elective_group: str | None = None
    source_locator: Locator
    source_excerpt: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    review_notes: list[str] = Field(default_factory=list)


class ParsedProgramme(ParserModel):
    name: Name
    canonical_url: str
    courses: list[ParsedCourse]
    notes: list[str] = Field(default_factory=list)


class CurriculumParser(Protocol):
    """Another institution can supply a parser without changing ingestion storage."""

    version: str

    def parse_directory(self, html: str, url: str) -> list[DirectoryProgramme]: ...

    def parse_programme(self, html: str, url: str) -> ParsedProgramme: ...


class XmumCurriculumParser:
    version = PARSER_VERSION

    def parse_directory(self, html: str, url: str) -> list[DirectoryProgramme]:
        return parse_directory(html, url)

    def parse_programme(self, html: str, url: str) -> ParsedProgramme:
        return parse_programme(html, url)


def _text(node: Tag) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _canonical_url(value: str) -> str:
    parts = urlsplit(urldefrag(value)[0])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def _locator(node: Tag) -> str:
    """A deterministic CSS locator that does not trust unsafe/duplicate source IDs."""
    parts: list[str] = []
    current = node
    while isinstance(current, Tag) and current.name != "[document]":
        source_id = current.get("id")
        if isinstance(source_id, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,120}", source_id):
            root = current
            while root.parent is not None:
                root = root.parent
            if len(root.find_all(id=source_id)) == 1:
                parts.append(f"#{source_id}")
                break
        parent = current.parent
        siblings = parent.find_all(current.name, recursive=False) if isinstance(parent, Tag) else []
        index = next((i for i, sibling in enumerate(siblings, 1) if sibling is current), 1)
        parts.append(f"{current.name}:nth-of-type({index})" if len(siblings) > 1 else current.name)
        current = parent
    path = " > ".join(reversed(parts))
    if len(path) > 500:
        raise CurriculumParseError(
            "source_structure_too_deep", "Source locator exceeds 500 characters"
        )
    return path


def _soup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    return soup


def parse_directory(html: str, url: str) -> list[DirectoryProgramme]:
    """Discover undergraduate links from the supplied directory, never a fixed major list."""
    soup = _soup(html)
    host = (urlsplit(url).hostname or "").removeprefix("www.").lower()
    programmes: dict[str, DirectoryProgramme] = {}
    for anchor in soup.find_all("a", href=True):
        target = _canonical_url(urljoin(url, str(anchor["href"])))
        parts = urlsplit(target)
        if parts.scheme not in {"http", "https"}:
            continue
        if (parts.hostname or "").removeprefix("www.").lower() != host:
            continue
        if not re.fullmatch(r"/(?:index\.php/)?courses/[^/]+", parts.path):
            continue
        name = _text(anchor)
        if not name:
            image = anchor.find("img", alt=True)
            name = str(image["alt"]).strip() if image else ""
        # Degree level must be explicit: do not promote foundation/postgraduate links.
        if not re.search(r"\bbachelor\b", name, re.I):
            continue
        entry = DirectoryProgramme(name=name, canonical_url=target, source_locator=_locator(anchor))
        previous = programmes.get(target)
        if previous is not None and previous.name != entry.name:
            # Some responsive cards repeat a shortened link followed by the full title.
            if previous.name in entry.name:
                programmes[target] = entry
            elif entry.name not in previous.name:
                raise CurriculumParseError(
                    "conflicting_programme_names", f"Conflicting directory labels: {target}"
                )
        else:
            programmes[target] = entry
    if not programmes:
        raise CurriculumParseError(
            "no_undergraduate_programmes", "No explicit undergraduate programme links found"
        )
    return list(programmes.values())


_YEAR = re.compile(r"\byears?\s*([1-9]\d*(?:\s*[/,&–-]\s*[1-9]\d*)*)", re.I)
_SEMESTER = re.compile(r"\bsem(?:ester)?s?\.?\s*([1-9]\d*(?:\s*[/,&–-]\s*[1-9]\d*)*)", re.I)
_STOP = re.compile(
    r"^(?:entry requirements?|career (?:opportunities|prospects|options)|admission requirements?"
    r"|fees?(?: structure)?|programme (?:overview|description|aims|objectives|outcomes)"
    r"|learning outcomes?|how to apply|contact(?: us)?|download(?: brochure)?|scholarships?)\s*:*$",
    re.I,
)
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "summary", "button"}


@dataclass
class _Context:
    year: int | None = None
    raw_year: str | None = None
    semester: int | None = None
    raw_semester: str | None = None
    course_type: CourseType = CourseType.UNKNOWN
    elective_group: str | None = None


def _number(match: re.Match | None) -> int | None:
    return int(match[1]) if match and match[1].isdigit() else None


def _label_context(text: str, context: _Context) -> _Context | None:
    """Only explicit headings set metadata; choose-counts are never semesters."""
    year = _YEAR.search(text)
    semester = _SEMESTER.search(text)
    is_elective = bool(re.search(r"\belectives?\b", text, re.I))
    is_compulsory = bool(
        re.search(r"\b(?:compulsory|mandatory|(?:common|major) core)\b", text, re.I)
    )
    if context.course_type == CourseType.ELECTIVE and re.match(r"^\d+\.\s+\S", text):
        root_group = (context.elective_group or "Electives").split(" / ", 1)[0]
        return replace(context, elective_group=f"{root_group} / {text}")
    if not (year or semester or is_elective or is_compulsory):
        return None
    result = replace(context)
    if year:
        multiple_year_labels = len(_YEAR.findall(text)) > 1
        result.year = None if multiple_year_labels else _number(year)
        result.raw_year = text if multiple_year_labels else year[0]
        result.semester = None
        result.raw_semester = None
        result.course_type = CourseType.UNKNOWN
        result.elective_group = None
    if semester:
        multiple_semester_labels = len(_SEMESTER.findall(text)) > 1
        result.semester = None if multiple_semester_labels else _number(semester)
        result.raw_semester = text if multiple_semester_labels else semester[0]
    if is_elective:
        result.course_type = CourseType.ELECTIVE
        result.elective_group = text
        # An explicit shared pool cannot inherit the last displayed academic year.
        if (
            re.search(r"\b(?:shared|pool|list of|all electives|available electives)\b", text, re.I)
            and not year
        ):
            result.year = None
            result.raw_year = None
            result.semester = None
            result.raw_semester = None
    elif is_compulsory:
        result.course_type = CourseType.COMPULSORY
        result.elective_group = None
    return result


def _main_course_nodes(soup: BeautifulSoup) -> list[Tag]:
    marker: Tag | None = None
    for candidate in soup.find_all(True):
        if _text(candidate).strip(": ").casefold() in {"main courses", "main course"}:
            # Prefer the semantic outer heading instead of its nested span/strong.
            marker = candidate
            break
    if marker is None:
        raise CurriculumParseError(
            "main_courses_missing", "The official Main Courses section was not found"
        )
    # The first following major content section is a hard stop, even in malformed HTML.
    nodes: list[Tag] = []
    marker_children = {id(child) for child in marker.descendants if isinstance(child, Tag)}
    # Live XMUM keeps the text and year accordions in separate sibling Drupal blocks.
    # Bound traversal to their enclosing course-page rather than to the text block.
    container = marker.find_parent(class_="course-page") or marker.find_parent("main")
    for node in marker.next_elements:
        if not isinstance(node, Tag) or id(node) in marker_children:
            continue
        if container is not None and container not in node.parents:
            break
        text = _text(node)
        if len(text) < 160 and _STOP.fullmatch(text.strip()):
            break
        if node.name in {"header", "aside"}:
            break
        nodes.append(node)
    return nodes


def _is_label(node: Tag) -> bool:
    text = _text(node)
    if len(text) > 200 or node.name in {"ul", "ol", "table", "tr", "tbody", "thead"}:
        return False
    if node.name in {"strong", "b"}:
        parent_item = node.find_parent("li")
        if parent_item is not None and not _is_label(parent_item):
            return False
    if node.name in _HEADING_TAGS or node.name in {"th", "strong", "b"}:
        return True
    if node.name == "li" and re.search(r"\b(?:choose|select|core courses?)\b", text, re.I):
        return bool(re.match(r"^(?:major\s+|open\s+|language\s+)?(?:elective|core)", text, re.I))
    if node.name in {"p", "div", "td"}:
        return not node.find(["ul", "ol", "table"]) and bool(
            re.match(
                r"^(?:years?\b|sem(?:ester)?s?\b|(?:(?:major|open|language|common)\s+)*(?:electives?|core)\b)",
                text,
                re.I,
            )
        )
    return False


def _course(node: Tag, context: _Context) -> ParsedCourse | None:
    text = _text(node)
    if not text:
        return None
    if len(text) > 255:
        raise CurriculumParseError(
            "course_title_too_long",
            "A course entry exceeds 255 characters; review source structure",
        )
    notes = ["title_only", "needs_syllabus_confirmation"]
    if re.fullmatch(
        r"(?:(?:programming|major|open|language)\s+)*electives?(?:\s+(?:[IVX]+|\d+))?(?:\s*\(\d+\))?",
        text,
        re.I,
    ):
        notes.append("unresolved_elective_placeholder")
    if re.search(r"\b[IVX]+\s*(?:&|,|and)\s*[IVX]+\b", text):
        notes.append("composite_label_not_split")
    if re.search(r"(?:\.\.\.|…)$", text) or re.search(
        r"\b(?:Visualisatio|Embedded Sy)$", text, re.I
    ):
        notes.append("possibly_truncated_title_requires_confirmation")
    if text.count("(") != text.count(")"):
        notes.append("unbalanced_title_punctuation_requires_confirmation")
    return ParsedCourse(
        course_name=text,
        year=context.year,
        semester=context.semester,
        course_type=context.course_type,
        raw_year_label=context.raw_year,
        raw_semester_label=context.raw_semester,
        elective_group=context.elective_group,
        source_locator=_locator(node),
        source_excerpt=text,
        review_notes=notes,
    )


def parse_programme(html: str, url: str) -> ParsedProgramme:
    """Extract a title inventory while retaining explicit labels and ambiguous entries."""
    soup = _soup(html)
    title = soup.select_one(".program-title") or soup.find("h1")
    if title is None or not _text(title):
        raise CurriculumParseError(
            "programme_title_missing", "Programme page has no explicit programme title"
        )
    nodes = _main_course_nodes(soup)
    context = _Context()
    courses: list[ParsedCourse] = []
    consumed: set[int] = set()
    for node in nodes:
        if id(node) in consumed:
            continue
        if node.name == "table":
            parsed, context = _table_courses(node, context)
            courses.extend(parsed)
            consumed.update(id(child) for child in node.descendants if isinstance(child, Tag))
        elif _is_label(node):
            if "accordion-header" in node.get("class", []) and not _YEAR.search(_text(node)):
                context = _Context()
            label = _label_context(_text(node), context)
            if label is not None:
                context = label
        elif node.name == "li":
            # A list wrapper with nested course lists is a grouping, never one huge title.
            if node.find(["ul", "ol"]):
                own_text = " ".join(
                    str(c).strip() for c in node.children if isinstance(c, NavigableString)
                )
                context = _label_context(own_text, context) or context
                continue
            item = _course(node, context)
            if item is not None:
                courses.append(item)
    if not courses:
        raise CurriculumParseError(
            "course_list_empty", "Main Courses contains no supported, nonempty course list"
        )
    courses = _join_bilingual_bullets(courses, soup)
    return ParsedProgramme(
        name=_text(title),
        canonical_url=_canonical_url(url),
        courses=courses,
        notes=[
            "public_main_courses_not_certified_complete_curriculum",
            "course_descriptions_not_extracted",
        ],
    )


def _join_bilingual_bullets(courses: list[ParsedCourse], soup: BeautifulSoup) -> list[ParsedCourse]:
    """Adjacent translation-only bullets remain one labelled, reviewable appearance.

    Pair only adjacent leaf bullets in the same list and identical year/group context.
    Do not merge names that already mix languages or unrelated titles in another pool.
    """
    result: list[ParsedCourse] = []
    cjk = re.compile(r"[\u3400-\u9fff]")
    latin = re.compile(r"[a-zA-Z]")
    for course in courses:
        if result and cjk.search(course.course_name) and not latin.search(course.course_name):
            previous = result[-1]
            left = soup.select_one(previous.source_locator)
            right = soup.select_one(course.source_locator)
            adjacent = (
                left is not None and right is not None and left.find_next_sibling("li") is right
            )
            matching = all(
                getattr(previous, key) == getattr(course, key)
                for key in ("year", "semester", "course_type", "elective_group")
            )
            if (
                adjacent
                and matching
                and latin.search(previous.course_name)
                and not cjk.search(previous.course_name)
            ):
                joined = f"{previous.course_name} {course.course_name}"
                if len(joined) > 255:
                    raise CurriculumParseError(
                        "course_title_too_long",
                        "Combined bilingual course label exceeds 255 characters",
                    )
                result[-1] = previous.model_copy(
                    update={
                        "course_name": joined,
                        "source_locator": f"{previous.source_locator}, {course.source_locator}",
                        "source_excerpt": joined,
                        "review_notes": [
                            *previous.review_notes,
                            "bilingual_adjacent_bullets_paired_requires_confirmation",
                        ],
                    }
                )
                # Revalidate combined locator/name lengths rather than truncate source text.
                result[-1] = ParsedCourse.model_validate(result[-1].model_dump())
                continue
        result.append(course)
    return result


def _table_courses(table: Tag, initial: _Context) -> tuple[list[ParsedCourse], _Context]:
    """Support explicit year columns and heading rows without guessing table semantics."""
    result: list[ParsedCourse] = []
    columns: dict[int, _Context] = {}
    context = replace(initial)
    for row in table.find_all("tr"):
        if row.find_parent("table") is not table:
            continue
        cells = row.find_all(["th", "td"], recursive=False)
        for index, cell in enumerate(cells):
            text = _text(cell)
            if not cell.find(["ul", "ol"]) and _is_label(cell):
                label = _label_context(text, context)
                if label is not None:
                    if len(cells) == 1 or cell.get("colspan"):
                        context = label
                        columns = {}
                    else:
                        columns[index] = label
                    continue
            local_context = replace(columns.get(index, context))
            items = cell.find_all("li")
            for item in items:
                if item.find(["ul", "ol"]):
                    continue
                parsed = _course(item, local_context)
                if parsed is not None:
                    result.append(parsed)
    return result, context
