# SHIFT//OS — academic decision-support backend

SHIFT//OS helps Malaysian university career centres and academic committees review whole programmes against traceable academic, occupational, workforce and AI evidence. Humans make academic decisions. The pilot catalogue target is **all publicly discoverable XMUM undergraduate programmes**, with deep engine validation on a small set of diverse disciplines first. Other Malaysian institutions will be discovered on demand.

This repository preserves the existing Phase 1 implementation and Git history and adapts its foundation to revised requirements. It is not an empty starter or a completed analysis platform. See [STATUS.md](STATUS.md) for actual verification results and [the migration audit](docs/15_PHASE1_MIGRATION_AUDIT.md) for preserved, changed and deferred work. No real XMUM catalogue has been collected by this phase.

## Current foundation

- FastAPI factory/lifespan, typed settings, request IDs and documented errors.
- PostgreSQL, SQLAlchemy 2, Alembic and UUID/UTC records; SQLite only for unit/API tests.
- Multiple institutions, programmes and versioned course inventories with optional course codes, year, semester and elective status.
- Source registry and provenance links; synthetic and incomplete records stay explicit.
- Paginated create/read catalogue APIs and an idempotent offline fixture CLI.
- Existing document metadata, exact anchors, revision checksums and job records retained.

Discovery, source fetching, parsing, workforce/AI imports, analysis, recommendations, scenarios, reports and frontend remain future phases. Source registration records supplied metadata and performs no external verification. A supplied verification assertion is not independent automated verification.

## Revised product contract

University name and programme selection are minimal inputs. Public course titles are required where available; year/elective information is retained when shown and **detailed syllabi are optional**. Individual-course analysis is a drill-down from programme review. A title proves no taught content: future outputs must use preliminary questions and `needs_syllabus_confirmation` where appropriate.

Future analysis proposes no change, syllabus revision, evidence-gated redesign/consolidation, new courses/electives, workshops and industry engagement, or request review. Staff compare alternatives including no change and approve decisions. Budget/time constraints are optional at later comparison. Recommendations need admissible citations or `insufficient_evidence`; benchmarks are not XMUM teaching facts.

The preliminary round needs a key-capability proof, proposal and accessible GitHub repository. The original final brief has six must-haves. Institutional framing and CV-upload exemption are reportedly accepted; other waivers remain **UNCONFIRMED** in [the compliance matrix](docs/09_HACKATHON_COMPLIANCE.md).

## Local setup

Use **Python 3.12+**, PowerShell and Docker Compose v2. Run from this repository:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e '.[dev]'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set `POSTGRES_PASSWORD` in `.env` and its URL-encoded equivalent in `DATABASE_URL`. The template supplies no password; changing port/database/user also requires updating the URL. Shell variables override `.env`. No AI/API key is needed. Dependencies are fixed in `pyproject.toml` and the full tested environment is recorded in `requirements.lock`.

```powershell
docker compose up -d --wait
python -m alembic upgrade head
python -m shiftos.cli import-fixture examples/sample_programme.json
uvicorn shiftos.main:app --reload --app-dir src
```

Open [Swagger UI](http://127.0.0.1:8000/docs) or [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). `/health` and `/health/live` are liveness routes; `/health/ready` checks connectivity and returns structured 503 when unavailable. Readiness does not certify migrations.

The original fixture contains 12 invented courses, two electives and six without detailed syllabi. Identical re-import returns `created: false`; conflicting content under existing revision/record IDs is rejected. The command reads local JSON and makes no external calls. `examples/` remains the executable Phase 1 fixture format. New cross-disciplinary `fixtures/` describe later acceptance cases and cannot be passed directly to this importer.

## Existing database upgrade

Back up the configured database and confirm the intended environment. Keep `0001_foundation` unchanged; apply additive `0002` with `python -m alembic upgrade head`. It adds source/provenance metadata without replacing the original seven tables or course/revision IDs. Existing rows gain nullable metadata and `is_verified: false`, not invented provenance. Fixture hashes and anchors remain intact. Downgrade refuses loss of populated added metadata; see [the data model](docs/03_DATA_MODEL.md) and audit.

## Development checks

```powershell
python -m pytest -q --basetemp=.pytest-tmp
python -m ruff check .
python -m ruff format --check .
python -m alembic upgrade head --sql
```

Unit/API tests use isolated SQLite databases and synthetic fixtures. Offline SQL generation does not prove a live PostgreSQL migration. To opt in to integration testing, replace the password placeholder and use an account permitted to create schemas:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://shiftos:<URL_ENCODED_PASSWORD>@localhost:5432/shiftos'
python -m pytest -q -m integration --basetemp=.pytest-tmp
Remove-Item Env:TEST_DATABASE_URL
```

Tests use randomly named `shiftos_test_*` schemas and clean them up; they do not migrate the application's existing schema. Current measured results and environmental limits are in STATUS.

## Documentation and next phase

| Path | Purpose |
|---|---|
| `AGENTS.md`, `CODEX_START.md` | Guardrails and continuation instructions |
| `PHASE_01_HANDOFF.md` | Foundation handoff and migration boundary |
| `docs/00_READ_ME_FIRST.md` | Revised requirements authority |
| `docs/03_DATA_MODEL.md`, `docs/10_API_CONTRACT.md` | Implemented schema/APIs vs future targets |
| `docs/12_MVP_ROADMAP.md` | Preliminary, final and post-hackathon priorities |
| `docs/15_PHASE1_MIGRATION_AUDIT.md` | Phase 1 compatibility review |
| `examples/` | Preserved executable synthetic fixtures |
| `fixtures/`, `references/` | Later acceptance cases and candidate sources |
| `prompts/` | One-phase instructions; legacy filenames redirect |

Continue with [Phase 2 discovery](prompts/02_CURRICULUM_DISCOVERY.md) only when explicitly requested. Do not commit or push automatically.
