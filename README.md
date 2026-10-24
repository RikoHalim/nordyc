# SHIFT//OS — evidence-led academic workspace

SHIFT//OS helps Malaysian university career centres and academic committees review whole programmes against traceable academic, occupational, workforce and AI evidence. Humans make academic decisions. The pilot catalogue target is **all publicly discoverable XMUM undergraduate programmes**, with deep engine validation on a small set of diverse disciplines first. Other Malaysian institutions will be discovered on demand.

Phase 2 adds bounded XMUM discovery, durable ingestion jobs, reviewed JSON fallback and immutable catalogue snapshots to the existing Phase 1 backend. See [STATUS.md](STATUS.md) for measured results and [the Phase 2 handoff](docs/16_PHASE2_CURRICULUM_INGESTION.md) for commands and source-access limits. In the historical Phase 2 environment, private DNS prevented live discovery; a real PostgreSQL/FastAPI manual-fallback check loaded 25 official directory programme records and 141 course appearances across three diverse programmes. That observation does not certify full curriculum coverage or current live discovery.

## Current foundation

Phase 8 adds the NORDYC React/TypeScript workspace over the Phase 7 protected APIs: programme library/creation, actual PDF and reviewed-input ingestion, course intelligence, career and competency evidence, recommendations, pathways, scenarios, SDG contributions, Action Plans and version-bound review. The design is reconstructed from the original revised NORDYC screenshots; original authored NORDYC source was not recovered. See [the Phase 8 setup, design recovery and controlled Replit preview runbook](docs/30_PHASE8_FRONTEND_REPLIT_MVP.md) and [current measured acceptance](STATUS.md). This is a controlled operator MVP, not public production identity or independent academic validation.

Phase 7 integrates the complete synthetic workflow, adds scoped operator/institution authorization, controlled evaluation/replay, bounded private PDF processing, runtime preflight and Phase 8 API examples. See [the Phase 7 runbook](docs/29_PHASE7_INTEGRATION_EVALUATION_SECURITY.md) for measured results, security boundaries and Replit prerequisites. This is not production or real academic validation.

Phase 6 adds versioned Academic Action Plans: exact Phase 5 lineage, conservative pathways, reviewed resources/workload bases, two hypothetical scenarios, UN target links and append-only review. See [the Phase 6 runbook](docs/28_PHASE6_ACADEMIC_PATHWAYS_ACTION_PLANS.md). No live AI/search request or deployment is implied.

Phase 5 adds protected programme career-alignment jobs, reviewed competency coverage/gap findings, minimum sufficient academic actions and append-only human review. The [Phase 5 methodology and runbook](docs/27_PHASE5_FUTURE_CAREER_ALIGNMENT.md) describe explicit mapping/passage requirements, calculation abstention and the synthetic demonstration. Phase 4.3 remains PARTIAL; no live research admission or real curriculum accuracy is implied.

- FastAPI factory/lifespan, typed settings, request IDs and documented errors.
- PostgreSQL, SQLAlchemy 2, Alembic and UUID/UTC records; SQLite only for unit/API tests.
- Multiple institutions, programmes and versioned course inventories with optional course codes, year, semester and elective status.
- Source registry and provenance links; synthetic and incomplete records stay explicit.
- Paginated create/read catalogue APIs and an idempotent offline fixture CLI.
- Existing document metadata, exact anchors, revision checksums and job records retained.
- Dynamic XMUM undergraduate discovery, conservative title/year/elective parsing, source dates/hashes and coverage/missing-field reporting.
- Separate worker, reviewed structured imports, duplicate checks and safe snapshot re-imports/history.
- Protected programme analysis jobs and history, internal evidence retrieval, Replit-managed `claude-opus-5`, separate Brave discovery, structured citation validation and explicit insufficient-evidence results. The real FastAPI → worker → Claude → PostgreSQL → protected FastAPI workflow passed on two fictional courses. Gemini is disabled for the MVP. [Phase 4.3](docs/26_PHASE43_BRAVE_SEARCH_VERIFICATION.md) verified one live Brave search, while original-source admission remains blocked by exact registration and robots checks. See [Phase 4.2 acceptance](docs/25_PHASE42_LIVE_BACKEND_VERIFICATION.md) and STATUS.md for measured results and evidence limits.

Phase 3 provides registry-driven acquisition, versioned PostgreSQL evidence, controlled PDF extraction and the Future Workforce Radar. Its recorded real-source imports contain **38 legacy ESCO occupations, 10 English-described skills, 39 relationships, 12 MQA benchmark summaries, 186 official SDG references, 247 workforce observations and 20 AI cards**, plus 76 unreviewed PDF page references. Phase 4 adds bounded evidence-grounded screening; [its runbook](docs/21_PHASE4_COURSE_RELEVANCE.md) and the Phase 4.2 record distinguish live backend acceptance from academic validation and partial Brave research. Legacy/language/currentness/identity/permission limits remain. See also [Phase 3 ingestion](docs/17_PHASE3_EVIDENCE_INGESTION.md), [measured evidence](docs/PHASE3_INGESTION_REPORT.md) and [workforce methodology](docs/18_WORKFORCE_TRENDS.md). Phase 5 provides evidence-bound action proposals; Phase 6 adds pathways/scenarios/action plans; Phase 7 adds integration/security controls; Phase 8 supplies the controlled React workspace. Replit preview acceptance and public-release readiness are separate decisions recorded in STATUS.

