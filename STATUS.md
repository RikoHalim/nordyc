# SHIFT//OS — implementation status

**As of 2026-10-24:** Primary AI is **Gemini 4 Argon via direct Google Gemini Interactions**, initially medium thinking; **Brave Search** remains research and **Replit** remains official future hosting. Replit AI Integrations/managed Claude are **DISCONTINUED for this MVP**; legacy code remains for compatibility. Phase 4 is **FUNCTIONAL OFFLINE**, with **816 passed**, including **16 PostgreSQL integration cases**, zero failures/skips, versus the previous 794-test Gemini baseline. **Live Gemini and live end-to-end verification are BLOCKED:** no local `.env`/key/model, enable/processing flags false; this run performed only zero-call preflight. Actual model/tokens/live latency/billing remain **none observed/unavailable**; project access/billing/quota are unverified. No posted credential was used or copied. Only `feature/phase4-gemini` is authorized for publication; no merge, teammate-branch changes, deployment, frontend or Phase 5/6 work.

**Pilot target:** all publicly discoverable XMUM undergraduate programme/course lists. The directory parser found 25 official undergraduate links. Production live retrieval **failed safely** in this environment because `www.xmu.edu.my` resolved to a private network address; no live crawl success is claimed. A separate reviewed manual fallback stored 25 directory programme facts and **141 course appearances across three programmes** in a disposable local PostgreSQL database, retrieved through real FastAPI HTTP. The remaining 22 programmes have no loaded course inventory in that validation database. None of these records certify a complete graduation curriculum or lecturer-taught content.

| Phase | Revised deliverable | Status |
|---|---|---|
| 1 | FastAPI/PostgreSQL multi-institution foundation, provenance, migrations and tests | COMPLETE |
| 2 | XMUM discovery/parser, year/elective extraction, safe import/versioning, worker, APIs and coverage | COMPLETE — live network blocked; reviewed manual fallback verified |
| 3 | Evidence acquisition, workforce radar and independent AI task evidence | FUNCTIONAL — bounded evidence gates met; legacy/language/currentness/permission limits explicit |
| 4 | Internal-first retrieval, controlled Brave research and conservative whole-programme screening | FUNCTIONAL OFFLINE — live provider/backend acceptance BLOCKED |
| 4.1 | Historical managed Claude | DISCONTINUED for MVP; legacy code/tests preserved, no live success claimed |
| 4 Gemini branch | Direct Argon Interactions, medium thinking/configurable limits, same academic fixture/schema and protected backend | OFFLINE VERIFIED — 816 passed; live Gemini/backend BLOCKED |
| 5 | Future Career Alignment, competency-gap review, minimum sufficient actions, alternatives/no change and human review | PENDING — requirements revised only |
| 6 | Ordered Academic Reskilling Pathways, scenarios/SDGs/resources/duration and consolidated Action Plans | PENDING — requirements revised only |
| 7 | Integration, evaluation, change replay and security | PENDING |
| 8 | Minimal working dashboard and preliminary demo | PENDING |

## Gemini 4 Argon Interactions and Phase 4 verification — 24 October 2026

This request fixes the current stack: local Codex/VS Code development, GitHub,
FastAPI/Python, PostgreSQL/SQLAlchemy/Alembic, **Google Gemini API directly with
`gemini-4-argon`**, Brave research, React/TypeScript later, and **Replit hosting later**.
Managed Claude is discontinued; code/tests remain without further development.
Starting branch `feature/phase4-gemini` at published
`63a7aff5727baa7c1849ce7835c929928dae6c95` was clean. No reset/stash, main change,
teammate-branch operation, merge, force push or deployment was performed.

Official Argon/Interactions/migration documentation was checked. The Gemini adapter
now posts stateless synchronous `/v1beta/interactions` with existing server-side key
authentication, unchanged academic instructions/schema, `response_format`, medium
thinking by default and no tools/agent/background/polling/history. It parses model
output steps, discards thoughts, maps the new usage fields, rejects legacy envelopes,
incomplete/tools/unexpected content and mismatched returned models. API-reported
identity is not described as a separately resolved backend model version.

New settings: `GEMINI_THINKING_LEVEL=medium` (low/medium/high),
`GEMINI_MAX_OUTPUT_TOKENS=32768` (1–65536), `GEMINI_TIMEOUT_SECONDS=180` (1–300).
The helper forces one attempt and caps at 32768 total thinking/output tokens;
the previous 4096 cap was raised following Argon's migration guidance. This is a
maximum, not observed usage. The existing worker's remaining 600-second deadline,
course/repair limits and byte caps still apply. A small optional transport timeout
override supports Gemini; Claude/Brave retain previous timeout behavior. Existing
manifest JSON now admits sanitized Gemini API/thinking/budget/timeout/latency fields,
including on failed output. No academic schema, HTTP route, table, dependency or
migration change; no workforce-math or evidence-rule change. All five Alembic
revisions through `0005_programme_analysis` remain.

| Current check | Actual result |
|---|---|
| Complete `python -m pytest -q --basetemp=.pytest-argon-complete --tb=short --junitxml=data/local/argon-tests.xml` with disposable PostgreSQL | **816 passed, 0 failed/errors/skipped, 93.78s**, one existing Starlette/httpx deprecation warning |
| Baseline comparison | Previous Gemini **794** preserved; **22** new Interactions/thinking/identity/status/tool/deadline/audit cases |
| Targeted Gemini/provider/legacy compatibility/academic validation/source-permission tests | **246 passed**, 6.21s, mocked/offline only |
| PostgreSQL coverage | **16 cases** in complete suite; real PostgreSQL, mocked provider HTTP |
| Separate `python -m pytest -q -m integration --basetemp=.pytest-argon-integration --tb=short --junitxml=data/local/argon-integration-tests.xml` | **16 passed, 800 deselected, 0 failures/skips, 34.79s** |
| Course pipeline/API proof | Synthetic inventory + academic/AI/workforce retrieval/admission → Interactions adapter → schema/citations/uncertainty → deterministic programme insights → committed findings/configuration/usage/latency → protected FastAPI and idempotent no-call replay; independent connection verifies commits |
| Actual `verify-gemini --report data/local/argon-preflight.json` | **BLOCKED**, exit 1, **0 requests**; no `.env`/key/model, false enable/processing; ESCO permission passes |
| Actual live Gemini / live end-to-end | **BLOCKED / BLOCKED**, no request attempted; full live backend waits for isolated success |
| Actual model / tokens / live latency / observed cost | **None observed / unavailable / unavailable / unavailable** |
| Google project access / paid billing / quota | **Unverified** without private configuration/project access; no consumer-subscription credit assumption |
| Brave | Adapter/rules preserved; no credential, live search → original → import/query → citation **PENDING** |
| Ruff lint/format / dependency integrity / Alembic heads+SQL / whitespace | **PASS** |
| Documentation links/fences/UTF-8 | **PASS**, 9 Markdown files, 71 local links/anchors |

The initial targeted selection had 147 passed and one PostgreSQL case skipped before
`TEST_DATABASE_URL` was set. The complete PostgreSQL-enabled run above includes all
cases with zero skips. No test failure is accepted. Tests/mocked metadata do not
establish real academic accuracy, service availability, billing or teaching content.

