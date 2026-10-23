# Backend architecture — foundation and future services

## Existing foundation retained

Python 3.12+, FastAPI/Pydantic v2, SQLAlchemy 2, Alembic and PostgreSQL form a modular monolith. HTTP database work uses synchronous sessions/psycopg; request sessions close through a dependency. Injected SQLite databases with foreign keys are for unit/API tests only. PostgreSQL is the runtime/migration target. Exact dependencies and the tested full environment are pinned.

The app factory owns/disposes its engine during lifespan. Startup does not connect or migrate. Liveness needs no database; readiness executes `SELECT 1` and proves connectivity only. Errors retain `{error:{code,message,details}}`; responses expose request IDs without logging secrets/raw documents.

Boundaries remain `api/routers`, `schemas`, `models`, `services`, `core`, `db`. Catalogue/source operations use small services and sessions; the fixture importer stays under ingestion. Introduce provider/repository boundaries where concrete phase needs justify them, without an oversized rewrite of stable services.

`0001_foundation` keeps seven tables; additive `0002` adds source metadata/provenance. Programme revisions retain the snapshot boundary. Docs 03 and 15 explain compatibility and migration safety. The fixture importer validates local synthetic JSON, preserves exact anchors/facts and canonical JSON hashes. It fetches/parses no official document and runs no AI. Identical reruns are idempotent; conflicting IDs/content are refused.

## Future data flow

```text
Official programme directory/pages + optional CSV/documents
  -> bounded discovery/extraction + coverage diagnostics
  -> versioned programme/course catalogue with provenance
  -> MQA / occupations/skills / dated workforce and AI evidence
  -> conservative whole-programme findings + course review questions
  -> supported primary intervention + alternatives/no change
  -> scenario replay + human review + draft report
```

Add `CurriculumSource`, `StandardsSource`, `WorkforceSignalSource`, `AIImpactSource` and optional `LLMExtractor` in their phases, with offline adapters. Access needs bounded timeouts/retries, terms/robots, lawful reuse and manual fallback. The Phase 1 source registry does not fetch or authenticate URLs.

Reuse jobs (`QUEUED|RUNNING|SUCCEEDED|PARTIAL|FAILED`) and choose a simple durable worker in Phase 2. Existing jobs are storage, not an execution queue. Slow activities should return 202/job IDs rather than block requests.

## Reproducibility and evidence gates

Future runs reference programme revision, source versions/hashes, dated signal snapshots, assumptions, rule version and model/prompt version if used. Results are immutable; evidence refresh creates a new run. Unrelated source changes should not alter unrelated discipline findings.

Schema and grounding validation must constrain LLM output to resolvable sources; application rules enforce evidence/action eligibility and abstention. No provider/key is required by Phase 1. Any future model is disclosed; offline output remains synthetic.

Title-only means unknown taught content and preliminary questions, never definitive obsolete/replacement decisions. Standards are benchmarks; occupation counts are not skill counts; AI exposure is not job-replacement probability.

## Deferred

Parsing, learning-outcome/topic/assessment tables, evidence passages/snapshots, workers, analysis/actions/reports and frontend remain future work. No microservices, default vector database, knowledge graph, custom training or per-major agents are required.
