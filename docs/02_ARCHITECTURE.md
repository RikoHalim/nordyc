# Backend architecture — foundation and future services

## Existing foundation retained

Python 3.12+, FastAPI/Pydantic v2, SQLAlchemy 2, Alembic and PostgreSQL form a modular monolith. HTTP database work uses synchronous sessions/psycopg; request sessions close through a dependency. Injected SQLite databases with foreign keys are for unit/API tests only. PostgreSQL is the runtime/migration target. Exact dependencies and the tested full environment are pinned.

The app factory owns/disposes its engine during lifespan. Startup does not connect or migrate. Liveness needs no database; readiness executes `SELECT 1` and proves connectivity only. Errors retain `{error:{code,message,details}}`; responses expose request IDs without logging secrets/raw documents.

Boundaries remain `api/routers`, `schemas`, `models`, `services`, `core`, `db`. Catalogue/source operations use small services and sessions; the fixture importer stays under ingestion. Introduce provider/repository boundaries where concrete phase needs justify them, without an oversized rewrite of stable services.

`0001_foundation` keeps seven tables; additive `0002` adds source metadata/provenance. Programme revisions retain the snapshot boundary. Docs 03 and 15 explain compatibility and migration safety. The fixture importer validates local synthetic JSON, preserves exact anchors/facts and canonical JSON hashes. It fetches/parses no official document and runs no AI. Identical reruns are idempotent; conflicting IDs/content are refused.

## Future data flow

```text
Selected programme + uploaded curriculum/brochure/syllabus
  -> existing extraction + coverage diagnostics (public discovery secondary)
  -> versioned programme/course catalogue with provenance
  -> internal PostgreSQL MQA / occupations/skills / dated workforce and AI evidence
  -> sufficiency check -> controlled external research only for important gaps
  -> original-source verification + permitted versioned evidence cache
  -> deterministic workforce indicators + one LLM over admitted evidence
  -> conservative whole-programme findings + course review questions
  -> supported primary intervention + alternatives/no change
  -> scenario replay + human review + draft report
```

Phase 2–3 supply curriculum providers and source-specific evidence adapters. Phase 4 extends them with internal evidence retrieval and approved Brave discovery. The current MVP selects Replit-managed `claude-opus-5`; Gemini and cross-provider fallback remain disabled. Replit remains the hosting target. [Phase 4.2](25_PHASE42_LIVE_BACKEND_VERIFICATION.md) verifies the actual HTTP/worker/Claude/PostgreSQL path without changing the academic contract or deploying publicly. Access retains bounded timeouts/retries, terms/robots, lawful reuse and manual fallback. The Phase 1 source registry itself does not fetch or authenticate URLs.

The separate durable worker uses `QUEUED|RUNNING|SUCCEEDED|PARTIAL|FAILED`; it now also processes programme-targeted analysis jobs. Phase 3 external imports retain their separate evidence jobs. The existing institution/revision constraint is not a generic external-research target. Slow HTTP submissions return202/job IDs rather than performing provider work in requests.

## Reproducibility and evidence gates

Future runs reference programme revision, source versions/hashes, dated signal snapshots, assumptions, rule version and model/prompt version if used. Results are immutable; evidence refresh creates a new run. Unrelated source changes should not alter unrelated discipline findings.

Schema and grounding validation constrain output to resolvable scoped sources; application rules enforce eligibility and abstention. No provider/key is required by baseline/offline operation. Configured live model identity is disclosed; synthetic fixtures remain labelled and genuine offline results disclose deterministic insufficiency.

Title-only means unknown taught content and preliminary questions, never definitive obsolete/replacement decisions. Standards are benchmarks; occupation counts are not skill counts; AI exposure is not job-replacement probability.

## Deferred

Expanded verified learning-outcome/assessment ingestion, Phase 5 career alignment/actions, Phase 6 pathways/scenario reports and frontend remain future work. Bounded Phase 4 analysis/research adapters exist; their live acceptance still needs credentials. No microservices, default vector database, knowledge graph, custom training or per-major agents are required.

## Implemented Phase 3 evidence boundary

`services/evidence/registry.py` validates the primary CSV catalogue; the explicit acquisition policy chooses supported endpoints/adapters and access/reuse decisions. `acquisition.py` subclasses the existing bounded HTTP transport with separate data host/type rules, preserving curriculum HTML defaults. `parsers.py` supplies deterministic source-specific CSV/XLSX/JSON transforms and PDF page/table candidates. Pydantic validates normalized records before `repositories/evidence.py` loads immutable version/evidence-linked facts in a per-dataset transaction. `pipeline.py` coordinates those layers and persists independent job/log outcomes. No automatic runtime AI or LLM interpretation is involved.

