# Implementation status

Codex should update this file only after completing and verifying each phase.

- [ ] Phase 01 — Foundation and data model
- [ ] Phase 02 — Whole-programme document ingestion
- [ ] Phase 03 — Versioned workforce/AI evidence ingestion
- [ ] Phase 04 — Course and programme relevance analysis
- [ ] Phase 05 — Recommendations and alternatives
- [ ] Phase 06 — Scenarios and academic reporting
- [ ] Phase 07 — Backend integration and demo hardening
- [ ] Phase 08 — Optional frontend (only after backend acceptance)

Phase 01 implementation is ready for its PostgreSQL acceptance check. No later phase has been implemented.

Verified locally on 2026-10-24:

- Editable package installation succeeded with Python 3.13.
- `python -m pytest -q --basetemp=.pytest-tmp`: **76 passed, 1 skipped, 1 warning**.
- The skipped test is the opt-in PostgreSQL migration integration test: `TEST_DATABASE_URL` is unset and Docker/PostgreSQL tools are unavailable locally.
- Ruff lint passed; Ruff format check passed (57 files).
- PostgreSQL offline migration SQL generation passed; this does not prove a live database migration.
- Uvicorn started successfully. Real localhost checks returned live 200, OpenAPI 200 and readiness 503 with the documented error while PostgreSQL was unavailable.
- Synthetic fixture tests verify all 12 courses, both electives, source references, missing syllabus metadata, idempotent reruns and rejection of changed/invalid records.
- One upstream Starlette warning recommends moving its test client from httpx to httpx2. The suite passes with the project's required httpx dependency.

Current acceptance blocker: the first GitHub Actions run must verify the migration against its PostgreSQL 16 service. Phase 01 remains unchecked until that result is available. The Windows sandbox blocks TestClient event-loop sockets; the passing suite was run with local socket access outside that sandbox. No real university analysis or deployment has occurred.