The user supplied a credential in chat; it was not copied to configuration/source/
requests/logs/reports/docs or used. The user must revoke/replace that exposed key
and configure the replacement only in ignored local `.env`. Required settings and
paid-project/source-privacy checks are in [the Gemini runbook](docs/24_PHASE4_GEMINI.md).
Do not make a live call until missing configuration is resolved; diagnose any first
failure before another paid request. Real private curricula are excluded from the
synthetic check. Provider state storage is disabled, but applicable retention/use
terms still require review.

[Replit hosting preparation](docs/25_REPLIT_HOSTING_PLAN.md) covers Secrets, direct
Google/Brave egress, PostgreSQL/psycopg/TLS, explicit release migrations, separate
FastAPI/worker processes, limits, private storage and sanitized logging. Architecture
is portable; **no actual Replit deployment/runtime acceptance** is claimed. Local
PostgreSQL/private files do not transfer through Git. Only the disposable loopback
test cluster/random test schemas were used, not an application/user database.

**Phase 5 recommendation: do not begin implementation yet.** First close the actual
Argon isolated request and live worker/PostgreSQL/protected-API gates, and retain
Brave/evidence/currentness/syllabus/occupation-identity and organiser-waiver limits.
Later source/action coverage must not be inferred from passing software tests.
**Publication: SUCCEEDED.** Reviewed implementation
[`107fdfbb776cb7b7d02073ead4ba1ac3aa35445f`](https://github.com/RikoHalim/shift-os/commit/107fdfbb776cb7b7d02073ead4ba1ac3aa35445f),
`feat: migrate Gemini 4 Argon to stateless Interactions API`, was pushed to
**`origin/feature/phase4-gemini`**. The remote ref returned that exact SHA after push;
remote `main` remained `164255d52b5ceb005647ec670506f10cb5054b10`, and no teammate
branch was changed. Exactly 18 relevant code/test/example/documentation files were
staged; scope, credential-pattern and whitespace checks passed. Private/local reports,
runtime/database files, real credentials and unrelated assets were excluded. AST/diff
checks confirm Claude/Brave adapters, academic schema/validator, shared input fixture
and workforce calculations are preserved. This is a documentation-only publication
follow-up; the final branch tip can include it without changing tested code. No
merge, force push, deployment or Phase 5/6 implementation occurred. Stop here.

**Next recommended prompt:** “Read AGENTS.md, STATUS.md and docs/24_PHASE4_GEMINI.md.
I privately configured a replacement Google key, Argon model access/billing/quota
and source-processing settings in local .env. Run preflight, then one bounded
synthetic Argon Interactions request with medium thinking. Diagnose failures before
any retry. Only after isolated success verify worker → PostgreSQL → protected API,
record actual identity/usage/latency/citations/billing when observed, update docs
and publish only feature/phase4-gemini. No merge, deployment or Phase 5/6.”

## Dedicated Gemini branch — historical 24 October 2026 publication

Shared base: fetched/published `main` at **`164255d52b5ceb005647ec670506f10cb5054b10`**.
Phase 4 `b586194` and Phase 4.1 implementation `ec9b7f79ea26760a75f84e3c98cef8d4ce71bcfb`
are already in that history. The working tree was clean. Created **`feature/phase4-gemini`**
from this stable base; no uncommitted work was reset/discarded. The teammate's
`feature/phase4-replit-claude` was absent from the inspected remote listing and was
not created, modified, deleted, overwritten or merged. Local `main` is unchanged.
This request supersedes historical no-publication instructions only for this branch.

Delivered [Gemini runbook](docs/24_PHASE4_GEMINI.md) and `verify-gemini` CLI with a
zero-call preflight and explicit one-attempt synthetic live check. It reuses the
exact published Claude packet builder/UUIDs, genuine attributed ESCO skill excerpt,
source-permission check, instruction, academic Pydantic schema and grounding rules.
It does not invoke Claude. No comparative accuracy/performance ranking is claimed.
Usage/latency/hashes and actual request limits are reported safely; missing billing
stays unknown. One supported citation plus title-only insufficiency must be exercised.

The existing direct Gemini adapter now configures output tokens (1–16,384; helper
caps at 4,096), requests one candidate, requires an actual returned Gemini identity,
discards thoughts and rejects malformed/tool/multiple-candidate output. Existing
provider timeout/retry/byte limits and worker validation repair remain. No dependency,
database/academic schema, HTTP endpoint, migration, Claude/Brave adapter or evidence
grading rule changed. Existing JSON manifests already persist model/token outcomes.

| Verification | Actual measured result |
|---|---|
| Complete `python -m pytest -q --basetemp=.pytest-gemini-complete --tb=short --junitxml=data/local/gemini-tests.xml` with disposable PostgreSQL `TEST_DATABASE_URL` | **794 passed, zero failures/errors/skips, 94.39s**; one existing upstream Starlette/httpx deprecation warning |
| PostgreSQL cases included | **16**, versus published 13; new cases use the actual Gemini adapter with mocked HTTP for success, invalid citations and rejected authentication |
| Separate `python -m pytest -q -m integration --basetemp=.pytest-gemini-integration --tb=short --junitxml=data/local/gemini-integration-tests.xml` | **16 passed, 778 deselected, zero failures/skips, 32.28s** |
| Existing provider/Claude targeted regressions | **125 passed** |
| Gemini-specific helper/CLI / new PostgreSQL checks | **35 / 3 passed**; synthetic response metadata, never live observations |
| Backend proof | Three-course synthetic Accounting inventory; internal academic/AI/workforce retrieval/admission, schema/grounding, deterministic summary/unknowns, complete committed findings, actual-model/usage metadata, protected API and no-call idempotent replay; independent PostgreSQL connection confirms commits |
| Ruff lint / formatting / dependency integrity | **PASS** |
| Alembic SQL / heads / migration suite / whitespace | **PASS**, existing five revisions through `0005_programme_analysis`; no new migration or application database change |
| Documentation checks | **PASS**, five Markdown files, 48 local links/anchors, balanced fences and UTF-8 |
| Actual Gemini preflight / guarded `--live` | **BLOCKED**, exit 1, **0 requests**; key/model missing, enable/external-processing false; ESCO permission passes |
| Preferred model / actual model | Officially documented stable **`gemini-4-argon`** / **none observed**; selection rationale and alternative identifiers in runbook |
| Actual input/output/thought tokens / live latency / observed charge | **Unavailable / unavailable / unavailable**, not estimated or inferred from mocks |
| Actual live Claude / Gemini / Brave requests | **0 / 0 / 0**; none independently verified |

Environment: Windows, Python **3.13.13**, fresh project virtual environment installed
from the existing lock and editable dev requirements, disposable loopback PostgreSQL
**16.15** on port 55434. Automated cases create/drop random `shiftos_test_*` schemas.
No existing application/user database was migrated. Ignored local reports, binary
runtime/cluster, credentials/private source material and unrelated assets are excluded
from Git. The historical 754 baseline became 756 through two earlier report-export
regressions; this branch adds 38 cases, preserving all existing tests.

**Live blockers:** configure an API-authorized Gemini key/model and project quota/billing,
approve the actual external-processing terms/settings, then run one controlled real
request. A consumer Google AI subscription does not prove API credits. Only after
isolated success perform the live worker/PostgreSQL/protected-API proof; current
database results used mocked HTTP. Brave's independent search → permitted original →
verified import/query → citation gate remains pending. Claude is not verified by
Gemini results. Currentness/coverage/syllabus/occupation-identity limits and the
organiser waiver gap below remain unchanged.

**GitHub publication: SUCCEEDED.** Implementation commit
[`c95384004e9563f3f00e2d69d8936aef7ec0956b`](https://github.com/RikoHalim/shift-os/commit/c95384004e9563f3f00e2d69d8936aef7ec0956b),
`feat: add bounded direct Gemini verification and backend regression checks`, was
pushed to **[`origin/feature/phase4-gemini`](https://github.com/RikoHalim/shift-os/tree/feature/phase4-gemini)**.
`git ls-remote --heads` returned that exact SHA after push; remote `main` still
returned `164255d52b5ceb005647ec670506f10cb5054b10`, and no teammate Claude branch
was present or changed. The commit contains exactly **14 reviewed Gemini-related
files**. Staged scope/whitespace/secret-pattern checks passed; private/local files
and unrelated assets were excluded. AST comparison confirms Claude, Brave and shared
HTTP transport are unchanged. This publication record is a documentation-only
follow-up; the final branch tip may include it without changing the tested code.
No merge, force push, application deployment or later-phase implementation occurred.
Stop here.

**Next recommended prompt:** “Read AGENTS.md, STATUS.md and docs/24_PHASE4_GEMINI.md.
On feature/phase4-gemini, with privately configured API credentials and approved
source/processing policy, run one synthetic Gemini request, record actual model,
citations, uncertainty, usage/latency/billing, then verify worker → PostgreSQL →
protected API. Keep the exact Claude comparison fixture and report any blockers.
Do not merge, deploy, start Phase 5/6 or claim curriculum accuracy.”

## Phase 4.1 final verification, publication and Replit handover — 24 October 2026

The final-verification request explicitly authorizes committing and pushing Phase 4.1 to the existing SHIFT//OS GitHub repository. This supersedes the original Phase 4.1 no-publication boundary below. Remote `origin` is `https://github.com/RikoHalim/shift-os.git`; fetched `main` matched local `b586194` with no teammate divergence before publication preparation. Only the 19 reviewed Phase 4.1 implementation/configuration/test/documentation paths are approved for this commit. Existing IDE/design assets are unchanged and excluded; real `.env` files, credentials, private/restricted documents, local databases/reports, caches and temporary files are excluded. No credential pattern or actual local credential value was detected in the approved publication content. Staged-content checks are required before commit.

One genuine defect was fixed conservatively: failure to export a Claude report after a model request could replace the completed activity/usage with an incorrect zero-request blocked result. The CLI now preserves the original outcome, actual model/usage/request count in stdout, adds a sanitized report-export failure flag/code, and returns exit1. Two mocked mkdir/write regression cases raise the previous **754** tests to **756**, without changing academic contracts or provider privacy/retrieval behavior.

| Final local check | Measured result |
|---|---|
| Complete `python -m pytest -q --basetemp=.pytest-phase41-publication --tb=short --junitxml=data/local/phase41-publication-tests.xml` with disposable PostgreSQL `TEST_DATABASE_URL` | **756 passed, zero failures/errors/skips**, **78.82s**; one pre-existing Starlette/httpx deprecation warning |
| PostgreSQL integration | **13 passed**, including migration/history, source/radar/curriculum persistence, worker → protected API and independently committed Claude-selected model/usage records with mocked responses |
| `ruff check .` / `ruff format --check .` / `pip check` | **PASS** |
| `alembic upgrade head --sql` / live disposable migration tests / `git diff --check` | **PASS**, existing five revisions; no new Phase 4.1 schema change |
| Documentation validation | **PASS**, 9 Markdown files, 68 local links/anchors, balanced fences and UTF-8 |
| Offline `verify-claude --report data/local/phase41-publication-preflight.json` | **BLOCKED**, expected exit1, **0 requests**; source permission passes but managed credential/endpoint and enable/processing gates are absent/false |
| Replit handover examples checked locally | **PASS**: five Python examples compile; one fictional course, 87 genuine existing-pack records, one attributed synthetic-lane skill copy and exact quoted source retrieval verified in a disposable PostgreSQL schema, then cleaned up; no external acquisition/model/search requests |
| Live Claude / Gemini / Brave requests in this verification | **0 / 0 / 0**; actual Claude model **none observed**, actual billed cost **unavailable** |

Replit handover is in [the existing runbook](docs/23_PHASE41_REPLIT_CLAUDE.md#replit-handover): import/synchronize the published branch, install pinned dependencies, provision an isolated PostgreSQL database, apply migrations, approve the actual managed Anthropic integration, map its real server-side configuration, preflight, one bounded synthetic-course live request, actual model/token/billing checks, then separate worker/database/protected-API proof. Local PostgreSQL datasets do not transfer through Git; only explicitly permitted packs and synthetic fixtures can be imported using documented commands. Gemini remains optional/disabled until separately configured and tested; Brave live search → original verification/import/cited finding remains unverified.

**GitHub publication: SUCCEEDED.** Implementation commit [ec9b7f79ea26760a75f84e3c98cef8d4ce71bcfb](https://github.com/RikoHalim/shift-os/commit/ec9b7f79ea26760a75f84e3c98cef8d4ce71bcfb), message `feat: complete phase 4.1 Replit-managed Claude integration`, was pushed to **`origin/main`**. A subsequent `git ls-remote --heads origin refs/heads/main` returned that exact SHA; local/remote divergence was **0 / 0** immediately after the implementation push. The commit contains exactly **19 reviewed files**: five backend/configuration modules, four new test modules, nine Markdown documents and `.env.example`. The staged-content audit found no secrets/private or unapproved files, and staged whitespace passed. Existing tracked IDE/design files are unchanged and absent from this commit; ignored credentials, data and local reports were not staged. This publication record is a documentation-only follow-up to that verified implementation; current `main` can include this later record without changing the tested code.

No public application deployment, branch merge, force push or Phase 5–8 implementation occurred. Remaining gates are actual Replit managed access/model/protocol/citation/persistence/billing verification, live permitted research where needed, and existing source-currentness/coverage/identity/syllabus and organiser-scope limits. Stop after publication and handover.

## Phase 4.1 managed Claude — original local verification, 24 October 2026

Starting checkout is `main` at `b586194` (`push phase 4`). The existing Phase 1–4 implementation and academic result schemas are retained. The latest instruction authorizes Phase 4.1 only and explicitly prohibits automatic Git publication/deployment or Phase 5/6 implementation; no prior push request was resumed.

Delivered [Phase 4.1 runbook](docs/23_PHASE41_REPLIT_CLAUDE.md): a bounded Anthropic Messages adapter uses only Replit-managed credential/base-URL settings, configurable `CLAUDE_MODEL` (preferred `claude-opus-5`) and the existing external-processing/source-rights gates. Gemini remains the compatible default; operators explicitly select `replit_claude`. Optional Gemini fallback is disabled by default, applies only to Claude operational failures, retains independent Gemini enable/configuration checks and is disclosed as PARTIAL. Authentication/privacy/configuration/schema/citation failures cannot trigger cross-provider fallback. Structured-output transport compatibility preserves full local Pydantic/citation validation; thinking blocks are discarded and tools/unsupported responses rejected.

Existing JSON manifests/job results retain whitelisted actual returned models, token counts, HTTP-attempt counts, response/validation errors and fallback transitions separately from the selected model and adapter invocation count. Actual model names are not inferred from configuration. Failed publication after a response preserves safe usage while the job is still running, without source text/findings; stale workers cannot overwrite terminated jobs. Abrupt termination can still require external billing reconciliation. No new tables, migrations, HTTP endpoints, dependencies, training, research agents or academic analysis contracts were introduced. Workforce arithmetic/retrieval and protected API/source revalidation are retained.

Actual `verify-claude --report data/local/phase41-claude-preflight.json` returned **blocked**, exit1, **0 provider requests**: Claude disabled, external processing not approved, managed credential missing, managed base URL missing. This is a configuration inspection, not a failed authentication attempt or proof that Replit's service is unavailable. Replit's published catalogue lists `claude-opus-5` and several older Opus alternatives (linked in the runbook); none was queried in this workspace. User response: **“Finish locally; document the live-test blocker.”** No private university documents or real source material were sent to a model.

The explicit `verify-claude --live` helper is ready for a later authorized Replit run: one labelled fictional irrigation course, one genuine attributed ESCO skill excerpt, one transport attempt, capped output, no fallback/repair/search, original schema plus supporting-citation validation. The copied verification lane is marked synthetic; the source's real identifiers, exact text, legacy/unknown-date limitations, partial-artifact hashes and attribution are retained. Explicit C-ESCO-V103 source-processing grants are checked before provider construction. No invented authority or university syllabus is used. The helper reports actual model/token usage and leaves cost unknown without a billing observation. This isolated helper is distinct from the worker/PostgreSQL/API proof. Live calls in this task: **Claude 0 / Gemini 0 / Brave 0**; observed actual model **none**; observed billed cost **unavailable**, not a fabricated token-price estimate.

| Verification | Actual measured result |
|---|---|
| Complete `python -m pytest -q --basetemp=.pytest-phase41-verified --tb=short --junitxml=data/local/phase41-tests.xml` with disposable `TEST_DATABASE_URL` | **754 passed, zero failed/errors/skipped**, **66.23s**; one existing Starlette/httpx deprecation warning |
| PostgreSQL cases included | **13 passed**; retained migration/history/radar/curriculum/analysis checks plus Claude-selected worker → protected API → independently committed PostgreSQL model/usage proof, using explicitly mocked model responses |
| Claude transport/configuration/output and academic regressions | Managed aliases, endpoint security, bounded attempts/bytes/time, schema compatibility, thinking discard, errors, exact citations, actual-model/usage sanitization, explicit fallback, offline no-call, source policy and genuine ESCO excerpt provenance passed |
| Publication failure/cancellation accounting | Policy-change failures retain safe usage without findings/text; terminated jobs reject late writes |
| Actual local Claude preflight | **BLOCKED**, exit1, **0 requests**; processing/enable gates false and managed credential/endpoint absent; genuine ESCO use is permitted by the existing source policy |
| Actual live Claude model / billing | **None observed / unavailable**; no live-model, preferred-model performance or cost claim from mocks |
| Ruff lint / format / dependency integrity | **PASS** (`ruff check .`, `ruff format --check .`, `pip check`) |
| Migration / whitespace | **PASS** (`alembic upgrade head --sql`, `git diff --check`); existing five revisions only, no Phase 4.1 migration |

The initial complete regression run caught one new PostgreSQL fixture failure (742 passed/1 failed): a test held an outer transaction open over worker sessions and rolled their changes back before its API read. Correcting the test to close submission sessions before worker execution resolved it; an independent PostgreSQL connection confirms committed status/usage. A complete 743-test rerun passed, followed by the final 754-test pass after replacing the smoke's fictional benchmark with genuine ESCO evidence and adding source-policy/error regressions. No remaining automated regression was observed. These mocked integration checks do not establish real Claude service compatibility.

Changed implementation: `core/config.py`, `services/analysis/providers.py`, `orchestrator.py`, new `claude_verification.py`, and `cli.py`; four new Claude provider/worker/helper/CLI test modules. Updated `.env.example`, README, architecture/data/API/test/roadmap/Phase 4 docs and the new Phase 4.1 runbook. Local preflight/JUnit/migration/verification reports remain ignored under `data/local`. Documentation validation **PASS: 9 Markdown files, 65 local links/anchors, balanced fences and UTF-8**. No new genuine dataset download/import or private data publication occurred.

**Readiness:** local adapter and conservative fallback are implemented; **Phase 4.1 is not fully live-verified**. Replit must actually provision managed Anthropic access, then the synthetic real request and genuine worker → PostgreSQL → protected API check must pass with returned model, citations and usage. Live Brave research remains a separate Phase 4 gate. Stop here; do not start Phase 5/6.

## Phase 4 publication authorization — 24 October 2026

After implementation and the planning revision, the user explicitly requested a GitHub push. This publication includes the completed Phase 4 backend, tests/migration and Phase 5–6 planning updates. Earlier no-commit/push statements describe their original stop boundaries; the later explicit request authorizes this publication only, not later-phase implementation or deployment.

Final publication checks passed: Ruff lint/formatting, dependency integrity, whitespace and remote-branch synchronization. The complete Phase 4 suite already passed 637 tests, including 12 PostgreSQL integration tests, as recorded below. Live Gemini/Brave verification remains pending. Private/local source material, database files, editor settings and unrelated visual-concept work are excluded from the publication.

## Phase 4 implementation and measured verification — 24 October 2026

The latest attached implementation request authorized Phase 4 only, and the subsequent enhancement request explicitly preserved that priority while revising later-phase documentation. Starting checkout `main`/`1585b9e` matched `origin/main`; completed Phase 3 code and the revised retrieval specifications were present. The initial full PostgreSQL baseline passed 487 tests before code changes. The previous conditional publication authorization does not apply to this work: both current requests prohibit automatic commit/push.

Delivered [runbook](docs/21_PHASE4_COURSE_RELEVANCE.md): existing background worker now processes `PROGRAMME_ANALYSIS`; explicit CLI and protected asynchronous API submissions freeze the selected revision/inventory. All courses have five structured screening dimensions, exact scoped citations, safe review questions, limits and deterministic programme insights. Internal retrieval includes source-attributed standards, occupations/skills/relations/tasks, workforce observations and independent AI evidence; conservative lexical associations never prove taught competencies or reviewed identities. Strict output validation rejects missing/extra courses, invented/unsupported citations, scores and obsolete/replacement claims. Missing content/evidence retains insufficient-evidence and syllabus-confirmation states.

Direct Gemini and Brave adapters use fixed endpoints, explicit credentials/configuration, finite attempts/time/bytes and sanitized errors. Research uses only generic policy-controlled discipline/gap queries, then exact registered permitted originals through Phase 3 adapters; no snippets/private uploads are admitted as evidence. Unknown/ambiguous sources stay manual/candidates. Permission-aware metadata caching, immutable source/run lineage and current read-time policy/rejection/correction checks preserve provenance and withhold text requiring revalidation. The original deterministic workforce calculations remain unchanged. No Replit AI Integration or additional runtime agent/model was added.

Additive `0005_programme_analysis` adds only `analysis_runs`, `course_findings`, `research_cache`; the first four revisions are unchanged. Composite constraints enforce course/revision ownership. Existing jobs provide idempotency, state/times and explicit stale-worker recovery; atomic completion fencing prevents late writes. All new analysis reads/writes, including legacy job reads for analysis jobs, require `X-Analysis-Token`; this operator token is not full production tenant identity.

| Verification | Actual measured result |
|---|---|
| Initial complete PostgreSQL baseline | **487 passed**, zero skips; 54.47s; one existing upstream warning |
| Final `python -m pytest -q --basetemp=.pytest-phase4-release --tb=short` with explicit disposable `TEST_DATABASE_URL` | **637 passed, zero failed/skipped**, 73.17s; one existing Starlette/httpx deprecation warning |
| PostgreSQL integration included in the complete suite | **12 passed**, including clean/history/guarded migrations and worker→protected API across Computing, Accounting and Marine Biotechnology synthetic fixtures |
| Genuine ESCO reference-pack retrieval regression | **87 genuine normalized records imported/queried** against an explicitly fictional engineering fixture; exact source URI/labels/relations and legacy/language limits retained |
| Genuine Accounting CLI/API/worker smoke in isolated database copy | **37/37 actual course appearances returned; 57 source-linked references, all57 internally eligible, 51 model/output eligible**; HTTP202 queue, protected200 reads, unauthorized401, idempotent replay unchanged |
| Accounting interpretation | All37 retain insufficient content evidence; genuine `deterministic_insufficiency`, no false synthetic or Gemini-success claim |
| Actual live Gemini calls / Brave calls | **0 / 0**; neither key/model configured; user chose offline tests. Mocked adapter/retry/schema/search→original import/cache tests passed; these are not live API verification |
| Ruff lint / formatting | **PASS** |
| Dependency integrity / migration SQL / whitespace | **PASS**; all five PostgreSQL revisions generate; `git diff --check` clean |

The real smoke used an isolated `shiftos_phase4_validation_fc15f950` copy of the prior disposable Phase 3 database; no application/user database was migrated. Prior source counts across 22 public-schema tables were preserved. Final smoke run `931de6a9-26bf-49ce-8864-e20268fb7c36` retained fingerprint `a1d32abb16e5afe0400e8c554b06f7bfefc2730743caf33611016b51eeffefaa`; ignored local reports preserve the detailed checks. No new genuine external dataset was downloaded by Phase 4. Only Accounting had an active genuine course inventory in this copied database; other real programme inventories mentioned in the historical Phase 2 handoff were not assumed to exist here. Cross-disciplinary worker validation used labelled synthetic fixtures plus genuine ESCO evidence where available.

Checks caught an old Phase 1 assertion that analysis routes must not exist; it was updated to the now-authorized contract, then the full suite passed. Review also closed an analysis-job authorization bypass and added changed-policy/source revalidation tests. Source/date/review/permission gates remain conservative; frozen historical cutoffs do not reconstruct every earlier mutable operator-review decision. No remote CI, live model quality/accuracy, complete current taxonomy, semantic curriculum mapping, general syllabus extraction or academic decision readiness is claimed.

**Readiness:** bounded offline Phase 4 works. Full live Phase 4 acceptance is incomplete until one configured Gemini model and Brave are actually verified through permitted originals/imports/citations; current source coverage, exact Malaysian occupation bridges and verified curriculum content also remain limitations. Do not start Phase 5 implementation automatically. No commit/push or deployment was performed; unrelated local visual-concept/editor work is preserved.

## MVP enhancement and Domain 1 planning revision — 24 October 2026

[The integrated plan](docs/22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md) revises product requirements, architecture/database/API targets, Phase 5/6 specs/prompts, MVP checklist, compliance matrix, tests and roadmap. **Documentation only for these additions:** Phase 4 remains the development priority; no Phase 5/6 code or migration was added.

- **Phase 5:** programme-level Future Career Alignment compares reviewed occupation/skill requirements with curriculum-supported competencies and potential gaps; distinguishes documented intent, assessed demonstration and unknown coverage. Optional deterministic scoring requires explicit method/weights/denominator/missingness and is never employment probability. Primary recommendations compare the minimum sufficient intervention, alternatives/no change and human review.
- **Phase 6:** ordered academic pathways within scenario/report/Academic Action Plans, with target competency, proposed objectives/activities, supported prerequisites, duration and basis, verified resources/observed access/cost, occupational/evidence pointers and meaningful SDG rationale. Unsupported fields remain unknown. Attendance does not establish technical competence; assessed hands-on evidence must be scoped. No full course content or real student tracking is planned.
- **Future contract work:** typed competency-support/mapping, requirement-level gap/confidence and optional alignment metadata; later action/comparison/review, ordered-step/resource/duration/SDG/scenario persistence and additive APIs. Existing Phase 4 citations/versions/limitations feed them but do not already implement skill coverage or pathways.
- **Domain 1 risk:** institutional framing and no-CV acceptance are user-reported; replacement of individual intake, person-to-role matching and personalised pathways remains **UNCONFIRMED**. The original brief PDF is unavailable locally; the existing brief-derived six requirements and latest supplied text are preserved without inventing fresh verification/approval. A lightweight form/questionnaire or synthetic learner contingency is planning only, pending written clarification and separate authorization; no student-facing module was implemented.

Priority: close Phase 4 live/source gates → obtain organiser clarification → authorize Phase 5 career alignment/actions → authorize Phase 6 pathways/scenarios/SDGs/Action Plans → later integration/minimal UI. Do not restart Phases 1–3, deploy or automatically commit/push.

Final documentation validation passed for **20 revised/new Markdown files and 92 local links/anchors**, including balanced code fences and UTF-8 checks. The enhancement itself changes planning only; existing Phase 4 code work continued separately as requested. Git HEAD remains `1585b9e`; nothing was staged, committed or pushed during these tasks.

## Nordyc visual concept — 24 October 2026

The user requested a Nordic/maritime identity and app concept under the name **Nordyc**, then narrowed the work to **logo exploration first** after finding the initial screen too generic and a more literal chartroom too game-like. The [visual concept guide](docs/20_NORDYC_VISUAL_CONCEPT.md) now leads with three reference-led sail/N logo studies based on five user-provided images, alongside their monochrome silhouettes; no mark is selected. Earlier app artwork remains an explicitly illustrative, unapproved exploration using fictional institutions, synthetic course records and sample counts.

Subsequent logo feedback requested **simpler**, **more curve**, then a stronger design. The latest candidate uses three curved navy sail-like strokes for a clearer N silhouette; the design guide retains the preceding two-shape versions and all prompts. No final logo has been selected.

This is design exploration only. No frontend, backend, schema, API, analysis service or deployment was implemented by this design task. Phase 3 remains the documented implementation boundary; the Phase 4 prerequisites and unconfirmed hackathon compliance gaps remain unchanged. No application tests or migrations are required for these image/Markdown artifacts; artifact checks are recorded in the concept guide.

## Historical Phase 3 GitHub publication — 24 October 2026

The user subsequently explicitly requested publication to GitHub. This authorizes committing/pushing the completed Phase 3 implementation and Phase 4 planning documentation together to `origin/main`; earlier no-commit/push statements record the prior phase stop boundaries. No Phase 4 implementation is included.

Fresh pre-publication checks: **487 tests passed, zero failed/skipped**, including PostgreSQL integration, in **37.37s** using the existing disposable local validation database. One existing upstream Starlette/httpx deprecation warning remains. Ruff lint passed, formatting passed for 134 Python files, dependency integrity passed, all four PostgreSQL migrations generated successfully, and staged whitespace checks passed. No remote CI result is claimed by these local checks.

Publication excludes `.idea`, private uploads, local databases/downloads and restricted research originals/cards. Only the permitted attributed ESCO/UN reference subsets and explicitly synthetic engineering fixtures accompany the implementation. Git publication does not deploy a service, transfer the local evidence database or make all restricted evidence redistributable.

## Historical Phase 4 planning revision — 24 October 2026

**At the original documentation-only boundary, Phase 4 had not started.** The subsequent authorized implementation and measured results above supersede that status. The original [retrieval contract](docs/19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md), [analysis specification](docs/06_ANALYSIS_ENGINE.md), architecture, schema/API targets, roadmap, prompt and test requirements specified:

- PostgreSQL as the primary source for occupational skills, applicable academic standards, dated workforce indicators and independent AI task evidence; claim-specific checks for quality, relevance, dates/edition, rights and completeness.
- Automatic, bounded research of authoritative original sources for important missing/stale/insufficient evidence once an approved provider and use policy are configured. Search snippets and unsupported model findings remain candidates; restricted sources retain manual/insufficient outcomes.
- Original-source claim checks with URLs, dates/precision, locators, permitted excerpts and provenance; permission-aware versioned storage/cache, immutable run manifests and correction/rights invalidation.
- One disclosed configured existing LLM for structured, citation-bounded analysis; deterministic workforce calculations; every available course returned; title-only benchmarking separated from verified syllabus content; explicit **INSUFFICIENT EVIDENCE**, without automatic obsolescence from decline or AI exposure.
- Configurable allowlists, budgets/rates/timeouts, safe transport, private-upload/egress controls, durable jobs, synthetic offline fixtures and a planned internal-only/fallback/security/cache/grounding test matrix across diverse disciplines.

**Historical prerequisite at that boundary:** no runtime LLM or research adapter existed then. The implementation above now supplies direct Gemini/Brave adapters, while actual credential-backed verification and Phase 3 source/identity/currentness limitations remain open.

This revision changes documentation only: no runtime code, tests, dependencies, configuration, data, migrations or Phase 1–3 behavior were changed. No new research, source import, model call or database migration was performed. The 487-test result below remains the historical Phase 3 completion result, not a new Phase 4 test pass. Documentation checks are reported separately for this revision. No commit or push was performed; stop before implementation.

Documentation validation: **PASS** — 12 revised/new Markdown files, 55 local links/anchors, balanced code fences and UTF-8 checks; `git diff --check` passed. SHA256 comparison against this task's starting snapshot found **zero changes in 96 implementation/data/configuration files**. Read-only review reconciled official-description evidence with optional syllabus evidence. Pytest was not rerun for this documentation-only revision; no Phase 4 tests or live integration pass are claimed.

## Phase 3 completion and measured readiness

The initial 405-test implementation was functional but lacked genuine taxonomy, standards and SDGs. This authorized completion preserved those components and filled a bounded real-data baseline. Read [the complete ingestion report](docs/PHASE3_INGESTION_REPORT.md), [runbook](docs/17_PHASE3_EVIDENCE_INGESTION.md) and [workforce methodology](docs/18_WORKFORCE_TRENDS.md) for exact source scopes and commands.

- **Registry/acquisition:** 75 rows (original 73 + explicit legacy ESCO and official UN resolution artifacts); latest source research and actual `phase3_*` outcomes remain separate. Interactive browser was unavailable; official web reads and legitimate normal downloads/manual imports were used. No SSRF, robots, CAPTCHA/login, rights or size safeguard was weakened.
- **Taxonomy:** 38 real occupations, 10 skills with actual English descriptions, 39 source essential/optional relationships from **ESCO v1.0.3**. Four occupation labels are source-English and 34 retain Arabic; no translations were invented. Complete Arabic CSV ZIP integrity verified; only complete relevant English blocks from a **partial** same-edition Turtle retrieval were used. Current English ESCO remains unavailable; old-edition/currentness limits are prominent. Exact joins queried and replay unchanged.
- **Benchmarks:** 12 narrow MQA bachelor summaries across Computing, Accounting, Business and Biotechnology, actual pages/edition/hash/date precision preserved. Scoped attributed prototype research, not a full-text redistribution licence, institutional teaching assertion or independent academic validation.
- **SDGs:** official A/RES/70/1 resolution supplied 17 goals + 169 targets; source-public-domain basis distinguished from API database rights. No skill/occupation-to-SDG links inferred.
- **AI:** 20 source-backed cards across ILO, OECD, HBS consulting, METR computing and corrected A-Lab materials workflows. Exposure, observed capability/practice, study/model dates, disagreements and corrections remain distinct. OECD contextual findings retain their workforce source class; no occupation demand is inferred from them.
- **Workforce Radar:** deterministic `RISING`, `DECLINING`, `STABLE`, `INSUFFICIENT_DATA` with absolute/% changes, thresholds, source IDs/versions/excerpts, strict compatible populations/periods/units/classifications and fingerprints. Zero/missing values and unsupported sector shares abstain. Two observations never establish a sustained trend.
- **Independent AI attribute:** `AI-TRANSFORMING` requires reviewed observed task/capability evidence and occupation identity. Exposure/forecasts cannot activate it. Exact bridges for the acquired taxonomy are still unreviewed; real examples correctly retain insufficient evidence. Synthetic tests cover both rising+AI and declining+AI combinations.
- **Upload-first workflow:** select a programme → protected private PDF upload → existing separate worker → every extracted course candidate. Supported explicit year-column detection with manual-region fallback; original PDF/hash/page anchors persist atomically. Detailed syllabi are optional; no taught content is invented. Public discovery remains secondary.
- **Compatibility:** no extra migration beyond additive 0004; existing Phase 1–3 functions/history are preserved. Explicit CLI reference imports, offline synthetic fixtures and permitted genuine frozen ESCO/UN reference packs remain available. No default startup download or public external-evidence import endpoint.

Actual local environment: **Python 3.12 / PostgreSQL 16.15**, retained disposable `shiftos_phase3_validation` database on loopback port 55433. No existing application/user database was migrated, and no remote CI pass is claimed.

| Measured check | Actual result |
|---|---|
| Genuine PostgreSQL evidence | **75 registered datasets, 18 versions, 628 references; 38 occupations, 10 skills, 39 relationships; 247 workforce observations; 20 AI cards; 12 academic benchmarks; 186 SDGs** |
| Actual API/provenance queries | HTTP200 for all normalized categories, all 18 version provenance reads; SQL join count39 and all linked skills have descriptions |
| Genuine ESCO repeated import | SUCCEEDED87 normalized rows, then UNCHANGED0 new rows/same version |
| Real Accounting PDF API + worker, repeated | HTTP202;37 unreviewed candidates (12/14/6 by explicit Years1/2/3,5 elective-year unknown),0 verified titles,1 private PDF; second extraction/import UNCHANGED |
| Professionals Q1→Q2 2026 | 315,768→285,907; **DECLINING**, −29,861 (−9.4566%) at default 5% |
| Elementary Occupations Q1→Q2 2026 | 4,070→4,646; **RISING**, +576 (+14.1523%) at default 5% |
| Unclassified Q1→Q2 | **INSUFFICIENT_DATA**, published Q2 missing value preserved |
| Technicians/associate professionals policy demonstration | 93,987→86,512; −7.9532%; STABLE under explicit 10% threshold, DECLINING under default 5%; no statistical-significance claim |
| `python -m pytest -q --basetemp=.pytest-phase3-completion-release --tb=short` with explicit disposable `TEST_DATABASE_URL` | **487 passed, 0 failed, 0 skipped**, one upstream Starlette/httpx warning, 42.42s |
| PostgreSQL integration coverage in that suite | **8 tests passed**, including migration/history/loss guards and real pipeline → idempotent replay → API radar |
| `python -m ruff check .` / `python -m ruff format --check .` | **PASS**, 133 Python files formatted |
| `python -m pip check` | **PASS**, no broken requirements |
| `python -m alembic upgrade head --sql` | **PASS**, all four PostgreSQL revisions compile; no new migration beyond 0004 |
| `git diff --check` | **PASS** |

All real demand examples are broad occupation-group **advertising**, short-term only, not individual-role/skill demand, employment/hires or AI-causation. No genuine combined rising/declining+AI-transforming occupation result is claimed where identity bridges/detailed demand are missing. Human academic review and currentness checks are required before academic action.

Restricted originals and narrow internal research cards remain in ignored local storage with citations/rights notes; permitted ESCO/UN frozen subsets are in `data/reference_packs/`. These are genuine separately attributed data, not synthetic fixtures. The 76 automatic PDF pages remain unreviewed candidates. Real standalone occupational-task taxonomy rows remain zero; supported professional task text lives in AI cards rather than being fabricated.

Completion checks caught and corrected PDF persistence occurring before result validation, malformed/future comparison metadata, a workforce-study exposure/source-class mismatch and fixtures assuming the original 73-row registry. Targeted checks and the final 487-test PostgreSQL-enabled suite pass. Historical failed acquisition/import attempts remain observable; their corrected retries or manual alternatives do not erase source failures. The warning is an existing upstream deprecation, not an accepted test failure.

**Remaining source actions:** obtain a permitted current English ESCO export (operator's own wizard consent/email); secure TalentCorp written aggregation/network-use consent (Group notice §3.3, PDF page 10); review taxonomy-to-Malaysian occupation bridges, exact AI occupation associations, standard editions/applicability and full discipline coverage. Unsupported layouts/scans/detailed syllabi need explicit regions or reviewed JSON. Limited catalogue tokens are not full production identity/tenant controls; private/rights-limited data is not approved for unrestricted deployment.

At the historical Phase 3 completion/Phase 4 planning boundaries, no commit/push was performed; the later Phase 3 publication is recorded above. Current Phase 4 implementation/validation is recorded at the top, with Phase 3 functionality preserved.

## Phase 2 delivered (historical handoff)

- Dynamic official XMUM undergraduate link discovery; no Software Engineering-only or fixed programme list. Provider/parser configuration can expand to other institutions without new catalogue tables.
- Conservative Main Courses parsing: public titles, explicit years/semesters, elective groups, original ambiguous labels and exact source locators. Missing metadata stays null/UNKNOWN; bilingual/composite/truncated entries carry review flags.
- Durable PostgreSQL job queue and separate worker; bounded opt-in HTTPS acquisition, robots checks, rate limiting, retries, response/time limits, host allowlist/public DNS/IP pinning and sanitized failures. No network fetch in HTTP handlers.
- Reviewed structured JSON API/CLI fallback; real/synthetic lanes, supplied review assertions and missing teaching evidence remain explicit.
- Institution/programme identity reconciliation, exact-duplicate filtering, immutable source/revision fingerprints, safe re-imports, historical retrieval and older-snapshot nonreactivation. Per-programme transactions preserve successful partial progress; stale-worker fencing prevents late writes after recovery.
- Existing catalogue retrieval APIs retained; new provider/job/discovery/import/history/coverage APIs and course provenance/missing-field response fields.
- Additive migration `0003_curriculum_ingestion`; original `0001`/`0002` unchanged. PostgreSQL JSONB defaults/constraints are schema-tested; downgrade refuses populated provenance/job data loss.
- New job-submission token guard in production, bounded request bodies, no credentials in errors. Existing manual Phase 1 routes are not a production authorization system.
- Offline synthetic HTML/JSON fixtures; automated parser, persistence, API, security and PostgreSQL migration tests. Pinned Beautiful Soup added; httpx is now a runtime dependency.
- [Phase 2 runbook](docs/16_PHASE2_CURRICULUM_INGESTION.md), README, schema/API documentation, environment template and ignore rules updated.

## Actual Phase 2 verification

Local environment: Windows, Python **3.13**, portable PostgreSQL **16.15**, localhost only. A new disposable `shiftos_phase2_validation` database was used; no application/user database was migrated. PostgreSQL automated tests create/drop isolated random schemas. CI is configured for Python 3.12/PostgreSQL 16; a local pass does not itself certify a remote CI run.

| Command / check | Actual result |
|---|---|
| Baseline before Phase 2 | 141 passed, 3 PostgreSQL tests skipped; pip check passed |
| `python -m pip install -e '.[dev]'` | PASS with pinned dependencies |
| `python -m pytest -q --basetemp=.pytest-phase2-release --tb=short` with explicit disposable `TEST_DATABASE_URL` | **301 passed, 0 skipped, 1 upstream warning in 13.65s** |
| `python -m ruff check .` / `python -m ruff format --check .` | PASS; 104 Python files formatted |
| `python -m pip check` | PASS — no broken requirements |
| `python -m alembic upgrade head --sql` | PASS — all three revisions compile as PostgreSQL SQL |
| Synthetic JSON example and research registry | PASS — manifest schema validation; 73 registry rows retained |
| Independent implementation review and secret/generated-file audit | PASS — no unresolved blocker or exposed real credentials; only explicit placeholders, disposable CI credentials and test sentinels matched secret patterns |
| `.gitignore` probes / `git diff --check` | PASS — environment/secrets, local databases/journals, raw/local source files, temporary files, keys and validation artifacts excluded; no whitespace errors |
| PostgreSQL migration suite | **6 passed**: clean lifecycle/schema match, populated old-data preservation, each Phase 2 metadata-family loss guard, imported history/replay/API |
| Real Uvicorn + PostgreSQL health/readiness/OpenAPI | HTTP 200 |
| Production live XMUM discovery, twice | **FAILED safely**, `unsafe_source_url`: environment DNS returned private `10.68.12.164` for `www.xmu.edu.my`; bare host did not resolve. Zero programme/course/source records persisted by those discovery jobs. |
| Reviewed cached official directory -> existing source/programme APIs | **25 programme records** with official URLs/locators; manual source-backed directory import |
| Reviewed three-source JSON -> `import-curriculum` CLI -> `worker --once` with discovery disabled -> FastAPI reads | **SUCCEEDED**, 141 course appearances: Accounting **37**, Chinese Studies **62**, Marine Biotechnology **42** |
| Same real reviewed file imported twice | **SUCCEEDED**, 3 unchanged programmes; totals stable at 25 programmes, 28 revisions (25 directory-only initial + 3 imported), 141 courses, 4 sources |
| Evidence quality in that manual validation | **138 verified title assertions**, 3 bilingual pairs need review; all **141 title-only**, zero syllabus claims |

Raw official HTML, local smoke scripts/results and portable database files remain outside versioned product data. Exact source links and limitations are in the runbook. This was a disposable validation, not a production dataset release. The dynamic parser has diverse offline fixtures plus real 25-link directory validation and three real programme-page checks; the other 22 real programme-page layouts and **all-25 live automatic course acquisition remain unverified** on this network. A later operator must run it from an allowed public-resolving network or supply reviewed files.

An initial PostgreSQL check caught JSON equality/default comparison and a downgrade constraint-name issue; both were fixed and rerun successfully. Independent security review caught blank-token authorization and stale-worker write races; fixes and regressions now pass. One existing Starlette test-client warning deprecates httpx integration; it does not fail the suite. No failing test is accepted for commit.

## Dataset research completed — 2026-10-24

Research deliverables: [findings](docs/DATASET_RESEARCH.md), [priorities](docs/DATASET_PRIORITY.md), [acquisition plan](docs/DATA_ACQUISITION_PLAN.md), [feature mapping](docs/DATASET_TO_FEATURE_MAPPING.md), [gaps](docs/DATA_GAPS.md), [registry](data/dataset_registry.csv). These research snapshots contain 73 source/artifact rows (42 P0, 26 P1, 5 P2), with 55 Verified, 17 Partially verified and 1 Unverified access states. Research access is distinct from reusable licensing or completed production acquisition.

The research found 25 XMUM Main Courses sections/brochure links, inspected two actual DOSM JMI workbooks (Q1/Q2 2026), selected ESCO API responses and UN goals/targets, and catalogued cross-disciplinary standards/AI evidence. Registry validation checked IDs/columns/enum/URL syntax; remote availability and rights remain publisher-specific. Research-time `acquired_into_backend=No` is superseded by the explicitly scoped Phase 3 outcomes above and appended registry columns.

## Phase 1 preserved and historical verification

Phase 1 retains FastAPI/settings, SQLAlchemy/psycopg, UUID/UTC models, all eight application tables, source registry, original manual create/read APIs, offline fixture IDs/hashes/anchors and loss-preventing migrations. See [the migration audit](docs/15_PHASE1_MIGRATION_AUDIT.md).

Historical local Phase 1 result: **144 passed, 0 skipped**, PostgreSQL 16.15/Python 3.13; Uvicorn/PostgreSQL smoke and 12-course synthetic fixture re-import passed. Its Python 3.12/PostgreSQL 16 [CI run 39998532797](https://github.com/RikoHalim/shift-os/actions/runs/39998532797) succeeded for implementation `866df6c`. These historical results do not replace Phase 2 acceptance.

## Remaining limits

- Live provider acquisition must be verified on a permitted network with public DNS. A private gateway is not an excuse to weaken source restrictions; reviewed JSON remains available offline.
- Public marketing lists are not certified complete curricula. Shared MPU, course codes/credits, cohort, unstated semesters/classifications and actual syllabi require separate confirmation. No inferred obsolete/replacement verdicts exist.
- HTML structure changes can require parser review; no general PDF or JavaScript crawler is implemented. Phase 3 adds local operator-selected PDF regions for unreviewed candidate preparation; other layouts can still require transcription. Raw HTML hash changes may create a new revision even when titles are unchanged.
- Copyright/reuse permission is not inferred from public access or robots. Whole brochures/pages are not committed. Reviewed flags/manual hashes are operator assertions, not independent source authentication.
- Full production identity/access control, automatic scheduling/monitoring, backups and Docker Compose execution remain outside this local verification. New tokens govern new catalogue job writes only.
- Genuine bounded taxonomy/benchmark/SDG subsets are loaded; latest English taxonomy, full coverage and reviewed local bridges remain limited. Phase 4 offline screening is implemented; live validation, actions, pathways/scenario reports and frontend remain pending. No analysis accuracy is claimed.

## Unresolved organiser clarification — UNCONFIRMED

The user reports approval of institutional framing and exemption from CV uploads. No written response/date/channel/evidence was provided for replacing individual skills intake overall, person-to-role matching, or personalised learning pathways. SDGs and multiple scenarios are not assumed waived. See [the compliance matrix](docs/09_HACKATHON_COMPLIANCE.md).

Obtain in writing: “Can programme-level profiles, occupation alignment and institutional academic interventions replace individual-profile intake, person-to-role matching and personalised learning plans for Domain 1?” Record the exact response and evidence. This gap is preserved; no learner waiver was invented.

## Next recommended prompt and stop boundary

“Read AGENTS.md, STATUS.md, the Phase 4 runbook and career alignment/pathway plan. Preserve the existing Phase 1–4 implementation and 637-test baseline. When local credentials/use policies are available, configure one explicit Gemini model and Brave Search, perform actual bounded structured-model and search→registered original→verified import/query→cited finding smoke tests, and report source/credential blockers honestly. Keep private uploads out of search and preserve title-only abstention, deterministic workforce scope and source permissions. Rerun appropriate checks after changes, update STATUS and stop. Do not implement Phase 5/6, deploy or commit/push without separate authorization.”

Historical Phase 2/3 publication authorizations do not authorize publishing this work. The current requests authorize Phase 4 implementation and Phase 5–6 documentation only, prohibit automatic commit/push and require stopping before later-phase implementation.

## Main merge verification — 2026-10-24

Merged Phase 2 implementation `0c0bc54` into `main`, preserving the feature branch and existing history. The earlier uncommitted local documentation revisions were saved in recoverable Git stash `codex-doc-revisions-before-phase2-merge`; they were not overlaid on the newer Phase 2 status/schema/API documents. All versioned repository folders are included in the merge, and the local virtual environment was updated from `requirements.lock` and the editable project.

- Current local suite: **295 passed, 6 skipped, 1 warning in 10.83s**. All six skipped tests require explicit PostgreSQL `TEST_DATABASE_URL`; the earlier 301-test PostgreSQL result above remains historical branch evidence, not a fresh database run.
- Ruff lint passed; formatting passed with 104 Python files already formatted.
- Dependency integrity check passed; PostgreSQL SQL generation passed for all three migrations. No application/user database migration was applied by this merge task.
- Read-only review of the migration, APIs, fetch boundary, worker/idempotency and Phase 1 compatibility found no merge blocker. Whitespace checks passed.
- Synchronising Git files does not import the earlier disposable validation database or perform live XMUM collection. The documented live-network/coverage limitations remain unchanged.
