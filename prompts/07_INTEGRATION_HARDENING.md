# CODEX PROMPT — Phase 07: E2E Integration, Testing and Demo Readiness

Read ALL relevant `AGENTS.md`, `docs/07_TEST_PLAN.md`, `docs/08_DEMO_WORKFLOW.md`, `docs/11_SECURITY.md` and current repo. Implement **hardening and integration only**, not new features.

1. From clean DB: `docker compose up`, `alembic upgrade head`, seed fixtures; import a programme with multiple courses, ingest curated sources, start programme-wide analysis, compare two snapshots/scenarios, fetch alternative recommendations and full academic JSON report.
2. Write `scripts/demo.sh` or portable Python equivalent, sample curl commands, README reproducible run instructions; no reliance on external network during tests.
3. Ensure **every detected course** is present in the analysis report, including missing-syllabus courses. Check source IDs resolve and `is_synthetic` is visible.
4. Enforce upload and prompt-injection safety boundaries; do not log document bodies/secrets. Flag scanned PDF for later OCR.
5. Performance smoke test with 40+ synthetic course records (no forced hard-coded course count); record bottlenecks not fake benchmarks.
6. Add regression tests for LLM invalid JSON/source refs, missing source dates, partial ingestion, repeated requests, multiple programme revisions, and proposal approval state.
7. Review spec-vs-code discrepancies; update docs and `STATUS.md` with real test results and known limitations.

Output an honest demo readiness report: working APIs, limitations, actual test command results, remaining risks. After this phase the team can start frontend.
