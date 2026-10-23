# Project instructions for Codex — SHIFT//OS

Read `README.md`, `docs/01_PRODUCT_SCOPE.md`, `docs/04_ANALYSIS_AND_DECISIONS.md`, and the **specific phase prompt** before modifying code. Treat these as requirements, not optional context. See `docs/09_SCOPE_AND_OPEN_QUESTIONS.md` for unresolved assumptions.

## Non-negotiable product rules

- The principal user is a **Malaysian university career centre**, collaborating with faculty; it does **not** have unilateral authority to alter course curricula.
- The **primary workflow analyses an entire programme** and all its identified courses (compulsory + elective), not one selected course.
- University onboarding: institution name, academic programme, programme/curriculum documents. No CV, no manual competency percentages, no budget or planning-period fields at onboarding; optional constraints are entered later when comparing actions.
- AI must evaluate course relevance **against AI developments and occupational requirements**, not assume that an AI-automatable task makes foundational education obsolete.
- Required outcomes include `RETAIN`, `UPDATE`, `MAJOR_REVIEW`, `INSUFFICIENT_EVIDENCE`. Proposed replacement / consolidation requires especially strong supporting evidence and faculty review.
- Action options: keep/no change; syllabus revision; major redesign/replacement review; new elective/course recommendation; **Workshops & Industry Engagement** (one category covering hands-on training, industry seminars, guest speakers, career talks). These may be combined when justified. Workshop may be standalone or pilot; not automatically an elective precursor.
- Attendance at seminars/talks is **not** proof of skill mastery. Workshop skill gain requires suitable assessment data.
- System generates primary recommendation **after** analysis, and also exposes alternatives; a human decides.
- Treat the user's stated hackathon-organiser approval as approval of the institutional concept and CV-upload exemption, **not** proof that all individual-level brief requirements were waived. Track as an open issue; do not invent approval.

## Engineering constraints

- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, pytest, Ruff. Use PyMuPDF for digital PDFs, python-docx for DOCX.
- Define coherent modules: ingestion, source/evidence, relevance analysis, recommendations, scenario simulation, academic reports. Do not invent extra product modules.
- Keep LLM integration behind an interface. Never hard-code a vendor. API key only from environment variables; never in examples or logs.
- Use Pydantic schemas for both API and LLM structured output. Validate source references, allowed status/action enums and evidence sufficiency in normal code. If an LLM is unavailable, **fail explicitly or run a prominently labelled synthetic/demo adapter**; never fake live AI analysis.
- Run the backend with `uvicorn shiftos.main:app --reload --app-dir src` (unless architecture is explicitly documented otherwise).
- Preserve source excerpts/anchors and version IDs so each important finding is auditable.
- Use UUIDs and timezone-aware UTC timestamps for stored records. SQL migrations via Alembic.
- Never call live websites in unit tests. Use synthetic fixtures marked `is_synthetic: true`.
- Keep endpoint names and response shapes aligned with `docs/05_API_CONTRACT.md`.
- Implement only the requested development phase; do not scaffold unrelated features or frontend prematurely.

## Working style and output

- First inspect current files; don't overwrite existing user changes.
- State a short plan; implement; run formatting/lint/tests; report **what changed, what passed, what failed, next step**.
- Add tests for significant logic and negative cases, especially **missing evidence**, invalid references and all-course analysis.
- Prefer maintainable service functions and explicit types. Avoid giant one-file prototypes, fragile prompt-only rules, or overengineering.
- Update `STATUS.md` only when a phase's acceptance criteria are met. If blocked, document exact blockers instead of claiming success.
- Never declare the university's real courses obsolete or recommend removal based solely on demo fixtures.
