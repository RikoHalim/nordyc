# Phase 4 course relevance — operation and validation

Implemented as a bounded backend extension on **24 October 2026**. [Phase 4.2 live backend acceptance](25_PHASE42_LIVE_BACKEND_VERIFICATION.md) passes using Replit-managed `claude-opus-5`, two fictional courses and one permitted public ESCO excerpt. [Phase 4.3](26_PHASE43_BRAVE_SEARCH_VERIFICATION.md) passed one real Brave search; original-source admission remains blocked, so research acceptance is PARTIAL. Gemini is discontinued for this MVP and disabled. [STATUS](../STATUS.md) distinguishes actual live acceptance from offline/mocked tests and evidence limitations. Phase 5 recommendations, Phase 6 pathways/scenarios, frontend and deployment remain unimplemented.

## Stack and retained boundaries

Python/FastAPI, PostgreSQL, SQLAlchemy and Alembic remain the runtime stack. [Phase 4.1](23_PHASE41_REPLIT_CLAUDE.md) supplies the Replit-managed Claude Messages adapter through the existing `httpx` dependency. Brave Search remains independent. The legacy Gemini adapter is retained for compatibility, with its enable and fallback gates false. Managed credentials stay inside Replit. No training, embeddings service or research-agent platform is introduced. React/TypeScript remains a future frontend target; no public deployment has occurred.

Existing curriculum extraction, catalogue APIs, evidence ETL, workforce radar, source classes and historical versions are retained. The normal separate worker now also handles `PROGRAMME_ANALYSIS`. No acquisition or model call runs at application startup or in an HTTP request handler.

## Fresh-computer setup

