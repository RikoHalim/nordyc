# Phase 7 — Integration, Evaluation, Security and Deployment Readiness

## Scope and separate readiness decisions

The branch is **`feature/phase7-system-integration`**, based on the verified published Phase 6 documentation receipt **`9149d55bf597d3eef2a10193cceba0d56694e040`**, including implementation `b711999d6c23023591eec590963ca8ee174ec703`. Existing Phase 1–6 architecture, sources, migrations and previous branches are preserved. Replit remains hosting, managed **`claude-opus-5`** remains primary, Brave remains independent and Gemini stays disabled. No new provider, application agent, model training, database, frontend, deployment or merge is included.

| Readiness | Meaning |
|---|---|
| Backend integration/hardening | Controlled workflows, scoped access, replay, evaluation and operating tools implemented; final measured checks are in STATUS |
| Automated evaluation | Versioned fictional collection and actual software observations; not an expert academic benchmark |
| Real academic validation | **Pending**: reviewed real curriculum/assessment/mapping data and independent academic reviewers |
| Security | Institution-scoped operator grants and concrete hardening implemented; production identity, host/storage validation and security operations remain gates |
| Operational deployment | **Not accepted**: no Replit PostgreSQL provision, supervisor, persistent-upload storage, restore test or public deployment performed |
| Hackathon compliance | Institutional substitutions for individual intake/matching/pathways remain **UNCONFIRMED** |

Implementation completion is not production readiness. [STATUS](../STATUS.md) distinguishes final observed acceptance from historical live provider tests and blocked external gates.

## Continuous workflow and fixture

`services/integration.py` drives the existing protected APIs, repositories, source ETL and worker. It imports source **inputs**, never writes derived findings/approvals directly. Programme creation → structured curriculum import job → committed revision and every course → reviewed synthetic source/passages → Phase 4 job and all-course results → exact-revision Phase 5 requirements/coverage/recommendations → explicit version-bound operator consideration → Phase 6 job linked to the exact Phase 4/5 outputs → scenarios/SDG/Action Plan → explicit plan review → protected retrieval and independent committed PostgreSQL read.

[The integration specification](../examples/system_integration.synthetic.json) and [versioned discipline collection](../examples/evaluation/collection.v1.json) provide six or more fictional courses, three fictional occupational candidates, reviewed intended/demonstrated/partial coverage, an explicit full-inventory deficiency audit and an unknown requirement. Occupations, requirements and programme names are discipline-specific across computing, accounting and biotechnology. Additional workload titles remain inventory-only unknowns. Benchmarks never prove actual university teaching. The genuine, already permitted UN pack remains labelled genuine even in a fictional programme.

The explicit acceptance harness in `scripts/verify_system.py` installs bounded mock Claude adapters and denies synchronous/asynchronous HTTP. Process-local consent is enabled only for these mocks; no real provider credential/base URL is supplied. API metadata uses the explicit `-synthetic-mock` model suffix and the receipt says `provider_execution=mocked`. This is not a real Claude response, token measurement or live prompt-red-team result. Application defaults and persistent external-processing/research gates stay false.

## Reproduction and owned database safety

Install the pinned development dependencies. Select an **owned disposable loopback PostgreSQL test database** explicitly; do not use a shared, production or ambient Replit database. The verification script rejects external hosts, non-test names, URL options and unbounded workloads. It creates fresh randomly named schemas, applies existing migrations only there, commits/query-checks results, then removes only schemas whose ownership comment matches its unique marker. Reports and input artifacts stay ignored under `data/local`.

```powershell
python scripts/verify_system.py --database-url <OWNED_LOOPBACK_TEST_URL> --sizes 6 30 100 --report data/local/system-verification.json --export-api
python scripts/evaluate_system.py --output data/local/evaluation.json
# Configure TEST_DATABASE_URL only to the separately selected disposable PostgreSQL DB.
python -m pytest -q
python -m ruff check src tests alembic scripts
python -m ruff format --check src tests alembic scripts
python -m pip check
python -m alembic heads
```

The verification URL is an administrative test input, not a frontend parameter; use a disposable local role and avoid credential-bearing URLs in terminal history. Never pass production credentials to this tool. The evaluation command uses fresh SQLite databases for controlled unit-level observations, and labels them **`sqlite_unit_only`**. It does not substitute SQLite for runtime or PostgreSQL integration acceptance.

## Evaluation method, denominators and limits

