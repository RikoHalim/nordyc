# Curriculum ingestion & university-wide catalogue coverage

## Goal

Discover the XMUM undergraduate programme list from official URLs and, programme by programme, collect publicly available course titles and year grouping. **Detailed syllabi are optional.** The system should not require selecting a single course for analysis.

## Discovery strategy

1. Begin at official programme directory and known official brochure/download listings. Collect programme URLs, names, degrees, field/category, date and source provenance.
2. Use a safe, domain-allowlisted extractor with bounded depth and rate limits, no login/captcha bypass, terms/robots checks and graceful network errors.
3. For each programme page, parse explicit headings (`Year 1`, `Year 2`, etc.), course labels, optional course codes, compulsory/elective tags. Preserve raw source locator and text excerpt.
4. Do not infer a semester or elective classification unless written. `null` is valid.
5. Output a coverage report: programmes discovered vs parsed, courses extracted, title-only counts, pages with ambiguous/unreadable structure, official source URLs and timestamps.
6. Cache and version fetch results; repeated run is idempotent. Manual import of official URLs/CSV/optional brochure is a fallback if automatic discovery fails.
7. Add a tiny **cross-disciplinary quality fixture** and integration tests for page layout changes. Never count fixture records as real university coverage.

## Public-only quality categories

- `verified_course_title`: appears in official page or brochure, with exact line/selector/page citation.
- `public_description`: actual description found; no assumption other programme provides it.
- `title_only`: no detailed syllabus; significance/skills are hypotheses, not facts.
- `unverified_candidate`: page scraped but ambiguous, requires human correction.

## Result contract

`programme -> [courses]` where each course carries course_id, title, academic_year nullable, semester nullable, elective nullable, evidence_level, official_url, source_locator, observed_at.

## Important failure cases

- Websites change; scraper reports parser failure instead of `0 courses` as though verified.
- Brochure differs from webpage; keep both source versions, do not silently merge conflicting year structures.
- Year heading `Year 3/4` or internship grouping: keep exact label and parsed numeric year only when unambiguous.
- Same course title in more than one programme: different relationships, no global deduplication that discards enrolment context.
