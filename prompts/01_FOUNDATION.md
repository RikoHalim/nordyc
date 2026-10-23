# CODEX PROMPT — Phase 01: Backend Foundation

## Mission

Implement only the backend foundation for the modular-monolith architecture in `docs/02_BACKEND_ARCHITECTURE.md`. This is **not** a model-powered prototype yet.

## Read first

`AGENTS.md`, `docs/01_PRODUCT_SCOPE.md`, `docs/02_BACKEND_ARCHITECTURE.md`, `docs/03_DATA_MODEL.md`, `docs/05_API_CONTRACT.md`, `docs/07_TEST_PLAN.md`, `examples/sample_programme.json`.

## Implement

1. A Python 3.11+ project using `src/shiftos/` with `pyproject.toml` and installable package. FastAPI app factory/lifespan, versioned router prefix and automatic OpenAPI.
2. Typed settings (Pydantic Settings), `.env.example`, safe defaults. Health live/ready endpoints and consistent error schema.
3. PostgreSQL Docker Compose dev DB and SQLAlchemy 2 async/sync choice documented (prefer a simple consistent approach), Alembic initial migrations for key Phase 01 tables: institution, programme, revision, course, document metadata, anchor, and job/run foundation. Remaining tables from data model may be added later; avoid rushed giant migration if not needed.
4. Endpoints create/list institutions, create/read programme, list all programme courses; basic input validation. Include a **documented offline fixture import command** that reads `examples/sample_programme.json` and preserves synthetic flags/unknown syllabus status. Idempotent reruns.
5. pytest API + service tests, migration integration test (if Postgres available), Ruff lint/format setup, simple README dev commands. No API key required.

## Key invariants

- Programme revision has many course records. Do not hardcode the number or model primary flow as one-course review.
- Real programme metadata can be incomplete; no fictitious CLOs, assessments or competency scores.
- UUID PKs, constraints, UTC timestamp fields. Do not leak credentials.
- `GET /api/v1/programmes/{id}/courses` returns **all** programme courses, paginated if needed.

## Out of scope this phase

Document text parsing, workforce source fetching, LLM integration, relevance decision engine, simulation, frontend, PDF reports.

## Done only when

- App starts, OpenAPI and both health endpoints behave as specified.
- PostgreSQL migration runs or limitation is explicitly reported.
- Fixture import, programme creation/listing, and pagination tests pass.
- `python -m pytest -q` and lint pass if environment supports installing dependencies.
- Show exact files and run commands; update `STATUS.md` with verified results.