Collection **`shiftos-controlled-academic-consistency`**, version **`1.0.0`**, SHA256 **`7672969c91f0eba884f8d0a353bae2a355f80747efd5dde4fd162c998847bd0f`**; method **`phase7-controlled-invariants-1`**. Phase 5/6 retain `phase5-requirement-coverage-1` / `phase6-pathways-1`.

The measured run executed **84 observations: 84 pass, 0 fail, 0 not observed**, across 28 labelled checks × three disciplines and 15 independently created controlled databases. Every denominator is executed checks in that dimension, not individual citations, students, programmes in the real world or independent academic judgements. Missing executions report `not_observed` and are excluded visibly, never counted as passes.

| Dimension | Passed / executed |
|---|---:|
| API correctness | 3 / 3 |
| Citation validation | 3 / 3 |
| Competency classification | 3 / 3 |
| Curriculum fidelity | 6 / 6 |
| Evidence grounding | 3 / 3 |
| Occupation mapping | 6 / 6 |
| Plan completion | 3 / 3 |
| Recommendation lineage | 6 / 6 |
| Repeat consistency | 3 / 3 |
| Review integrity | 9 / 9 |
| Scenario integrity | 6 / 6 |
| SDG integrity | 6 / 6 |
| Stale-source invalidation | 6 / 6 |
| Structured output | 3 / 3 |
| Uncertainty | 9 / 9 |
| Unsupported-claim rejection | 9 / 9 |

Three methods are distinguished: observed valid outputs; rejection of deliberately forged outputs by production validators after validating the unmodified baseline; and actual changed-input/source/replay executions. Variants include conflicting positive/negative curriculum evidence, stale workforce evidence, wrong occupation identity, title-only unknowns, missing intent, source withdrawal/change, duplicate requests, invented quotations, manipulated skills/versions/SDGs/scenarios and automatic approval attempts. Embedded instruction text stays source data. Existing provider/SSRF/robots regressions remain intact.

These are engineering-authored fixture labels and consistency checks, not independent expert labels or academic accuracy estimates. Rule regeneration and output-mutation rejection do not validate real curricula. Offline/mocked injection tests establish software boundaries; actual Claude jailbreak resistance, real Phase 5/6 semantic model quality and live research admission remain unmeasured. No paid request was made to close those gaps.

## Replay and historical integrity

POST **`/api/v1/programmes/{programme_id}/replay-assessment`** is an authenticated read assessment. Select exact existing Phase 4/career/plan IDs and bounded typed changes: programme revision, source, dataset version, evidence reference, document anchor, occupation requirement, workforce observation, career review or scenario assumption. The service checks programme ownership, revision and exact parent lineage, then reuses current source/permission/review guards.

It returns current eligibility, affected phases/pathway keys, reason codes and required explicit submissions. It creates **zero jobs**, returns no source prose and transfers no approvals. A newly admitted but unfrozen observation needs applicability/retrieval review; absence from an old snapshot cannot prove no effect. An assumption change can require a new plan while leaving Phase 4/5 unchanged. Source invalidation can affect a whole dependent plan, even when the associated pathway is narrow. Historical results stay immutable and may be withheld when current rights no longer permit disclosure.

Positive revision replay uses the actual import API/worker to create a new revision, then new Phase 4, career and plan jobs. All six new course IDs are accounted for. Old course assertions/mappings/reviews do not silently transfer: new title-only records retain insufficiency and manual review, while prior raw results/fingerprints remain preserved and flagged stale. An old plan fingerprint cannot approve the new plan. The existing explicit assumption replay changes one dependent pathway and preserves unaffected paths and the earlier plan.

## Threat model and implemented controls

Trusted boundaries are the server administrator, selected database role, operator-managed policy file and checked-in source-use policies. Untrusted inputs include HTTP clients, resource IDs, uploads, source text, search results and model output. We defend API disclosure/write boundaries, not a compromised host/database administrator. The PDF child is a resource boundary, not an OS sandbox.

