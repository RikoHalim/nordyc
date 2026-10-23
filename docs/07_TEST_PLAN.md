# 07 — Tests and Acceptance Gates

Codex must implement tests per phase and report exact commands/results. A passing unit suite is not a substitute for real Postgres migration testing.

## Phase 01 — Foundation

- FastAPI starts and OpenAPI loads.
- `/health/live` returns success without DB; `/health/ready` checks DB and fails appropriately.
- SQLAlchemy metadata and initial Alembic migration work on PostgreSQL; unique/FK constraints verified.
- Create institution + programme, and list programme courses; status codes and schemas tested.
- Deterministic synthetic fixture import doesn't create duplicate courses when rerun.
- Ruff and pytest pass; secrets only env-based.

## Phase 02 — Document ingestion

- Accept PDF and DOCX only, size/type checks and traversal protection.
- Programme structure listing multiple courses yields **multiple course records**, including electives. Duplicate codes get review flag/merge policy, not silent loss.
- Extracted text contains page/paragraph anchors; no invented CLOs/topics.
- Scanned-only PDF => explicit `NEEDS_OCR` (not blank interpreted as no content).
- Missing detailed syllabus => course still in programme inventory and eventual analysis results.
- Re-upload same bytes returns existing content or a version-linked result, not silent duplication.

## Phase 03 — Evidence integrity

- Valid synthetic sources/snapshots import with correct dates/jurisdiction.
- Invalid source ID/anchor and malformed snapshot are rejected.
- Occupation counts aren't automatically transformed into skill demand.
- Older and newer snapshots coexist; old results remain reproducible.

## Phase 04 — Relevance analysis

- A run produces **exactly N course results for N programme courses**, including courses without detailed syllabi.
- With only a course title, `INSUFFICIENT_EVIDENCE` and a clear reason.
- 'AI automates task X' does **not** imply course is obsolete.
- Source refs in result are validated and retrievable; any invented IDs rejected.
- No LLM configured => explicit unavailable/demo state; never pretend real AI ran.
- Unit cases handle contradictory evidence, empty outcomes, empty source snapshot, repeated rerun and partial document parse.
- Course analysed as part of whole programme; programme findings consider **cross-course** coverage.

## Phase 05 — Decisions

- Recommendation produced only with admissible evidence; otherwise `REQUEST_MORE_EVIDENCE`.
- Primary is present when justified; alternatives include no change where admissible.
- New elective recommended only after inspecting existing programme coverage and revision options.
- Replace/consolidate is marked as **review**, never auto-executed.
- Seminar/guest speaker/career talk cannot count attendance as skill mastery.
- Human approval starts `PROPOSED` and changes only via explicit action.

## Phase 06 — Scenarios and reports

- Both scenarios use documented assumptions; identical assumptions yield identical outputs.
- Source change replay creates a new run with old run preserved.
- Report includes exact course count, evidence gaps, primary actions, alternatives, cited support, dates, review statuses and SDG justification or `NEEDS_REVIEW`.
- No fake labour statistics / ROI / job placement predictions.

## Phase 07 — Integration / demo

- Start database; migrate; import sample docs/synthetic fixtures; run whole programme; retrieve every course + programme findings; request recommendations, scenarios, academic report.
- All paths documented and scripted with reproducible demo commands.
- Smoke tests cover 1 valid course, 1 missing syllabus and 1 conflicting/unknown source.
- Tests must be offline/deterministic. Real LLM tests opt-in, separately labelled and not required for CI.

## Acceptance checklist used at each milestone

1. Behaviour meets scope; no off-scope features.
2. Tests for success + at least two failure/unknown cases.
3. Runs with documented commands; env sample accurate.
4. Result has source identity and synthetic markers where relevant.
5. Codex can summarise remaining issues without claiming unsupported success.
