# Phase 01 handoff

The foundation implements the Phase 01 prompt only. It includes FastAPI factory/lifespan, typed environment settings, consistent errors, health checks, PostgreSQL models, Alembic, institution/programme APIs, paginated whole-programme inventory, and an idempotent offline fixture CLI. All supplied synthetic facts, excerpts, identifiers and synthetic markers are retained. No analysis verdict is generated.

## Run locally

From the project directory in PowerShell:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` to set `POSTGRES_PASSWORD` and its URL-encoded equivalent in `DATABASE_URL`, then:

```powershell
docker compose up -d --wait
python -m alembic upgrade head
python -m shiftos.cli import-fixture examples/sample_programme.json
uvicorn shiftos.main:app --reload --app-dir src
```

```powershell
python -m pytest -q --basetemp=.pytest-tmp
python -m ruff check .
python -m ruff format --check .
```

The fixture programme ID is `693f20d6-4952-5c77-aae3-47c59928449d`. Retrieve its inventory through `/api/v1/programmes/{id}/courses`; traverse pages using `limit` and `offset`. The fixture contains 12 invented courses, including two electives and six without detailed syllabi.

## Verification

Local output: `76 passed, 1 skipped, 1 warning in 2.58s`. The skipped PostgreSQL integration requires `TEST_DATABASE_URL`; Docker/PostgreSQL is unavailable locally. [GitHub Actions run 1](https://github.com/RikoHalim/shift-os/actions/runs/39985901492) passed with Python 3.11 and PostgreSQL 16: `77 passed, 1 warning in 2.55s`, with no skips. This verifies the real migration, constraints, schema comparison, downgrade and re-upgrade. Phase 01 is complete in `STATUS.md`.

Ruff lint and formatting pass. Editable installation, CLI help, offline PostgreSQL SQL generation and Uvicorn startup were verified. Real HTTP smoke checks returned live 200, OpenAPI 200 and readiness 503 without a database. Windows sandbox restrictions required running TestClient with local socket access. One upstream Starlette/httpx deprecation warning remains.

## Decisions and remaining work

- PostgreSQL is the runtime database; SQLite is limited to unit/API tests. Sessions and services are synchronous.
- A new programme starts with an empty revision labelled `initial` unless a version label is supplied. Metadata may remain unknown. The courses endpoint returns the active revision and includes every course across pages.
- Fixture facts remain in document JSON metadata with normalized records and source anchors. Learning-outcome/topic/assessment tables and parsing belong to Phase 02.
- Job records provide a foundation; ingestion/analysis execution, LLM adapters, recommendations, simulation and reports remain deferred.
- This is local development infrastructure. No real curriculum, workforce evidence, faculty decision, production authentication or deployment is claimed.
- Organiser exemption details, legal access to detailed syllabi, source licensing and academic approval authority remain open in `docs/09_SCOPE_AND_OPEN_QUESTIONS.md`.

## Files created

```text
.github/workflows/backend.yml
PHASE_01_HANDOFF.md
pyproject.toml
compose.yaml
alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/0001_foundation.py
src/shiftos/__init__.py
src/shiftos/main.py
src/shiftos/cli.py
src/shiftos/api/__init__.py
src/shiftos/api/routers/__init__.py
src/shiftos/api/routers/academic.py
src/shiftos/api/routers/health.py
src/shiftos/core/__init__.py
src/shiftos/core/config.py
src/shiftos/core/enums.py
src/shiftos/core/errors.py
src/shiftos/db/__init__.py
src/shiftos/db/base.py
src/shiftos/db/session.py
src/shiftos/models/__init__.py
src/shiftos/models/foundation.py
src/shiftos/schemas/__init__.py
src/shiftos/schemas/academic.py
src/shiftos/schemas/common.py
src/shiftos/schemas/fixtures.py
src/shiftos/services/__init__.py
src/shiftos/services/academic.py
src/shiftos/services/ingestion/__init__.py
src/shiftos/services/ingestion/fixtures.py
tests/conftest.py
tests/test_api.py
tests/test_config.py
tests/test_fixtures.py
tests/test_migrations.py
tests/test_models.py
```

Updated existing files: `.env.example`, `.gitignore`, `README.md`, `STATUS.md`, `docs/02_BACKEND_ARCHITECTURE.md`, `docs/05_API_CONTRACT.md`. Original starter specifications and examples are preserved in Git.