| Threat / concrete issue | Implemented control |
|---|---|
| Public catalogue/source routes and cross-institution identifiers | Optional scoped bearer mode across API routers; object ownership and filtered list/count pagination before disclosure |
| Shared-token privilege ambiguity | Explicit read/write/review grants; global source/evidence administration additionally requires admin; admin does not imply other permissions |
| Generic career/plan job result bypass | All three analysis job kinds require analysis access and withhold source-derived job results; use the protected typed analysis resources |
| Foreign source attribution on a write | Ordinary scoped writers cannot attach another institution's source ID |
| Stale/source-withdrawn results and reviews | Existing current-state checks, exact fingerprints, withheld derived JSON and blocked approval; policy revocation checked on new requests |
| Slow/incomplete request body | 30-second total receive deadline, existing 1 MiB JSON and 20 MB PDF limits, safe 408/413 envelopes |
| Private PDF storage | Institution namespaces in scoped mode, generated SHA256 filenames, regular-file/nofollow/hardlink checks; private 0700 directories/0600 new files on POSIX |
| PDF parser resource exhaustion | Scoped uploads execute in a secret-free child: 30-second wall limit; POSIX 20 CPU seconds and 512 MiB address space; bounded input/output and candidate validation before DB writes |
| Credential/source leakage | SecretStr settings, redacted fixed errors, no provider bodies or query/header values in HTTP logs; API responses use no-store/nosniff/no-referrer |
| Prompt-injected source or forged model output | No source-driven tools, bounded schema/IDs/options, exact citations, deterministic facts/eligibility/approval rules and explicit insufficiency |
| Interrupted/duplicate/late worker | Existing atomic publication, idempotency, running-job locks, stale fencing and explicit recovery; no silent paid retry or approval transfer |

Legacy upload paths remain readable for old local jobs; newly scoped processing uses isolation even for an older stored upload. No original is served as a static file. Windows ACLs require deployment-owner verification; POSIX mode bits do not prove durable host security. Parser-library vulnerabilities, OS containment, dependency vulnerability monitoring, encrypted storage, quotas/rate limiting at the edge, backups and restore procedures remain operational work. Files that cannot be associated with a completed upload after an interruption are retained privately for explicit administrator reconciliation; there is no unsafe automatic recursive cleanup.

## Access policy and compatibility

`API_ACCESS_MODE=legacy` preserves the verified local development/test header workflows. It is prohibited for production startup. Replit preview defaults to `scoped`, so missing policy blocks API use rather than exposing institution data. Configure **`API_ACCESS_POLICY_PATH`** to a private JSON file. [The template](../examples/access-policy.template.json) deliberately contains invalid placeholders and cannot grant access until configured.

Policy version `phase7-access-1` contains bounded principals: an operator alias, SHA256 of a private bearer credential of at least 32 characters, explicit institution UUIDs and read/write/review/admin grants. Keep raw credentials only in a private channel/Secrets. Use `Authorization: Bearer ...`; legacy headers cannot bypass scoped mode. Global source/reference store has no tenant owner, so ordinary scoped institutional users consume permitted derived views and cannot use raw reference administration. The policy alias is an operator grant, **not named academic identity**. Persisted reviews retain server-assigned `authenticated_analysis_operator`; no fake academic author is introduced.

This is application-level scoped authorization, not database row-level security, SSO, student authentication or a production identity service. The server worker/CLI retains administrator database access and is not a tenant-facing endpoint. Within protected routers, unrecognised ownership families fail closed; every future data router must retain the common access dependency. Role/policy management, rotation, named users, MFA, transport/edge policy and operational audit retention must be validated before public multi-user deployment.

## PostgreSQL, preflight and Replit preparation

Standard managed `postgresql://` / `postgres://` URIs now normalize to the existing synchronous **`postgresql+psycopg`** driver, preserving credentials and TLS/query options. Unsupported database engines/drivers remain rejected; no SQLite runtime fallback is added. Existing `DATABASE_URL` selects the environment; never hardcode a local cluster address or silently connect to a historical verification database.

`python -m shiftos.cli runtime-preflight` inspects safe configuration, including the source-use policy, with **zero provider calls/migrations**. Optional **`--check-database`** explicitly reads connectivity and migration heads from the selected DB. Run it with **`--component api`** and **`--component worker`** in their respective environments. Compare the opaque configuration receipts (driver, host, database, role and query/schema options; passwords excluded). Matching configuration receipts are not a heartbeat or proof a worker is running. The real PostgreSQL test uses an independent connection and confirms matching current-schema receipts. `/health/live` remains liveness; production `/health/ready` requires a valid scoped policy, database connectivity and the reviewed Alembic head.

