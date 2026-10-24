# Phase 4 — direct Gemini 4 Argon

Current MVP decision, **24 October 2026**: **Gemini 4 Argon is primary AI,
Google Gemini API is the direct provider, Brave Search is external research, and
Replit remains the official future hosting platform.** Replit AI Integrations and
managed Claude are discontinued for this MVP. Legacy code/tests remain for
compatibility; no Claude development resumes. Development stays in Codex/VS Code;
React/TypeScript and deployment remain future work.

Work continues on **feature/phase4-gemini**, starting at published
`63a7aff5727baa7c1849ce7835c929928dae6c95`. The initial tree was clean. Main,
teammate branches, academic schemas, citation rules, workforce calculations and
migrations are preserved. [STATUS](../STATUS.md) records current checks/publication;
the earlier 794-test/16-PostgreSQL result is historical.

Published tested implementation:
[`107fdfbb776cb7b7d02073ead4ba1ac3aa35445f`](https://github.com/RikoHalim/shift-os/commit/107fdfbb776cb7b7d02073ead4ba1ac3aa35445f).
The remote Gemini ref matched exactly after push; main remained unchanged. A later
documentation-only publication record may be the tip of
[feature/phase4-gemini](https://github.com/RikoHalim/shift-os/tree/feature/phase4-gemini).

## Actual live status and credential handling

**Live Gemini: BLOCKED. Live worker/PostgreSQL/API: BLOCKED pending isolated success.**
There is no local .env; Gemini key/model are absent and enable/processing flags are
false. Zero-call preflight confirms these blockers; ESCO source permission passes.
**No live Gemini, Brave or Claude request was attempted.** Project access, billing
and quotas cannot be established without privately configured credentials/project
access. Actual model, tokens, live latency and observed billing remain unavailable.

A credential appeared in chat. Its value was not copied into configuration, source,
requests, logs, reports or documentation. Revoke/replace exposed keys and enter the
replacement only in ignored local .env or, later, Replit Secrets. Do not paste
credentials into chat or reuse the exposed value.

## Official compatibility and migration

Google's [Argon model page](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon)
documents stable reasoning/structured-output support. The
[Argon migration guidance](https://ai.google.dev/gemini-api/docs/latest-model)
recommends reviewing thinking, token limits and timeouts, removing obsolete sampling/
explicit-cache settings, and documents no free-tier access. It lists a unified
1,048,576-token window and synchronous output up to 65,536. Public documentation
does not prove this project's access or remaining quota.

The [Interactions overview](https://ai.google.dev/gemini-api/docs/interactions)
recommends Interactions and also says generateContent remains supported. This is
a deliberate migration, not a claim that the old endpoint stopped working. The
[API reference](https://ai.google.dev/api/interactions-api) and
[migration mapping](https://ai.google.dev/gemini-api/docs/migrate-to-interactions)
describe a different envelope. We follow the current model-guide/reference
/v1beta/interactions endpoint. Some migration examples show /v1beta2; no automatic
endpoint probing/fallback or paid request resolves documentation inconsistencies.
Actual account/protocol acceptance remains pending.

| Contract | Implemented behavior |
|---|---|
| Endpoint/auth | POST https://generativelanguage.googleapis.com/v1beta/interactions; x-goog-api-key header from GEMINI_API_KEY |
| Input | Explicit model, serialized admitted packet as input, unchanged system_instruction |
| Reasoning | generation_config.thinking_level: medium by default, configurable low/medium/high; thinking_summaries=none |
| Structure | response_format=[{type: text, mime_type: application/json, schema: original Pydantic schema}] |
| State/tools | store=false, background=false, stream=false, tool_choice=none; no tools, agent, prior interaction, polling or continuation |
| Output | Require status=completed; join text from model_output steps; discard thought steps; reject tools/media/unexpected steps/incomplete status |
| Identity | Require a safe returned model equal to the requested code; different models fail visibly |
| Usage | Map usage.total_input_tokens, total_output_tokens, total_thought_tokens, total_cached_tokens and total_tokens into existing safe usage names |
| Errors | Fixed sanitized codes, bounded requests/bytes/time; available model/usage retained on rejected output |

Returned model is the API-reported identity, not a separately resolved backend-version
identifier. Old candidates/parts/camelCase responses are not treated as Interactions
results. Original Pydantic and quote/scope/rights/course-coverage validation remain
mandatory. No academic schema is relaxed. Google's
[structured-output guide](https://ai.google.dev/gemini-api/docs/structured-output)
documents schema subset/complexity limits; actual service acceptance remains unproven.

## Required local configuration

Inspect .env.example and configure these in ignored .env yourself:

```dotenv
ANALYSIS_MODEL_PROVIDER=gemini
GEMINI_ENABLED=true
GEMINI_API_KEY=<PRIVATE_REPLACEMENT_KEY_SET_LOCALLY>
GEMINI_MODEL=gemini-4-argon
GEMINI_THINKING_LEVEL=medium
GEMINI_MAX_OUTPUT_TOKENS=32768
GEMINI_TIMEOUT_SECONDS=180
ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=true
ANALYSIS_PROVIDER_MAX_ATTEMPTS=1
ANALYSIS_GEMINI_FALLBACK_ENABLED=false
ANALYSIS_PERMISSIONS_PATH=data/analysis_permissions.json
CLAUDE_ENABLED=false
RESEARCH_ENABLED=false
```

Use a real authorized replacement credential, not the placeholder. Keep DATABASE_URL
valid for PostgreSQL/psycopg settings; no database is constructed by preflight/the
isolated helper. Set a private nonempty ANALYSIS_WRITE_TOKEN for later protected
API reads/writes. Source permission is independent; a key does not grant rights.

In the actual Google project, verify Argon access, active paid billing and
[project quotas](https://ai.google.dev/gemini-api/docs/rate-limits) before spending.
A consumer Google AI subscription does not establish API credits; review
[API billing](https://ai.google.dev/gemini-api/docs/billing) and
[pricing](https://ai.google.dev/gemini-api/docs/pricing). Prices are not observed charges.

[Google data-use terms](https://ai.google.dev/gemini-api/terms) differ for paid/unpaid
services. Store=false opts out of Interactions history storage; it does not replace
provider abuse-monitoring/retention terms or source/privacy approval. The helper
includes one fictional course and the permitted, attributed ESCO excerpt, excluding
private real curricula and restricted MQA documents.

## Bounded verification

First run local inspection; it constructs no provider/database and makes zero requests:

```powershell
python -m shiftos.cli verify-gemini --report data/local/argon-preflight.json
```

Stop when blocked. Once credentials, source permission, project access and billing
are ready, one explicitly authorized call is:

```powershell
python -m shiftos.cli verify-gemini --live --report data/local/argon-verification.json
```

The helper forces **one HTTP attempt**, no repair/search/other provider, and at most
**32,768 total thinking/output tokens**, further limited by GEMINI_MAX_OUTPUT_TOKENS.
The old 4,096 cap was raised because Argon migration guidance recommends at least
32,768 when an application previously used smaller budgets. This is a ceiling,
not claimed consumption. Academic criteria and the exact one-course ESCO packet/
UUIDs are unchanged. Its shared packet builder remains in the legacy Claude helper;
importing that input fixture never constructs/calls Claude.

Normal output bounds: 1–65,536, default 32,768. GEMINI_TIMEOUT_SECONDS: 1–300, default
180. The worker's remaining 600-second deadline also applies; byte limits remain
1,000,000 per request/response. Normal worker transport retries (1–3) and one
validation repair are separate from the one-attempt helper. The timeout override
does not change Claude/Brave timeout behavior. This synchronous 180-second bound is
deliberately narrower than Google's long/hard-prompt guidance; difficult batches
may time out and remain PARTIAL rather than run indefinitely.

Verification requires actual model identity, one request, original schema/grounding,
at least one supported citation, syllabus confirmation, all five dimensions
insufficient on this title-only/legacy case, and observed input/output tokens.
Reports include available thought/cache/total tokens, latency, hashes and bounds.
Cost stays unknown without billing evidence. Export failure preserves safe activity/
usage in stdout. Diagnose failure before authorizing another paid request.

## Backend verification and remaining gates

[STATUS](../STATUS.md) records current measured tests. Real PostgreSQL cases use the
actual Interactions adapter with mocked HTTP: synthetic Accounting inventory,
internal academic/AI/workforce admission, sufficiency gaps, schema/citations,
deterministic programme insights, committed findings/usage/configuration/latency,
protected API and no-call replay. An independent connection verifies commits.
Authentication/citation failures preserve every course as PARTIAL/insufficient.
Existing genuine ESCO provenance cases remain. These checks establish software
behavior, not live provider acceptance or academic accuracy.

Existing manifest JSON now also admits sanitized Gemini API/thinking/token-budget/
timeout/latency metadata. No table, route or academic schema changes/migration are
needed; existing revisions 0001–0005 and deterministic workforce calculations remain.

After isolated live success, use a new idle verification PostgreSQL database with
synthetic academic records and permitted imports. The historical
[one-course dataset preparation](23_PHASE41_REPLIT_CLAUDE.md#separate-worker--postgresql--protected-api-proof)
can be reused as data preparation only: use current Gemini settings and
inspect_gemini_configuration, not managed Anthropic setup. Submit with a new
idempotency key, run the separate worker, confirm its exact job ID, then retrieve
the run/every course through protected endpoints. Require gemini_direct, actual
Argon model, supported quotes/rights/uncertainty, usage/configuration and committed
rows. Isolated success alone does not prove this live backend gate.

Brave remains independent and pending without BRAVE_SEARCH_API_KEY and explicit
RESEARCH_ENABLED approval. Respect acquisition/source policies and subscription
rights for bounded search → registered original → verified import/query → citation.
Snippets/model memory are never evidence; private uploads never enter public search.

The [Replit hosting plan](25_REPLIT_HOSTING_PLAN.md) assesses future compatibility.
No deployment, frontend, merge or Phase 5/6 work occurs here. Close Phase 4 live
acceptance before treating Phase 5 as unblocked. Syllabus, currentness, coverage,
occupation-identity and organiser-waiver limits remain.