The local `ingest-evidence` CLI is the administrative worker mechanism; no ingestion HTTP endpoint or startup acquisition is exposed. Read-only evidence routers provide historical observations and full provenance. Original allowed bytes stay in ignored hash-addressed storage, subject to individual source rules. Unavailable/restricted sources remain explicit failures/manual requirements. Synthetic fixtures are separate and require an explicit flag.

Version-local classification relationships prevent accidental joins across editions; unresolved relationships fail atomically. Publication precision, observation periods and UTC retrieval are stored separately. Reviewed cards retain original artifact hashes/locators and review basis; automatic PDF pages remain candidates. The Future Workforce Radar is a deterministic read-only service over frozen observations, with independent AI admission and method/threshold fingerprints. No derived analysis schema is introduced. Protected curriculum PDF upload only stores/queues; the existing separate worker handles bounded layout detection/extraction and atomic document/catalogue/page provenance. The primary workflow is upload-first and public discovery secondary. See [the runbook](17_PHASE3_EVIDENCE_INGESTION.md) and [report](PHASE3_INGESTION_REPORT.md): a bounded prototype evidence baseline is available; broad current coverage/identity/permission gates remain open.

## Implemented bounded Phase 4 hybrid retrieval boundary

The [retrieval contract](19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md) remains the design authority; [the Phase 4 runbook](21_PHASE4_COURSE_RELEVANCE.md) distinguishes implementation from unverified live gates. A small coordinator retrieves PostgreSQL evidence first and applies deterministic relevance, class/review, date, rights and coverage checks. Sufficient local evidence incurs no external request. Important supported gaps invoke the approved Brave adapter only when configured/enabled, within a durable job and finite budgets. Original acquisition/verification uses exact registered artifacts and existing source adapters; unknown/ambiguous originals remain manual/candidate outcomes. Live provider success is not claimed from mocked tests.

Existing evidence repositories/tables, immutable versions, locators and source-class constraints are reused. Additive 0005 adds analysis runs, owned course findings and research metadata cache; existing jobs queue `PROGRAMME_ANALYSIS` for the separate worker. Cache eligibility includes freshness, review and policy hashes; refresh creates a new run. Frozen inputs and final findings publish atomically behind running-job fencing. Failed/blocked research/model processing is observable and yields partial coverage or `insufficient_evidence`, without synthetic substitution.

One selected pretrained model receives bounded admitted evidence; structured quotations, statuses and fixed review questions undergo final schema/citation/scope checks. [Phase 4.1](23_PHASE41_REPLIT_CLAUDE.md) adds a configurable Replit-managed Anthropic Messages adapter, retaining Gemini as the compatible default and an optional explicit fallback for Claude operational failures. Privacy/authentication/schema/citation errors do not trigger cross-provider fallback. Programme totals/insights are application-derived. Existing manifest JSON stores sanitized returned model/token/request/fallback metadata; no schema migration or additional runtime agent is needed. No managed connection/key is configured locally and actual Claude/Gemini/Brave calls remain unverified; the user selected local tests. Workforce arithmetic stays in the deterministic radar; exposure remains separate from observed AI task change.

External search/model egress must respect private upload and content-use policy. Use generic nonprivate search terms, restrict original-source hosts and redirects, retain transport SSRF/robots/size/rate/timeout controls, and treat retrieved instructions as untrusted data. Authorize analysis submission/result access; the catalogue token alone is not production tenant isolation. Research has no public arbitrary-URL trigger and does not run on backend startup. A missing provider, blocked source or unsupported claim remains an explicit limitation in every affected course result.

## Planned Phase 5–6 enhancement integration

[Future Career Alignment and Academic Reskilling Pathways](22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md) extend the existing Academic Decision Studio and Action Plans. Phase 5 consumes frozen Phase 4 evidence to compare programme-supported competencies with reviewed occupation/skill requirements, identify potential gaps and compare minimum sufficient interventions, alternatives/no change and human review. Optional alignment calculations must be deterministic, explained and insufficient when coverage is unknown; they are not employment probabilities.

Phase 6 adds ordered learning steps, supported prerequisites, duration estimates with a basis, verified resources and meaningful SDG links inside scenario/report/action-plan results. Proposed objectives are future intervention plans, not university teaching facts. Seminars/talk attendance cannot establish technical competence; assessed practical work needs actual assessment evidence. Scenarios preserve observed data and version assumptions separately. These remain planning-only; no standalone student platform, runtime module, additional model or Phase 5/6 migration was implemented. Replit hosting and React/TypeScript UI remain future work. Domain 1 substitution approval remains UNCONFIRMED.
