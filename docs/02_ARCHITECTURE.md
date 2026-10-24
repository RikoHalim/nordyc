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

Phase 2–3 already supply curriculum providers and source-specific evidence adapters. Extend those boundaries for internal evidence retrieval, approved external search and one configured LLM when Phase 4 is authorized; do not replace the implemented pipeline with hypothetical interfaces. Access needs bounded timeouts/retries, terms/robots, lawful reuse and manual fallback. The Phase 1 source registry itself does not fetch or authenticate URLs.

Phase 2 implements the separate durable catalogue worker and job states (`QUEUED|RUNNING|SUCCEEDED|PARTIAL|FAILED`). Phase 3 evidence imports use separate import jobs. Extend an appropriate worker/job boundary for Phase 4; the current curriculum target constraint is not a generic research queue. Slow activities should return 202/job IDs rather than block requests.

## Reproducibility and evidence gates

Future runs reference programme revision, source versions/hashes, dated signal snapshots, assumptions, rule version and model/prompt version if used. Results are immutable; evidence refresh creates a new run. Unrelated source changes should not alter unrelated discipline findings.

Schema and grounding validation must constrain LLM output to resolvable sources; application rules enforce evidence/action eligibility and abstention. No provider/key is required by Phase 1. Any future model is disclosed; offline output remains synthetic.

Title-only means unknown taught content and preliminary questions, never definitive obsolete/replacement decisions. Standards are benchmarks; occupation counts are not skill counts; AI exposure is not job-replacement probability.

## Deferred

Learning-outcome/topic/assessment tables, analysis/actions/reports, automatic research fallback and frontend remain future work. No microservices, default vector database, knowledge graph, custom training or per-major agents are required.

## Implemented Phase 3 evidence boundary

`services/evidence/registry.py` validates the primary CSV catalogue; the explicit acquisition policy chooses supported endpoints/adapters and access/reuse decisions. `acquisition.py` subclasses the existing bounded HTTP transport with separate data host/type rules, preserving curriculum HTML defaults. `parsers.py` supplies deterministic source-specific CSV/XLSX/JSON transforms and PDF page/table candidates. Pydantic validates normalized records before `repositories/evidence.py` loads immutable version/evidence-linked facts in a per-dataset transaction. `pipeline.py` coordinates those layers and persists independent job/log outcomes. No automatic runtime AI or LLM interpretation is involved.

The local `ingest-evidence` CLI is the administrative worker mechanism; no ingestion HTTP endpoint or startup acquisition is exposed. Read-only evidence routers provide historical observations and full provenance. Original allowed bytes stay in ignored hash-addressed storage, subject to individual source rules. Unavailable/restricted sources remain explicit failures/manual requirements. Synthetic fixtures are separate and require an explicit flag.

Version-local classification relationships prevent accidental joins across editions; unresolved relationships fail atomically. Publication precision, observation periods and UTC retrieval are stored separately. Reviewed cards retain original artifact hashes/locators and review basis; automatic PDF pages remain candidates. The Future Workforce Radar is a deterministic read-only service over frozen observations, with independent AI admission and method/threshold fingerprints. No derived analysis schema is introduced. Protected curriculum PDF upload only stores/queues; the existing separate worker handles bounded layout detection/extraction and atomic document/catalogue/page provenance. The primary workflow is upload-first and public discovery secondary. See [the runbook](17_PHASE3_EVIDENCE_INGESTION.md) and [report](PHASE3_INGESTION_REPORT.md): a bounded prototype evidence baseline is available; broad current coverage/identity/permission gates remain open.

## Planned Phase 4 hybrid retrieval boundary

The [Phase 4 retrieval contract](19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md) is the design authority for this extension; none of its new components is implemented by this documentation revision. A small coordinator retrieves PostgreSQL evidence first and applies deterministic claim-specific relevance, quality, date/edition, rights and coverage gates. Sufficient local evidence incurs no external request. Important gaps automatically invoke an approved, configured search adapter within a durable job and finite budgets. Source-specific original acquisition and verification remain separate from search discovery; only supported, permitted findings can be imported and reused.

Reuse the evidence repository/tables, immutable versions, exact locators and source-class constraints. Add minimal analysis/finding and research-attempt/cache persistence only in the authorized implementation, with additive migrations/tests. Cache eligibility includes freshness, review, source-policy and rights versions; refresh produces a new run and does not rewrite a frozen manifest. Failed/blocked research is observable and yields partial coverage or `insufficient_evidence`, without synthetic substitution.

One disclosed existing model receives the bounded admitted evidence packet and produces schema-validated, citation-checked explanations. A runtime LLM connection/provider/model is currently absent and must be explicitly configured during implementation. No extra model, training or tool-using research agent is required. Workforce arithmetic stays in the existing deterministic radar, and exposure stays separate from observed AI task change.

External search/model egress must respect private upload and content-use policy. Use generic nonprivate search terms, restrict original-source hosts and redirects, retain transport SSRF/robots/size/rate/timeout controls, and treat retrieved instructions as untrusted data. Authorize analysis submission/result access; the catalogue token alone is not production tenant isolation. Research has no public arbitrary-URL trigger and does not run on backend startup. A missing provider, blocked source or unsupported claim remains an explicit limitation in every affected course result.