## Revised product contract

The primary journey is **select programme → upload available curriculum/brochure or syllabus documents → review extraction → analyse every available course**. Detailed syllabi are optional; public discovery remains secondary. Phase 3 implements the upload/extraction portion, with explicit year columns or reviewed-region fallback and unreviewed title candidates; analysis is Phase 4. A title proves no taught content, so later outputs must preserve `needs_syllabus_confirmation` where appropriate.

The implemented career-alignment and Action Plan workflows propose evidence-bound academic interventions, alternatives including no change, or requests for more evidence and review. Staff retain academic decision authority; recorded operator consideration does not automatically modify curricula or establish named committee approval. Budget/time constraints are optional at later comparison. Recommendations need admissible citations or `insufficient_evidence`; benchmarks are not XMUM teaching facts.

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

Set `POSTGRES_PASSWORD` in `.env` and its URL-encoded equivalent in `DATABASE_URL`. The template supplies no password; changing port/database/user also requires updating the URL. Shell variables override `.env`. Baseline/offline operation needs no AI key; [live Phase 4](docs/21_PHASE4_COURSE_RELEVANCE.md) separately requires a configured model provider and approved use. [Phase 4.1](docs/23_PHASE41_REPLIT_CLAUDE.md) adds managed Claude; local cloning does not provision a Replit connection. Brave research is configured independently. Dependencies are fixed in `pyproject.toml` and the tested environment is recorded in `requirements.lock`.

```powershell
docker compose up -d --wait
python -m alembic upgrade head
python -m shiftos.cli import-fixture examples/sample_programme.json
uvicorn shiftos.main:app --reload --app-dir src
```