Clone the repository and follow the [README setup](../README.md#local-setup). Install the pinned environment and apply migrations with `python -m alembic upgrade head` to the intended backed-up/new PostgreSQL database. Do not copy a prior developer's `.env`, private downloads or local database into Git. Migration `0005_programme_analysis` adds only `analysis_runs`, `course_findings` and `research_cache`; populated downgrade is refused.

Git includes attributed permitted ESCO/UN frozen subsets and explicitly synthetic fixtures, not the complete local research database. Use the [Phase 3 runbook](17_PHASE3_EVIDENCE_INGESTION.md) and [reference-pack instructions](../data/reference_packs/README.md) to populate permitted evidence. MQA/research cards and broader curriculum inventories may require lawful manual acquisition/import. Database absence or an empty category is never filled with invented records. Unsupported PDF layouts/scans still need the existing reviewed-region/structured-import fallback; Phase 4 does not rebuild PDF ingestion or claim a general syllabus extractor.

Copy `.env.example` locally. The baseline, tests and offline jobs need no provider keys. All analysis HTTP reads and writes require a nonempty `ANALYSIS_WRITE_TOKEN` and `X-Analysis-Token` header; absent configuration returns 503, wrong/missing supplied token returns 401. Local CLI administration relies on operating-system/database access. This is a single-operator MVP access boundary, not full institution-specific identity/tenant authorization.

Use `ANALYSIS_MODEL_PROVIDER=replit_claude`, `CLAUDE_MODEL=claude-opus-5` and the [managed configuration](23_PHASE41_REPLIT_CLAUDE.md). Keep `GEMINI_ENABLED=false` and `ANALYSIS_GEMINI_FALLBACK_ENABLED=false`. No connection is assumed from a Git checkout. External processing requires explicit consent; retain the persistent false gate and enable only the authorised worker process. `RESEARCH_ENABLED` and `BRAVE_SEARCH_API_KEY` separately enable approved research. Do not paste keys into chat, commit them or send private uploaded documents to Brave. Record returned model identity and actual usage separately from configured values and price estimates.

The current Claude transport uses a simplified JSON grammar followed by the original Pydantic and citation validation. The actual live worker proof is recorded separately; no academic schema was weakened. [Brave Web Search](https://api-dashboard.search.brave.com/api-reference/web/search/get) still requires its own approved live check.

## Submit and retrieve a run

Staff select a programme and upload documents through the existing catalogue path. Finish extraction and inspect ambiguity/coverage before analysis. A title/brochure is sufficient for preliminary screening; a missing detailed syllabus is an explicit limitation.

```powershell
python -m shiftos.cli analyse-programme --programme <PROGRAMME_UUID> --mode offline --no-research --idempotency-key review-v1
python -m shiftos.cli worker --once
```

The CLI prints `analysis_id` and `job_id`. HTTP `POST /api/v1/programmes/{id}/analyses` accepts:

```json
{"mode":"offline","research":false,"idempotency_key":"review-v1"}
```

It returns 202 with the run and job identifiers. Optional `revision_id` chooses a historical catalogue revision; otherwise the active revision is frozen. Optional aware `as_of` selects a historical as-known evidence cutoff and disables research backfill. Same idempotency key and intent return the original run even if a later catalogue becomes active; changed intent returns 409. A new refresh uses a new key/run. An empty inventory or another programme's revision is rejected.

Protected GET routes provide `/programmes/{id}/analyses`, `/analyses/{id}`, `/analyses/{id}/courses` and `/analyses/{id}/courses/{course_id}` under `/api/v1`. Lists use existing pagination. The legacy `/catalogue/jobs/{id}` read also requires analysis authorization for analysis jobs; curriculum job reads retain their previous behavior. No public arbitrary-URL research or evidence-ingestion endpoint was added.

## Internal-first retrieval and controlled fallback

`services/analysis/retrieval.py` retrieves versioned occupation/skill/relationship/task, academic standard, workforce and AI records from PostgreSQL. It keeps every frozen course appearance. Bounded lexical/discipline associations are review candidates, not verified curriculum skills or occupation identities. Preserve actual taxonomy/edition/language; do not invent translations or Malaysian classification bridges.

Sufficiency checks retain class, review state, dates/precision, scope, applicability, corrections, rights and coverage gaps. Exact structured official values can remain provisional `needs_review` context; automatic PDF pages do not become factual findings. AI transformation needs reviewed task/capability and identity evidence. Published occupation-group advertising stays broad context; the existing deterministic radar owns units, comparison compatibility, thresholds and arithmetic. No LLM calculates workforce trends or turns exposure/decline into course obsolescence.

`data/analysis_permissions.json` separates internal analysis, external model processing and excerpt output. Unknown use is denied; explicit source/version/record denial overrides a grant. Scoped internal MQA/research use does not authorize sharing with Gemini or redistributing text. Model-facing packets strip nonpermitted content and retain bibliographic limitations. Applicable source policy/version/hash is frozen with each run.

For important evidence gaps, enabled `ResearchService` uses generic allowlisted discipline/gap queries through Brave. It does not send uploaded prose, course titles or personal identifiers. Search results are discovery candidates. Automatic original acquisition is limited to exact registered source/artifact URLs with approved source/use rules and supported deterministic adapters. It reuses the safe transport and actual Phase 3 import/query path. Unknown sources need registration/policy/manual review; ambiguous PDFs remain candidates. This is a bounded research fallback, not unrestricted interpretation of arbitrary websites.

`data/research_policy.json` limits two queries per supported gap, ten queries/documents and 180 seconds per run. Original acquisition retains public-IP/DNS/redirect/robots/terms, size, retry and rate protections. Disabled/missing providers, unsafe/restricted sources, failed imports and exhausted budgets produce explicit outcomes and unresolved evidence. Search snippets, same-model agreement and URL existence cannot verify a factual claim.

Permitted evidence keeps immutable Phase 3 lineage; repeated imports are idempotent. Research cache keys include scope and registry/acquisition/research/permission policy hashes, and cached version pointers are rechecked. Positive metadata defaults to one hour, negative operational outcomes to five minutes. The default Brave plan policy forbids storing search result text/titles/unknown URLs; only operator-owned operational outcomes and registered evidence lineage are cached. Broader result storage requires the appropriate [Brave storage entitlement](https://brave.com/search/api/) and explicit policy. No live subscription rights were assumed.

## Grounded findings, programme insights and lifecycle

The selected model receives a bounded evidence packet and a provider-compatible JSON schema; the original Pydantic contract is always enforced locally. Output has five dimensions for every course: foundational relevance, AI transformation, workforce alignment, curriculum currency and future resilience. It can select source-backed quotations, scoped statuses, fixed safe review questions and explicit limitation codes. There are no free-form factual-assertion, arbitrary score, course-replacement or action-authoring fields. Application validation checks exact course coverage, reference association, quote support, scope, rights and title/syllabus restrictions, then derives programme counts and insights deterministically.

Programme insights contain verified curriculum evidence where available, cited AI task context, possible coverage questions, course review IDs, deterministic demand context and unknowns. They do not turn a title match into competency coverage, a possible gap into a confirmed missing skill, or a quoted experiment into a general prediction. Verified descriptions/syllabus passages support only their documented level and intent, not measured student competence.

Titles alone retain `needs_syllabus_confirmation`; unsupported dimensions return `insufficient_evidence` (**INSUFFICIENT EVIDENCE**). Every course has `is_final_curriculum_verdict=false`. Source-rich review questions can coexist with an insufficient content conclusion. Current retrieval does not certify comprehensive/current standards, exact occupational identity or a complete graduation curriculum.

Offline synthetic runs disclose `offline_synthetic`; genuine offline runs disclose `deterministic_insufficiency`. They never claim Gemini analysis. Live configuration/provider/validation failure preserves all courses through the deterministic fallback and a visible PARTIAL job/model outcome. Adapter invocation counts include configuration checks and retries/repair; they must not be described as verified live API calls. A model-generated batch has `live_model` only after output validation, with fallback-course counts disclosed for mixed results.

Limits are 1,000 inventoried courses, model batches of 20 with at most ten batches, one structured-output repair per batch, bounded provider attempts/bytes/time and a 600-second worker research/model budget. Remaining courses receive explicit budget insufficiency, not omission. Completed manifests/results are immutable through the service/API; a changed inventory fails the run and requires new submission. Late workers cannot publish after operator stale-job recovery. `fail-stale-jobs` explicitly handles analysis jobs; it does not silently retry them.

Read APIs recheck permission-policy version/hash and source rejection/correction state where implemented; changed/unknown policy withholds text and flags revalidation rather than rewriting the frozen result. Full production identity, retention enforcement and continuous publisher monitoring remain later operational work. Replaying completed results makes no research/model call; regenerating with new evidence creates another versioned run.

## Measured validation and remaining gates

The initial Phase 1–3 PostgreSQL baseline was **487 passed**, zero skips, one existing upstream deprecation warning. The final complete suite was **637 passed, zero failures/skips in 73.17s**, including **12 PostgreSQL integration tests**, with the same existing warning. Ruff lint/formatting, dependency integrity, all-five-revision migration SQL and whitespace checks passed. Unit/API/provider/retrieval/grounding tests use labelled fixtures/mocked providers; PostgreSQL coverage includes additive migration/history/ownership and worker-to-protected-API execution across Computing, Accounting and Marine Biotechnology fixtures. A genuine ESCO pack regression imported/queried 87 normalized records against a fictional engineering programme, retaining real source identifiers and limits.

A separate isolated PostgreSQL copy of the genuine Phase 3 validation data was migrated to 0005. Final Accounting CLI/API → worker → protected reads returned **all 37 real course appearances**, **57 source-linked references** (57 internally eligible, 51 model/output eligible), unchanged idempotent replay and HTTP401 without authorization. All 37 courses retained insufficient content evidence. These references include standards, AI, skills/relations and broad workforce context; reviewed occupation identities and syllabus content remain gaps. This was genuine database retrieval with **zero live Gemini/Brave calls**, not a new download, live research success or validated model reasoning. The original validation database was preserved; only Accounting had an active genuine course inventory in this copy, so other discipline proofs use clearly labelled fixtures rather than claiming loaded real programmes.

The user selected offline verification; credentials/model are not configured. Live Gemini structured output and real Brave → original verification/import → cited finding remain unverified acceptance gates. Current source/currentness/permissions/identity gaps also remain. Phase 4 is functional for a bounded offline proof; complete live acceptance and automatic academic recommendations must not be claimed. Stop before Phase 5 implementation. The [future career/pathway plan](22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md) only revises later requirements.
