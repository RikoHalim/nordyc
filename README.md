# SHIFT//OS — Codex Backend Starter Kit

**Current checkout:** Phase 01 is implemented and verified, including PostgreSQL migration testing in GitHub CI. See [the quickstart](#phase-01-implementation-and-quickstart), [handoff](PHASE_01_HANDOFF.md), and [status](STATUS.md). The original starter-kit instructions below remain as context for later phases.

**What this starter kit is:** A set of *project instructions, design contracts, synthetic fixtures, and sequential prompts* for building the backend of SHIFT//OS in a new project folder. The original ZIP contained specifications; the Phase 01 application code is now included in this repository.

## Start in 4 steps

1. Make a new empty project folder (for example `shift-os`) and **extract the ZIP contents directly into that folder**. `AGENTS.md` must be in the project root.
2. Open the **same folder** in VS Code / Codex. Initialise Git (`git init`) if needed.
3. Open **`CODEX_START.md`** and paste its **START PROMPT** into Codex. Ask Codex to implement **Phase 01 only**.
4. After Codex finishes, inspect the changes, run the tests, and continue with `prompts/02_DOCUMENT_INGESTION.md` **one phase at a time**. Do not paste all the phase prompts at once.

## What you are building

A **Malaysia-first university academic decision-support backend**. A university uploads the **whole degree curriculum** plus detailed course syllabi where available. SHIFT//OS assesses **every course** for continued relevance amid AI developments and documents its uncertainties. It then offers **programme-level recommendations** and **course-level explanations**. AI suggests a primary academic response first; authorised humans may compare alternatives and approve or reject.

The central question is: **Is our entire academic programme still relevant in the AI era, and what should change, if anything?**

## Scope for the first backend MVP

- Pilot: Xiamen University Malaysia, Software Engineering programme, Malaysia.
- Demonstrate on **8–12 illustrative courses first**, but design for **all** courses and electives in a programme. Never use a single-course picker as the primary ingestion flow.
- Upload programme structure plus one or more supporting syllabi; analyse what is supported, mark missing details **INSUFFICIENT_EVIDENCE**.
- Data sources: versioned public/open and clearly labelled synthetic examples. No private student data.
- Two labelled uncertainty scenarios, two dated workforce snapshots, reproducible recommendations, SDG links supported by explanations.
- No frontend until the backend acceptance gate passes; Swagger/OpenAPI is sufficient during backend development.

## Files

| Path | Purpose |
|---|---|
| `AGENTS.md` | Persistent instructions Codex reads automatically |
| `CODEX_START.md` | Exact initial Codex prompt |
| `docs/01_PRODUCT_SCOPE.md` | Problem, users, functional scope, non-goals |
| `docs/02_BACKEND_ARCHITECTURE.md` | Layers, backend structure, runtime and technology |
| `docs/03_DATA_MODEL.md` | Entities, fields, relationships, statuses |
| `docs/04_ANALYSIS_AND_DECISIONS.md` | How to judge relevance without made-up percentages |
| `docs/05_API_CONTRACT.md` | Endpoints and request / response conventions |
| `docs/06_SOURCES_AND_PROVENANCE.md` | Sources, licences, dated evidence, limitations |
| `docs/07_TEST_PLAN.md` | Acceptance gates and negative tests |
| `docs/08_DEMO_WORKFLOW.md` | End-to-end pilot demonstration |
| `docs/09_SCOPE_AND_OPEN_QUESTIONS.md` | Product decisions and organiser-compliance caveats |
| `docs/10_TEAM_WORKFLOW.md` | Five-person division of work and commit boundaries |
| `docs/11_SECURITY.md` | File-upload, privacy and LLM safeguards |
| `prompts/*.md` | Implementation instructions, one phase at a time |
| `examples/*.json` | Synthetic test records; **not factual university syllabi** |
| `STATUS.md` | Phase checklist (Codex updates when work is complete) |

## Planned project layout (Codex will create this)

```text
src/shiftos/
  main.py
  api/routers/
  core/
  db/
  models/
  schemas/
  services/ingestion/
  services/evidence/
  services/analysis/
  services/recommendations/
  services/scenarios/
  services/reports/
  llm/
tests/
alembic/
pyproject.toml
alembic.ini
compose.yaml
.env.example
```

## Core engineering rules

1. **Evidence before conclusions:** never invent a CLO, lecture topic, assessment, source, date, skill-demand statistic or course verdict.
2. **No arbitrary relevance scores:** use explainable qualitative statuses plus evidence sufficiency; percentages are not required.
3. **Analysis scope is programme-wide:** every identified course appears in an analysis run, including courses with insufficient documents.
4. **Automated suggestion, human decision:** default AI recommendation first; alternatives shown; approvals are explicit and never inferred.
5. **Deterministic validation:** LLM may extract and draft, but cannot override provenance checks or business rules.
6. **Reproducible versioning:** preserve document revisions, source snapshots, model/prompt versions, result generation time.
7. **Low-cost MVP:** avoid multi-agent orchestration, separate vector DB, custom model training, live scraping, scheduling systems, recruitment features and unaudited forecasts.

## Developer references

- Codex project guidance: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy 2.x: https://docs.sqlalchemy.org/en/20/
- Alembic: https://alembic.sqlalchemy.org/
- PyMuPDF: https://pymupdf.readthedocs.io/en/latest/recipes-text.html

**Important:** This starter kit is a development specification. Neither real curriculum analysis nor real Malaysian labour-market data has been loaded into the ZIP.

## Phase 01 implementation and quickstart

The original starter instructions above remain as project context. This checkout now contains the Phase 01 foundation: a FastAPI application, institution/programme APIs, a programme-wide course inventory, PostgreSQL models and an Alembic migration, plus an offline synthetic fixture importer. Later phases remain specified in `prompts/`; document upload/parsing, AI analysis, recommendations and frontend work are deferred.

Use Python 3.11 or newer, PowerShell and Docker with Compose v2. Run these commands from the project root:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` before continuing: choose a local `POSTGRES_PASSWORD` and replace `<URL_ENCODED_PASSWORD>` in `DATABASE_URL` with a URL-encoded copy of the same password. The sample intentionally supplies no password. If you change the database name, user or published port, update the connection URL to match. Settings read `.env`; shell environment variables take precedence. No API key is needed.

```powershell
docker compose up -d --wait
python -m alembic upgrade head
python -m shiftos.cli import-fixture examples/sample_programme.json
uvicorn shiftos.main:app --reload --app-dir src
```

Open [Swagger UI](http://127.0.0.1:8000/docs) or [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). `GET /health/live` returns `{"status":"alive"}` without opening a database connection. `GET /health/ready` executes `SELECT 1`, returns `{"status":"ready"}` on connectivity success and returns a structured 503 error when the database is unavailable. Readiness checks connectivity; apply migrations separately before using the academic APIs.

The fixture command prints programme/revision IDs, the actual course count, `created` and `is_synthetic: true`. Rerunning an identical fixture returns `created: false` without duplicating courses. Changed content under existing IDs is rejected; use new revision and record IDs to preserve history. This command reads local JSON and writes to your configured database; it fetches no websites and runs no AI.

All imported institution, programme, revision, course, document and anchor records remain explicitly synthetic. Inventory-only courses keep `detailed_syllabus_available: false` and `extraction_status: INVENTORY_ONLY`; no learning evidence is invented for them. Provided synthetic facts and exact anchor excerpts remain in document metadata for later ingestion work. These are invented test curricula, not factual claims about any university.

### Development checks

With the virtual environment active:

```powershell
python -m pytest -q --basetemp=.pytest-tmp
python -m ruff check .
python -m ruff format --check .
```

Unit/API tests use isolated SQLite databases and synthetic fixtures. The PostgreSQL migration integration test is skipped unless `TEST_DATABASE_URL` is explicitly set. To opt in, replace the placeholder below with your local test password first:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://shiftos:<URL_ENCODED_PASSWORD>@localhost:5432/shiftos'
python -m pytest -q -m integration --basetemp=.pytest-tmp
Remove-Item Env:TEST_DATABASE_URL
```

The test role must be able to create schemas. Each run creates a randomly named `shiftos_test_*` schema, exercises upgrade, constraints, schema/metadata comparison, downgrade and re-upgrade, then drops that schema. It does not migrate the application's existing schema. SQLite unit results and generated SQL are separate from a successful PostgreSQL integration run; see `STATUS.md` for verified results and current limitations.

To inspect PostgreSQL migration SQL without a live database:

```powershell
python -m alembic upgrade head --sql
```

### Foundation choices

The application factory owns its engine and disposes it through [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/). HTTP database work and the importer use synchronous SQLAlchemy 2 sessions with psycopg, keeping this phase's service functions consistent and easy to test; request sessions close through a dependency, following the [SQLAlchemy session lifecycle](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it). PostgreSQL is the development/runtime database. SQLite is permitted by settings only for tests and cannot validate the PostgreSQL migration.

The API uses `/api/v1`, UUID identifiers, timezone-aware UTC timestamps and explicit `is_synthetic` flags. Institution/programme lists and active-revision course lists use `limit`/`offset` pagination, with default limit 50 and maximum 100. Results sort by UUID; the limit caps one page, not programme size. See `docs/05_API_CONTRACT.md` for exact Phase 01 shapes and `docs/02_BACKEND_ARCHITECTURE.md` for persistence decisions.
