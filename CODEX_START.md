# Paste this as your FIRST message to Codex

```text
You are the lead backend engineer for SHIFT//OS. The working directory is the project root of a new repository containing AGENTS.md, README.md, docs/, prompts/, and examples/.

Read AGENTS.md, README.md, STATUS.md, docs/01_PRODUCT_SCOPE.md, docs/02_BACKEND_ARCHITECTURE.md, docs/03_DATA_MODEL.md, docs/04_ANALYSIS_AND_DECISIONS.md, docs/05_API_CONTRACT.md, docs/07_TEST_PLAN.md, and prompts/01_FOUNDATION.md.

Implement PHASE 01 ONLY, following prompts/01_FOUNDATION.md. This is a backend-first project. Build a clean FastAPI application with SQLAlchemy models, PostgreSQL/Docker Compose configuration, Alembic initial migration, health endpoints, environment configuration, test setup, and seed/import capability for synthetic fixture records as specified. Do not build the AI engine, document parser, frontend, or unrelated features yet.

IMPORTANT PRODUCT CONSTRAINT: The eventual workflow analyses an ENTIRE uploaded academic programme and ALL detected courses. Never design the database or primary API around selecting one course to analyse. No manual relevance percentages.

Run any available lint/tests and fix failures. Show me files created, exact local run commands, test output, assumptions, and remaining TODOs. Update STATUS.md only after verified acceptance criteria are met. Do not claim a database integration test passed if Docker/Postgres is unavailable.
```

## After Phase 01

Paste the contents of `prompts/02_DOCUMENT_INGESTION.md`, then Phase 03, and so on. Ask Codex to complete, test, and commit/review each phase separately.

## If Codex gets distracted

```text
Stop feature expansion. Re-read AGENTS.md, docs/01_PRODUCT_SCOPE.md and the current prompts/0X_*.md. Implement only the acceptance criteria of the current phase. Identify any proposed work that belongs to a later phase and defer it.
```
