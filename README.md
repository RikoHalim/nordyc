# SHIFT//OS — academic decision-support backend

SHIFT//OS helps Malaysian university career centres and academic committees review whole programmes against traceable academic, occupational, workforce and AI evidence. Humans make academic decisions. The pilot catalogue target is **all publicly discoverable XMUM undergraduate programmes**, with deep engine validation on a small set of diverse disciplines first. Other Malaysian institutions will be discovered on demand.

Phase 2 adds bounded XMUM discovery, durable ingestion jobs, reviewed JSON fallback and immutable catalogue snapshots to the existing Phase 1 backend. See [STATUS.md](STATUS.md) for measured results and [the Phase 2 handoff](docs/16_PHASE2_CURRICULUM_INGESTION.md) for commands and source-access limits. Live discovery was refused by this environment's private DNS; a real PostgreSQL/FastAPI manual-fallback check loaded 25 official directory programme records and 141 course appearances across three diverse programmes. This does not certify full curriculum coverage.

## Current foundation

- FastAPI factory/lifespan, typed settings, request IDs and documented errors.
- PostgreSQL, SQLAlchemy 2, Alembic and UUID/UTC records; SQLite only for unit/API tests.
- Multiple institutions, programmes and versioned course inventories with optional course codes, year, semester and elective status.
- Source registry and provenance links; synthetic and incomplete records stay explicit.
- Paginated create/read catalogue APIs and an idempotent offline fixture CLI.
- Existing document metadata, exact anchors, revision checksums and job records retained.
- Dynamic XMUM undergraduate discovery, conservative title/year/elective parsing, source dates/hashes and coverage/missing-field reporting.
- Separate worker, reviewed structured imports, duplicate checks and safe snapshot re-imports/history.

Workforce/academic/AI reference imports, analysis, recommendations, scenarios, reports and frontend remain future phases. Source registration and reviewed-file flags are supplied assertions; they do not independently verify actual teaching content.

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

Back up the configured database and confirm the intended environment. Keep original migrations unchanged; `python -m alembic upgrade head` applies additive `0002` and `0003`. They preserve original tables, IDs, fixture hashes and anchors while adding provenance, import metadata and institution-scoped jobs. Existing rows receive safe defaults, not invented provenance. Downgrade refuses loss of populated added metadata; see [the data model](docs/03_DATA_MODEL.md).

## Curriculum discovery and imports

Read the [Phase 2 runbook](docs/16_PHASE2_CURRICULUM_INGESTION.md) before live acquisition. Both discovery flags default false. After recording publisher access/terms review, enable them in the worker environment, queue `POST /api/v1/catalogue/discover` with `{"provider":"xmum"}`, and run `python -m shiftos.cli worker`. Poll `/api/v1/catalogue/jobs/{id}` and inspect each programme's `/coverage`. Failed pages retain existing snapshots and expose manual fallback.

For verified files, `python -m shiftos.cli import-curriculum path/to/reviewed.json --institution <UUID>` queues the same persistence path; `python -m shiftos.cli worker --once` processes the next eligible job. [The clearly synthetic example](examples/curriculum_import.synthetic.json) works offline with a matching synthetic institution. Real imports require official URLs, actual retrieval dates, locators and title excerpts. No syllabus is invented. In production configure a nonempty `CATALOGUE_WRITE_TOKEN` for new HTTP job submissions; this is not full deployment authentication.

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
| `docs/16_PHASE2_CURRICULUM_INGESTION.md` | Discovery, structured import, worker and actual coverage handoff |
| `docs/DATASET_RESEARCH.md`, `data/dataset_registry.csv` | Verified research and acquisition candidates |
| `examples/` | Preserved executable synthetic fixtures |
| `fixtures/`, `references/` | Later acceptance cases and candidate sources |
| `prompts/` | One-phase instructions; legacy filenames redirect |

Phase 2 stops here. The user subsequently authorised merging `feature/phase-2-curriculum-ingestion` into `main` and synchronising the local checkout. The next recommended development task is Phase 3 reference evidence ingestion, guided by the completed dataset research; start only when explicitly requested. See STATUS for the merge verification and remaining source-access limits.