Open [Swagger UI](http://127.0.0.1:8000/docs) or [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). `/health` and `/health/live` are liveness routes; `/health/ready` checks connectivity and returns structured 503 when unavailable. Production readiness additionally requires a valid scoped access policy and the expected Alembic head. These checks do not certify academic coverage, worker availability or production operations.

The original fixture contains 12 invented courses, two electives and six without detailed syllabi. Identical re-import returns `created: false`; conflicting content under existing revision/record IDs is rejected. The command reads local JSON and makes no external calls. `examples/` remains the executable Phase 1 fixture format. New cross-disciplinary `fixtures/` describe later acceptance cases and cannot be passed directly to this importer.

## Existing database upgrade

Back up the configured database and confirm the intended environment. Keep original migrations unchanged; `python -m alembic upgrade head` applies additive `0002`–`0007`. They preserve original tables, IDs, fixture hashes and anchors while adding provenance, curriculum jobs, reference evidence, programme analysis, career/review and Action Plan/history tables. Existing rows receive safe defaults, not invented provenance. Downgrade refuses loss of populated added metadata and immutable history; see [the data model](docs/03_DATA_MODEL.md).

## Curriculum discovery and imports

Read the [Phase 2 runbook](docs/16_PHASE2_CURRICULUM_INGESTION.md) before live acquisition. Both discovery flags default false. After recording publisher access/terms review, enable them in the worker environment, queue `POST /api/v1/catalogue/discover` with `{"provider":"xmum"}`, and run `python -m shiftos.cli worker`. Poll `/api/v1/catalogue/jobs/{id}` and inspect each programme's `/coverage`. Failed pages retain existing snapshots and expose manual fallback.

For verified files, `python -m shiftos.cli import-curriculum path/to/reviewed.json --institution <UUID>` queues the same persistence path; `python -m shiftos.cli worker --once` processes the next eligible job. [The clearly synthetic example](examples/curriculum_import.synthetic.json) works offline with a matching synthetic institution. Real imports require official URLs, actual retrieval dates, locators and title excerpts. No syllabus is invented. Controlled preview and production HTTP access require scoped bearer grants with explicit institution and operation permissions. `CATALOGUE_WRITE_TOKEN` remains a legacy local-development boundary; it cannot replace the production scoped policy or a future production identity service.

## Development checks

Upload-first catalogue ingestion is explicit and uses the existing worker:

```powershell
python -m shiftos.cli upload-curriculum-pdf path/to/brochure.pdf --programme <UUID>
python -m shiftos.cli worker --once
```

The protected HTTP equivalent is `POST /api/v1/programmes/{id}/curriculum-pdf` with an `application/pdf` body. Supported labelled year-column brochures can be detected automatically; unsupported/scanned layouts need explicit regions or reviewed JSON. Private originals are retained separately from unreviewed course candidates. This performs no course relevance analysis.

Phase 3 administration is explicit, outside HTTP requests:

```powershell
python -m shiftos.cli ingest-evidence --dataset D-JMI-Q1-2026 --dataset D-JMI-Q2-2026 --live --report data/local/workforce-report.json
```

Per-source access/rights gates still apply. Without `--live`, acquisition remains disabled; permitted manual files and explicitly synthetic offline fixtures are supported. See the Phase 3 runbook for commands, formats, provenance, restricted sources and brochure review.

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
| `docs/17_PHASE3_EVIDENCE_INGESTION.md`, `docs/PHASE3_INGESTION_REPORT.md` | Evidence ETL, manual procedures, measured counts and readiness blockers |
| `docs/18_WORKFORCE_TRENDS.md`, `data/reference_packs/README.md` | Demand/AI separation, reproducible calculations and permitted frozen real subsets |
| `docs/19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md` | Planned PostgreSQL-first retrieval, controlled research fallback, verification/cache and single-model analysis |
| `docs/21_PHASE4_COURSE_RELEVANCE.md` | Implemented analysis jobs/APIs, academic evidence rules, offline operation and historical provider configuration |
| `docs/22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md` | Planned Phase 5 career alignment and Phase 6 academic pathways/Action Plans; unresolved Domain 1 substitutions |
| `docs/23_PHASE41_REPLIT_CLAUDE.md` | Managed Claude configuration, structured-output contract and historical diagnostics |
| `docs/25_PHASE42_LIVE_BACKEND_VERIFICATION.md` | Historical successful live Claude worker/PostgreSQL/FastAPI proof on fictional courses |
| `docs/26_PHASE43_BRAVE_SEARCH_VERIFICATION.md` | Live Brave transport proof and remaining original-source admission gate |
| `docs/27_PHASE5_FUTURE_CAREER_ALIGNMENT.md`, `docs/28_PHASE6_ACADEMIC_PATHWAYS_ACTION_PLANS.md` | Implemented alignment, recommendations, pathways, scenarios and immutable review |
| `docs/29_PHASE7_INTEGRATION_EVALUATION_SECURITY.md`, `docs/30_PHASE8_FRONTEND_REPLIT_MVP.md` | Integration/security acceptance, frontend setup, design reconstruction and controlled-preview/public-release boundaries |
| `docs/DATASET_RESEARCH.md`, `data/dataset_registry.csv` | Verified research and acquisition candidates |
| `examples/` | Preserved executable synthetic fixtures |
| `fixtures/`, `references/` | Later acceptance cases and candidate sources |
| `prompts/` | One-phase instructions; legacy filenames redirect |

### Historical Phase 4 handoff (superseded by current STATUS)

The original Phase 4.1 handoff recorded **756 passing tests**, including 13 PostgreSQL cases, before live provider verification. Those are historical counts, not the current baseline. Phase 4.2 subsequently verified the real managed Claude → PostgreSQL → protected FastAPI workflow on two fictional courses. Phase 5–8 were separately authorised and implemented; current automated and browser measurements are in [STATUS](STATUS.md). Gemini remains disabled, Brave original-source admission remains **PARTIAL**, and synthetic/mocked software acceptance does not establish real academic accuracy. Public release and institutional substitution for individual workflows remain separate unresolved gates; see [the roadmap](docs/12_MVP_ROADMAP.md).


## Scoped backend operation

Legacy API access is for trusted loopback development only. Production refuses legacy access; Replit preview and `scripts/run_backend.py` require a valid scoped operator policy. Configure `API_ACCESS_MODE=scoped` and private `API_ACCESS_POLICY_PATH` using the intentionally invalid [template](examples/access-policy.template.json), with locally generated bearer credentials, token hashes, explicit institutions and read/write/review/admin grants. This is not named academic identity or production SSO. Do not publish the private policy or credential.

Run from the project root after configuring the intended database:

```powershell
python -m shiftos.cli runtime-preflight
# Explicit read of the selected database; never performs migrations/model calls:
python -m shiftos.cli runtime-preflight --check-database --component api
python -m shiftos.cli runtime-preflight --check-database --component worker
# Apply migrations separately only after confirming an owned development DB:
python -m alembic upgrade head
python scripts/run_backend.py
# In a separately supervised process with the same DB/policy/private storage:
python -m shiftos.cli worker
```

Managed `postgresql://`/`postgres://` URLs normalize to the existing psycopg3 driver. No database is provisioned or copied by ordinary startup. External processing, research and Gemini remain disabled by default. The API launcher performs no automatic migration or worker start; local legacy development can continue with loopback `uvicorn` as above. Review [the integration/evaluation commands and deployment gates](docs/29_PHASE7_INTEGRATION_EVALUATION_SECURITY.md), then use [the Phase 8 frontend and explicit synthetic-preview procedure](docs/30_PHASE8_FRONTEND_REPLIT_MVP.md). The commands above start backend components only; they do not publish a public application or establish Replit preview acceptance.
