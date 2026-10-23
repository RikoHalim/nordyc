# PHASE 2 — XMUM programme and course discovery

First verify Phase 1 passes. Read `docs/04_DISCOVERY_AND_INGESTION.md` and source registry.

Implement official-source discovery of **all publicly discoverable XMUM undergraduate programmes**, with course titles, years and elective status where explicitly stated. Start from official directory; follow programme/brochure URLs with bounded crawling and terms/robots respect. Support heterogeneous pages, failures and manual official CSV/URL fallback. Store source URL/locator, source timestamp, canonical programme/course snapshots and extraction review status. Version, deduplicate and expose completeness metrics and parsing tests.

**Do not** invent syllabi, course descriptions, semesters, course codes or hidden majors. Do not claim XMUM coverage until a real run and verified count. Offline HTML fixtures across three disciplines must work; optional live extraction only when access permits. Preserve year groupings.

API: discovery job, status, programme coverage, programme course list; route shapes in `docs/10_API_CONTRACT.md`.

Run tests and document actual source access outcomes. Update `STATUS.md`, then STOP. Next: Phase 3.
