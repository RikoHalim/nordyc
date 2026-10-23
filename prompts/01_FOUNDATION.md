# PHASE 1 — Foundation compatibility and maintenance

Phase 1 already exists. Inspect and preserve working code, migration 0001 and persisted data; make only necessary additive corrections. Do not recreate the repository.

Read `AGENTS.md`, `README.md`, `STATUS.md`, docs 01–03 and 10–11. **Implement Phase 1 only**.

## Implement

- FastAPI app with `/health`, `/api/v1` router, conventional settings, logging and typed Pydantic errors.
- PostgreSQL database connection, SQLAlchemy 2 declarative models and Alembic migrations.
- Institution, Programme, Course and Source minimal tables. A university has many programmes; programme has many courses; optional year/semester/type and **source provenance** are supported.
- Basic institution/programme/course create/read endpoints (retain compatible routes; updates/deletes need a later explicit versioning contract) with pagination and validation. Add consistent 404/409/422 errors.
- Database transaction lifecycle and dependency injection, clean package layout.
- Basic automated tests including nested multi-major fixture, nullable metadata, foreign keys, and migrations. Provide local setup e.g. docker compose Postgres optionally (if used, document it).
- `.env.example`, dependency file/lock, `.gitignore`, README development instructions and example commands.

## Not now

No scraper, no external datasets, no LLM, no relevance algorithm, no frontend, no fabricated imported XMUM records.

## Acceptance / stop

Demonstrate creating one institution with **multiple distinct programmes**, each with courses and year fields, using local DB and API. Run tests and migrations; record actual command outcomes. Update `STATUS.md`: Phase 1 COMPLETE only if genuinely tested. Then STOP; next `prompts/02_CURRICULUM_DISCOVERY.md`.