| Setting | Required treatment |
|---|---|
| `DATABASE_URL` | Explicit development/production PostgreSQL connection from the selected environment; preserve required TLS options |
| `APP_ENV` | Development/test locally; production only with scoped policy and deployment checks |
| `API_ACCESS_MODE`, `API_ACCESS_POLICY_PATH` | Scoped mode and private configured policy for Replit/production |
| `CURRICULUM_UPLOAD_DIR` | Shared private durable storage accessible to API and worker; private ACLs, ownership, retention and backups verified |
| `ANALYSIS_MODEL_PROVIDER`, `CLAUDE_MODEL` | `replit_claude`, `claude-opus-5`; managed key/base URL provisioned by Replit |
| `AI_INTEGRATIONS_ANTHROPIC_API_KEY/BASE_URL` | Replit-managed Secrets; never put them in code, example responses or logs |
| `BRAVE_SEARCH_API_KEY` | Independent source/API entitlement and separately approved live research |
| External gates | `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=false`, `RESEARCH_ENABLED=false`, `GEMINI_ENABLED=false`, `ANALYSIS_GEMINI_FALLBACK_ENABLED=false` |
| `PORT` | Valid integer 1–65535; API launcher binds the platform-selected port |

Select the intended **development** database in Replit's Database tool and verify its environment connection, rather than guessing legacy PG variables. Replit documents `DATABASE_URL` as its development connection variable. [Official connection guidance](https://docs.replit.com/features/data-and-storage/connection-details).

