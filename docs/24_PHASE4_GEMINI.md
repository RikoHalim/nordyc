# Phase 4 direct Gemini — isolated development and verification

Branch **`feature/phase4-gemini`**, based on published `main`
**`164255d52b5ceb005647ec670506f10cb5054b10`**, fetched/inspected on **24 October 2026**.
Phase 4 was already published as `b586194`, Phase 4.1 Claude implementation as
`ec9b7f79ea26760a75f84e3c98cef8d4ce71bcfb`; the base includes its later publication record.
The working tree was clean; no stash/reset/overwriting was needed. The teammate's
`feature/phase4-replit-claude` was absent from the remote listing at inspection and
was not created/modified/merged/deleted. [STATUS](../STATUS.md) records Gemini's
implementation commit and publication result. Only this Gemini branch is authorized
for publication; stop before merging, Phase 5/6, frontend or deployment.

Published implementation:
[`c95384004e9563f3f00e2d69d8936aef7ec0956b`](https://github.com/RikoHalim/shift-os/commit/c95384004e9563f3f00e2d69d8936aef7ec0956b).
After push, the remote feature ref matched exactly and `main` remained at the shared
base. A documentation-only publication record can be the later tip of
[`feature/phase4-gemini`](https://github.com/RikoHalim/shift-os/tree/feature/phase4-gemini).

## Actual acceptance result

**Implemented and offline verified; live Gemini verification is BLOCKED.**
No `GEMINI_API_KEY`/`GEMINI_MODEL` is configured in the process and no local `.env`
exists. Enable/external-processing settings retain false defaults. Actual preflight
and explicit `verify-gemini --live` both returned blocked, exit 1, **zero requests**.
The bounded ESCO source permission passes. This is a configuration blocker, not
attempted authentication or an observed Google outage.

Actual model **none observed**; actual input/output/thought tokens, live latency and
observed cost **unavailable**. No zero-dollar bill or estimated charge is represented
as observed cost. Claude and Brave remain independently live-unverified. This does
not establish curriculum accuracy or provider superiority.

## Model, protocol and limits

Official Google documentation checked on 24 October 2026 lists these identifiers:

| Model | Documented selection/status |
|---|---|
| `gemini-4-argon` | Stable flagship reasoning model; preferred quality-first candidate. Account access is unverified. |
| `gemini-3.8-flash` | Stable thinking/structured-output alternative, requiring explicit selection. |
| `gemini-3.1-pro-preview` | Preview reasoning alternative; preview lifecycle/quotas need separate consideration. |
| `gemini-2.5-pro` | Older stable thinking/structured-output model; recheck lifecycle/project availability before use. |

Sources: [model catalogue](https://ai.google.dev/gemini-api/docs/models),
[Argon specification](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon),
[Argon API changes](https://ai.google.dev/gemini-api/docs/latest-model),
[Flash specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[Pro preview](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview),
[older stable Pro](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-pro).
These are documentation observations, not successful model requests. There is no
automatic model substitution or Gemini-to-Claude fallback.

The existing `httpx` adapter uses direct REST, not Replit AI Integrations:
`POST https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent`.
Authentication uses the server-side `x-goog-api-key` header, never a URL parameter.
Use a project-authorized key restricted appropriately to the Gemini API. This
application deliberately reads `GEMINI_API_KEY`, not SDK key discovery or Replit
credentials. See [Google key setup](https://ai.google.dev/gemini-api/docs/api-key)
and [GenerateContent REST](https://ai.google.dev/api/generate-content).

Requests use `responseMimeType=application/json`, the unchanged
`ProgrammeResult.model_json_schema()` as `responseJsonSchema`, and `candidateCount=1`.
Original Pydantic and citation/rights/scope/course-coverage validation always run
locally. Google's schema subset/complexity is still a live compatibility gate;
do not relax the academic schema to make a request succeed. See
[structured outputs](https://ai.google.dev/gemini-api/docs/structured-output).
The adapter now requires an actual returned Gemini model and a complete `STOP`
response, rejects malformed/tool parts and unexpected candidate counts, and discards
thought text. Returned model/whitelisted tokens survive invalid/incomplete output
where available. No tools, external grounding, sampling override, training or
additional agent is introduced. Claude/Brave adapters are unchanged.

Google documents Argon's unified 1,048,576-token context and default synchronous
maximum output of 65,536. SHIFT//OS uses narrower bounds:

| Limit | Application behavior |
|---|---|
| Request/response bytes | 1,000,000 each |
| Output tokens | `GEMINI_MAX_OUTPUT_TOKENS`: 1–16,384; isolated verification caps at 4,096 |
| HTTP attempts | Configurable 1–3 per generation; verification forces **one** |
| Timeout | Configurable 1–60 seconds, default 20; explicitly use 60 for a reasoning-model check |
| Retries | Bounded 429/5xx/HTTP retries, backoff/Retry-After and deadline; none in the isolated helper |
| Worker | Existing 20-course batches, ten-batch maximum, one validation repair, 600-second budget; unprocessed courses abstain |

Argon thinking and visible output share the token cap; 4,096 may truncate a response.
Inspect failure/usage before authorizing another request; do not auto-loop or
silently raise the verification cap. Worker repair is separate from the one-request
helper. Byte limits are not token predictions. RPM/TPM/RPD depend on project/model/
tier, not key count; inspect the project's [active rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).
No account quota/credit entitlement is assumed. A consumer Google AI subscription
does not establish API credits; inspect project [billing](https://ai.google.dev/gemini-api/docs/billing)
and [current API pricing](https://ai.google.dev/gemini-api/docs/pricing).

## Privacy and local configuration

The helper sends one fictional course and one existing attributed, permitted ESCO
excerpt. Unknown/restricted sources remain denied by the existing source policy;
private uploads/restricted MQA documents are excluded. Public access alone is not
processing permission. Google documents different paid/unpaid data-use terms:
unpaid inputs may support improvement/human review; paid prompts are not used for
product improvement under the stated terms, with limited abuse-detection processing.
Review actual project status, applicable [terms](https://ai.google.dev/gemini-api/terms)
and institutional policy before enabling processing. An ESCO grant does not approve
all future uploaded documents.

Install locked dependencies as in README. Keep credentials in environment variables
or ignored `.env`, never in chat/Git. For a later authorized check, set locally:

```dotenv
ANALYSIS_MODEL_PROVIDER=gemini
GEMINI_ENABLED=true
GEMINI_MODEL=gemini-4-argon
GEMINI_MAX_OUTPUT_TOKENS=16384
ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=true
ANALYSIS_PROVIDER_TIMEOUT_SECONDS=60
ANALYSIS_PROVIDER_MAX_ATTEMPTS=1
ANALYSIS_GEMINI_FALLBACK_ENABLED=false
RESEARCH_ENABLED=false
ANALYSIS_PERMISSIONS_PATH=data/analysis_permissions.json
```

Configure `GEMINI_API_KEY` privately and verify API billing/quota separately. Inspect
configuration first; this constructs neither a provider nor a database:

```powershell
python -m shiftos.cli verify-gemini --report data/local/gemini-preflight.json
```

When configuration/processing permission is ready, run **once**:

```powershell
python -m shiftos.cli verify-gemini --live --report data/local/gemini-verification.json
```

There is at most one transport attempt, no repair/fallback/search/database call.
Exit 0 requires actual model identity, one request, schema/grounding/insufficiency
validation, at least one exact supported citation, and observed input/output tokens.
Reports include thought/total/cache tokens when supplied, provider latency, packet/
schema/instruction/result hashes and request bounds. Costs remain unknown without
billing evidence. Fixed error codes replace raw rejected output. A report-export
failure preserves outcome/usage in stdout and returns exit 1. Reports remain ignored
under `data/local`. Preflight readiness is not proof of account/model availability.

## Backend, tests and live follow-up

FastAPI routes, academic schemas and PostgreSQL tables are unchanged. No migration
is needed; existing revisions 0001–0005 remain the complete history. Existing JSON
manifests persist actual model/token/request/validation outcomes. Network work stays
in the separate worker, outside HTTP handlers.

New PostgreSQL tests exercise the actual Gemini adapter with mocked HTTP:
three-course synthetic Accounting inventory → internal academic/AI/workforce records
→ sufficiency/rights → structured request → schema/citation validation → deterministic
programme summary/unknowns → committed findings/usage → protected FastAPI reads.
An independent connection verifies committed state; replay makes no further call.
Authentication/citation failures preserve all courses as PARTIAL/insufficient results.
These are backend/transport tests, **not live Gemini acceptance**. Existing genuine
ESCO-pack retrieval/provenance tests remain in the complete suite.

Measured on Windows/Python 3.13.13 with disposable loopback PostgreSQL 16.15:

| Check | Actual result |
|---|---|
| Existing provider/Claude targeted regressions | 125 passed |
| New Gemini helper/CLI targeted checks | 35 passed |
| New Gemini PostgreSQL/worker/API checks | 3 passed, mocked HTTP only |
| Separate complete PostgreSQL integration selection | **16 passed**, 778 deselected, zero failures/skips; 32.28s |
| Complete PostgreSQL-enabled pytest suite | **794 passed**, zero failed/errors/skipped; **94.39s**, one existing Starlette/httpx deprecation warning |
| Baseline comparison | Original Phase 4.1 754; publication baseline 756; Gemini adds 38 cases |
| Ruff lint/format, dependency integrity, Alembic SQL/heads, whitespace | PASS; existing five revisions, no schema/API change |
| Actual Gemini preflight and guarded `--live` | BLOCKED, exit 1, 0 requests; missing key/model and false enable/processing gates |
| Actual Claude / Gemini / Brave requests | **0 / 0 / 0** |

Commands (set `TEST_DATABASE_URL` to a disposable schema-capable PostgreSQL account):

```powershell
python -m pytest -q tests/test_analysis_gemini_integration.py --basetemp=.pytest-gemini-pg
python -m pytest -q --basetemp=.pytest-gemini-complete --tb=short --junitxml=data/local/gemini-tests.xml
python -m ruff check .
python -m ruff format --check .
python -m pip check
python -m alembic heads
python -m alembic upgrade head --sql
git diff --check
```

Live worker/PostgreSQL/API acceptance remains **blocked until the isolated request
succeeds**. Then use a new idle verification database and the same one-course ESCO
copy/inventory from [the Phase 4.1 backend proof](23_PHASE41_REPLIT_CLAUDE.md#separate-worker--postgresql--protected-api-proof).
Select Gemini, replace its Claude preflight with `inspect_gemini_configuration`, use
a new Gemini idempotency key and verify `model_provider=gemini_direct`, actual model/
usage and all citations through protected reads. Its Bash here-doc examples require
PowerShell here-strings on Windows. Keep fixture IDs/source text unchanged for
comparison; historical `claude`/`replit` fixture labels do not select a provider.
Inspect worker/validation failures before retrying and reconcile billing separately.

Brave remains independent and live-unverified: search → permitted registered
original → verified import/query → cited finding is still a separate acceptance
gate. No Brave request occurred. Source permissions, private-upload isolation,
SSRF/robots/research limits and deterministic workforce calculations are preserved.

## Fair comparison with Claude

Gemini deliberately imports the unchanged Phase 4.1 packet builder/permission check,
including original UUIDs; it never invokes Claude. Both use the same source excerpt,
`MODEL_SYSTEM_INSTRUCTION`, `ProgrammeResult`, `validate_result`, one course/one
request and the 4,096-output-token cap. Use identical timeout/policy and compare
canonical packet hashes. Preserve the legacy edition, unknown publication date,
title-only constraints and missing workforce/AI capability evidence. Academic
criteria and the Claude adapter/helper are unchanged.

| Criterion | Shared assessment |
|---|---|
| Evidence fidelity | Human review of supplied-evidence support; no accuracy percentage from one case |
| Unsupported claims | Reject invented IDs/quotes, extra fields, altered inventory, taught-content claims and academic verdicts |
| Citations | Exact admitted ID/quote/scope/rights, with at least one supporting citation exercised |
| Structure | Original Pydantic and grounding rules pass without repair in the isolated request |
| Uncertainty | All five dimensions remain insufficient for this title-only/legacy-benchmark case; syllabus confirmation retained |
| Latency | Same CLI wall-time measurement and timeout for both providers; Gemini provider-only timing is supplemental |
| Tokens | Observed input/output/reasoning/cache/total counts, missing values and provider-accounting differences explicit |
| Cost | Exact-run project/Replit billing observation; any later list-price estimate must be labelled separately |

Gemini additionally requires input/output usage to call verification complete; this
is an observability gate, not different academic grading. Apply the same usage and
insufficiency checks to Claude reports during comparison even though its published
helper does not expose those explicit flags. No live ranking, latency/cost comparison
or Claude live-success claim is available. Stop after Gemini branch publication.
