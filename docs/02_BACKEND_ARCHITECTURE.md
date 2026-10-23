# 02 — Backend Architecture

## Architectural shape

**Modular monolith** with FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, and isolated services. Do NOT start with microservices, vector databases, agents or event buses.

```text
POST /programmes/{id}/documents
             |
      Ingestion service
             |  extracted text + page/paragraph anchors
      Course inventory and syllabus facts
             |
  Evidence pipeline <--- CSV/JSON import of dated, attributed sources
             |
      Relevance analysis service
       | course-level findings and programme-wide gaps
       v
      Recommendation service
       | primary action + alternatives + safeguards
       v
    Scenario/report service
       | JSON + review state / export later
       v
       FastAPI endpoints
```

## Suggested code boundaries

```text
src/shiftos/
  main.py                 # ASGI app, router mounts, lifespan
  api/routers/            # HTTP-only logic; Pydantic request/response
  core/config.py          # Pydantic Settings / env config
  core/enums.py           # Status/action/evidence enums
  db/base.py              # SQLAlchemy metadata/base
  db/session.py           # Engine, session factory, dependency
  models/                 # SQLAlchemy persistence
  schemas/                # Pydantic DTOs, LLM contracts
  services/ingestion/     # PDF/DOCX extraction and source anchors
  services/evidence/      # source registries, dated snapshots, import, crosswalk
  services/analysis/      # interpretation and evidence sufficiency
  services/recommendations/  # decision guards / alternatives
  services/scenarios/     # uncertainty comparison, replay
  services/reports/       # academic report JSON representation
  llm/                    # provider interface; offline demo and optional real adapter
alembic/                  # schema migrations
tests/                     # unit, API, integration, contract
```

## Technology and dependency policy

- Python >= 3.11; modern stable package versions, consistent `pyproject.toml`.
- Web: FastAPI, Uvicorn, Pydantic v2, pydantic-settings.
- Persistence: SQLAlchemy 2, psycopg (PostgreSQL), Alembic.
- Documents: PyMuPDF + python-docx. Digital text only initially; scanned PDF -> explicit `NEEDS_OCR` review, no automatic OCR.
- Quality: pytest, httpx, Ruff. Use Black only if chosen consistently; avoid overlapping formatter conflict.
- Task execution: start with a **synchronous testable service function**, expose job records/status through API. For expensive jobs, add a simple worker in a later phase; don't hold a production HTTP connection for multi-document analysis. Test service logic without background infrastructure.
- AI model: an adapter (structured input/output); provider implementation optional until Phase 04. Configure via environment variables and redact secrets. A personal chat subscription does **not** guarantee API credits.

## Error handling and observability

- Errors: stable JSON `{ "error": {"code": "...", "message": "...", "details": [...] } }`.
- Jobs/runs record status `QUEUED|RUNNING|SUCCEEDED|PARTIAL|FAILED`, error summary and timestamps.
- Idempotency: repeated ingestion of identical file SHA-256 and parser version should not silently duplicate content; each revision is traceable.
- Structured logs with IDs and timings, no uploaded document text/API keys in logs.
- Use UTC in storage and ISO-8601 in API.

## Versioned analysis inputs

Every analysis references: programme revision, course/document revisions, signal snapshot IDs, analysis algorithm version, prompt/model version (if used), scenario ID, generated timestamp. Results are immutable run snapshots; re-run instead of silently overwriting.

## Failure modes worth engineering for

- Missing detailed syllabus: include course in inventory, emit `INSUFFICIENT_EVIDENCE` for unsupported conclusions.
- Multi-course PDF extraction ambiguity: preserve original passages, flag `NEEDS_REVIEW`.
- Poorly ordered PDF text: preserve page text, no pretend-perfect structural extraction.
- Stale/inadequate labour evidence: qualified unknown, not generic claims of obsolete skills.
- LLM hallucinated source: reject if not in supplied source registry / passages.
- Updated evidence: comparison to prior run, not retroactive mutation.

## Phase 01 implementation decisions

The foundation uses synchronous SQLAlchemy 2 `Session` objects and the psycopg PostgreSQL driver throughout HTTP services, fixture imports and Alembic. Database routes are synchronous FastAPI handlers. Each HTTP request receives its own session, which closes after the dependency yields; service functions commit resource creation, while the fixture command owns its import transaction. The application factory exposes injectable settings/database dependencies for tests and disposes an engine it owns during lifespan shutdown. App startup does not open a database connection or run migrations automatically.

PostgreSQL is the supported development and runtime database. `compose.yaml` provides a PostgreSQL 16 development service bound to `127.0.0.1`, requires a locally supplied `POSTGRES_PASSWORD`, and persists data in a named volume. Pydantic Settings reads the connection URL as a secret. SQLite URLs are allowed only with `APP_ENV=test`; in-memory SQLite is used for deterministic unit/API tests, with foreign-key checks enabled. A UTC SQLAlchemy type rejects naive timestamp writes and restores the UTC offset on SQLite reads. PostgreSQL columns use `TIMESTAMP WITH TIME ZONE`.

The initial migration contains exactly seven application tables: `institutions`, `programmes`, `programme_revisions`, `courses`, `documents`, `document_anchors` and `jobs`. UUID identifiers and `created_at`, `updated_at`, `is_synthetic` fields apply to all seven. Programme revisions preserve version labels and optional fixture identity/checksum metadata. A composite foreign key restricts a programme's active revision to its own revisions; another restricts a document's optional course link to the same revision. Course-code indexes support programme-wide inventory queries; course codes deliberately are not unique, so duplicate-code records can remain visible for later review. No delete cascades erase the source history.

`jobs` supplies revision linkage, kind, `QUEUED|RUNNING|SUCCEEDED|PARTIAL|FAILED` status, times and an optional error. Phase 01 has no job execution endpoints or worker. Analysis-specific runs, source snapshots and result tables will be introduced in their requested phases rather than treating the job foundation as a completed analysis engine.

The offline importer accepts validated, explicitly synthetic JSON fixtures. It preserves source identity, document kinds/statuses, exact anchor excerpts and locations, course inventory, syllabus-availability flags and the original normalized fixture facts. `documents.metadata_json` stores the fixture disclaimer, document metadata and anchored fact payloads; programme-structure document metadata also contains the complete normalized fixture. Fixture and document checksums describe canonical JSON content, not bytes parsed from an official PDF/DOCX. An identical rerun is idempotent; incompatible content under existing IDs is rejected instead of silently rewriting a revision.

Separate learning-outcome, topic and assessment tables are deferred to Phase 02 ingestion. `NORMALIZED_FIXTURE` marks supplied synthetic syllabus detail; `INVENTORY_ONLY` marks a course without such detail. Neither status is an academic relevance verdict. Parsing, evidence fetching, LLM/provider integration, relevance decisions, recommendations, scenarios and reports remain deferred. The Phase 01 application needs no API key and makes no AI calls.

Institution/programme listings and all courses in a programme's active revision use UUID-ordered offset pagination. The default page size is 50 and the maximum is 100; every programme course remains retrievable across pages. Readiness performs `SELECT 1` and reports connectivity only. Alembic must run explicitly before importing fixtures or calling persistence endpoints. The opt-in PostgreSQL migration test uses a temporary isolated schema; SQLite tests and offline SQL generation are not substitutes for that test.