Replit documents separate development/production environments. Do not assume local Windows data or safe fixture content automatically belongs in production; confirm the selected database, migration plan and export/restore policy before any change. No shared/production database was altered here. [Official environment guidance](https://docs.replit.com/features/data-and-storage/development-and-production).

The all-interface launcher requires a valid scoped policy in every environment. Trusted local legacy development uses loopback uvicorn. The `.replit` Run command starts **only FastAPI** through `scripts/run_backend.py`; it performs no migration or worker launch. Install pinned dependencies, configure the policy/storage/selected development database, inspect preflight, then explicitly apply `python -m alembic upgrade head` to that approved isolated development DB. Run `python -m shiftos.cli worker` separately with the **same** database/policy/storage configuration. `worker --once` is useful for controlled operations.

For Phase 8, a Reserved VM with an explicitly supervised worker is the proposed fit for this durable polling design. This is an engineering recommendation: Replit describes Reserved VM as suitable for persistent background work, while Autoscale can scale to zero. No hosting tier was selected or purchased and no supervisor installed/deployment performed. [Official deployment types](https://docs.replit.com/features/publishing/deployment-types). Do not assume an API-only Autoscale process provides a reliable long-running worker or durable local upload filesystem.

Recovery is explicit: inspect protected job status, reconcile private upload artifacts, run `fail-stale-jobs` after the documented one-hour abandoned-job threshold, then submit a new deliberate request/version/key where appropriate. A repeated idempotency key returns the original run, including a failed one. Never delete paid-request receipts, silently repeat a model call or transfer approval to retry output. Existing database transactions roll back incomplete derived results.

## Measured bounded performance

Windows Python 3.13.13 / PostgreSQL 16.15, one workload per size, local TestClient and mocked Claude, Python `tracemalloc` enabled. End-to-end includes source seeding, all jobs, explicit reviews, idempotent read/replay, assumption replay and independent persistence check; it is not an HTTP throughput or cloud SLA benchmark.

| Courses | Total elapsed | SQL statements | Plan response bytes | Python allocation peak |
|---:|---:|---:|---:|---:|
| 6 | 7,969.026 ms | 2,053 | 300,477 | 25,216,216 bytes |
| 30 | 9,118.951 ms | 2,102 | 309,522 | 13,762,925 bytes |
| 100 | 10,668.120 ms | 2,241 | 335,863 | 16,055,650 bytes |

For 6/30/100 courses, curriculum import measured 635.578/792.952/835.755 ms; Phase 4 554.168/708.530/1,734.525 ms; career processing 1,026.282/1,343.499/1,198.956 ms; plan aggregation 1,476.858/1,552.648/1,780.137 ms. Aggregate protected retrieval stages measured 508.520/524.513/659.028 ms and are not per-request p95 values. Python allocation peak is not process RSS or PostgreSQL memory. The first run includes cold initialization; no monotonic-memory or cloud-capacity conclusion is inferred.

The source admission/review/policy validation work dominates fixed query overhead (source admission alone: 612 SQL statements). There is no measured need for Redis/Celery/Kafka or a new architecture. Follow-up optimization should profile batched source checks and pagination under representative real workloads while preserving rights/revalidation; no speculative caching rewrite was introduced. Actual paid-model tokens, network latency and billing are **not observed**. Mock call counts are 1/2/5 Phase 4 batches, one Phase 5 comparison and two Phase 6 reviews per workload, including the explicit assumption replay.

## Frontend and Phase 8 handoff

Existing protected programme/revision/course/analysis/career/plan endpoints remain the source of truth. Career and plan read schemas now expose their full result models alongside the existing pending/withheld dictionaries; typed section endpoints retain pagination/status/error fields. OpenAPI model validation, internal references and unique operation IDs are checked. The only new business route is read-only replay assessment; no frontend is included.

[Six bounded API examples](../examples/api/courses.synthetic.json) cover course inventory, Phase 4 course results, pathways, scenarios, SDG and plan review. They are actual mocked/synthetic response extracts with one consistent normalized UUID map, explicit mock flags and normalized hashes/dates. They support frontend mock rendering, **not backend replay or approval submissions**. Never send normalized version hashes to a real review endpoint.

Recommended dashboard sequence: programme/revision and coverage → all-course intelligence/evidence → occupation/competency matrix → academic actions/alternatives/no change → pathways/resources/unknown duration → scenario comparison → justified SDGs → consolidated plan and separate review history. Preserve empty/loading/failed/partial/insufficient states, null measures, source dates and review requirements. Read `needs_evidence_revalidation` before rendering any source-derived text; withheld dictionaries are not complete results. Use exact current fingerprints on review writes and display 401/403/404/409/422/503 safe errors. Do not implement named reviewer identity by displaying the shared operator alias.

Before controlled deployment: confirm organiser scope; obtain permitted reviewed real data and expert validation; provision/verify a separate selected Replit database; configure scoped identities and rotation; validate worker supervision, shared durable private storage/ACLs, backups/restore, TLS, edge throttling and logs; verify runtime/schema/API-worker receipts; then obtain any new bounded live model/research approval. Brave Phase 4.3 original-source admission remains **PARTIAL**. The institution workflow does not close personal matching/pathway compliance gaps. Stop before Phase 8 implementation until separately authorized.


## Final automated acceptance

Final complete suite: **1,078 passed**, including **20 real PostgreSQL cases**, **0 failures/errors/skips**, **178.91 seconds** on Python 3.13.13 and isolated PostgreSQL 16.15. Baseline 974 → 1,078 (net +104), PostgreSQL 18 → 20. Ruff lint/format, dependency integrity, Alembic upgrade/schema-drift/head/offline SQL and Git whitespace pass. One existing Starlette/httpx deprecation warning remains. API/worker preflights passed with the same explicit owned database/schema configuration receipt, valid source policy and zero provider requests/migrations. New access/data changes require no extra persistent table; single head remains 0007_academic_action_plans.

CI now includes PostgreSQL integration, source/processing-off defaults, dependency and migration/runtime checks. This local acceptance does not assert that GitHub Actions or Replit executed the branch. Public staged credential/path/link checks and publication receipts are recorded in STATUS. Local reports, raw controlled receipts and database files remain ignored; the owned PostgreSQL server is stopped after verification. Backend integration/hardening is complete for the controlled contract; production, real academic validation and organiser scope remain explicitly unresolved.

The final remote audit observed an independent Claude/Brave branch advance from b8b5e3ae315f656390eae3d0a45256c4884e450c to ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec. Phase 7 remains based on the unchanged verified Phase 6 receipt; the other branch was neither merged nor modified by this work.

## Publication receipt

The tested 55-file implementation was committed and pushed to **feature/phase7-system-integration** as [80f0f1412fa5b9702f8d1d0ffc3d7db38dd9fc70](https://github.com/RikoHalim/NORDYC/commit/80f0f1412fa5b9702f8d1d0ffc3d7db38dd9fc70); the exact remote SHA was verified. All 95 checked local Markdown links resolved; staged credential-pattern/private-path/whitespace checks passed. This documentation-only receipt records that publication. Main, Gemini and Phase 5/6 remote commits matched the initial audit. The independently advanced Claude branch was not modified or merged. No force-push, provider request, Replit change, public deployment or Phase 8 implementation occurred. The owned PostgreSQL server was stopped; local receipts/data remain ignored. GitHub Actions execution was not observed or claimed.
