# 10 — Five-Person Team Work Plan

## Roles

- **Member 1 — Research/proposal & validation:** analyse academic requirements, committee compliance, final presentation, judge narrative and human-review rubric. Maintains `docs/01...` and demo script.
- **Member 2 — Workforce/evidence data:** document official Malaysian sources and rights; curate dated sample snapshots, skill/occupation crosswalks, reference integrity tests. Owns `examples/sample_evidence.json` and evidence provenance docs.
- **Member 3 — Backend/data engineer:** SQLAlchemy schema, Alembic, FastAPI routes, document ingestion, uploads/jobs, DB integration tests.
- **Member 4 — AI/decision engineer:** LLM provider interface, evidence-backed course analysis, validation, recommendation/scenario logic, outcome tests.
- **Member 5 — Integration/frontend engineer:** initially write API contract and end-to-end tests, help validate fixture consistency; **only then** React dashboard (after Phase 07).

## Parallelise without merge chaos

1. Team agrees `docs/03_DATA_MODEL.md` and `docs/05_API_CONTRACT.md` before independent edits.
2. Backend owns `models/`, `db/`, `api/`; AI owns `services/analysis/`, `services/recommendations/`, `llm/`; data owns `services/evidence/` and sample sources; shared DTOs need review.
3. Use Git branches, small pull requests and migrations reviewed before merge. No two members should independently create incompatible tables.
4. Every PR: scope, files, exact test command, output, data provenance impact, backwards compatibility.
5. Weekly / demo checkpoint: run all-course analysis from a clean DB, spot check 3 cases with manual academic interpretation.

## Stop-the-line issues

Do not ship recommendations without real anchors; if a fixture fails to show provenance, fix before adding frontend. Do not demo synthetic evidence as authentic university or labour-market facts.
