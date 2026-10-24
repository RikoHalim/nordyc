# Phase 4.1 — Replit-managed Claude

This extension preserves the Phase 4 evidence engine, academic Pydantic contract, citation validator, deterministic workforce calculations, background worker and protected APIs. It adds a configurable Replit-managed Anthropic Messages adapter and retains an explicitly gated Gemini fallback in code. Current MVP decision: Replit-managed Claude Opus is primary; Gemini is discontinued and not enabled; Replit remains the host; Brave research is preserved but pending. **[Phase 4.2 live backend acceptance is now PASS / COMPLETE](25_PHASE42_LIVE_BACKEND_VERIFICATION.md)**: one actual worker request, two courses, three citations, committed PostgreSQL results and protected HTTP retrieval. Earlier handover/diagnostic snapshots below are historical and do not authorize another request.

Current bounds additionally include `ANALYSIS_VALIDATION_MAX_ATTEMPTS` (default 2, use **1** to prohibit paid repair) and `ANALYSIS_PROVIDER_MAX_REQUEST_BYTES` (default 1,000,000, acceptance **24,576**). These complement transport attempts, timeout and output-token limits. Safe Claude HTTP status and elapsed milliseconds are retained with actual model/usage in the existing manifest. Persistent external processing stays false. The current development/publication branch is **`codex/replit-managed-ai`**; do not follow historical main-branch import commands in an existing checkout.

## Historical Phase 4.2 diagnostic correction and accepted isolated result — 24 October 2026

**Assessment: isolated live Claude verification PASS; full live worker/database/API verification PARTIAL (pending).** Replit-managed Anthropic is the primary MVP provider, requested and returned model `claude-opus-5`; Gemini remains disabled, Replit remains the hosting platform, and Brave remains independent and live-unverified. The later owner-approved diagnosis and instruction to continue until success supersede the earlier one-request stop recorded below. Retrying did not remove the $1 diagnostic budget or source restrictions.

The accepted request began at **2026-10-24T14:01:40.426482+00:00**. Exactly one HTTP attempt returned **200**, `application/json`, `stop_reason=end_turn`, actual model **`claude-opus-5`**. Request size was **15,989 UTF-8 bytes**, capped at **16,384**; output cap **4,096 tokens**, timeout **60 seconds**, no retries, repair, Gemini fallback, tools, or search. The external-processing gate was true only inside the consent-scoped process. Persistent `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=false` and source permissions were unchanged.

| Accepted live check | Actual observation |
|---|---|
| Existing `verify-claude --live` workflow | **PASS**, CLI exit 0, `status=live_verified`, one actual request |
| Model identity | Requested and returned **`claude-opus-5`**; no more specific version was reported |
| JSON / original Pydantic / grounding | **PASS / PASS / PASS**; academic schemas and validators unchanged |
| Evidence citations | **3** valid occurrences, exact quotes of the one admitted, attributed ESCO v1.0.3 irrigation excerpt; no private curriculum documents |
| Uncertainty / course coverage | The sole fictional title-only course was returned; **all five dimensions `insufficient_evidence`**, `needs_syllabus_confirmation=true`, final curriculum verdict false |
| Usage | **6,828 input**, **1,677 output**, **0 cache creation**, **0 cache read** tokens |
| Measured client request duration | **18,264.139 ms** (includes network and response processing; not an academic performance metric) |
| Observed billing | **Unavailable**, `observed_cost=null`; token-price estimates are not invoices; rejected attempts are not asserted free |

There were **five actual transport attempts across Phase 4.2**, including the original failed request: (1) original generic invalid response, HTTP status unavailable, 8,052.512 ms; (2) safe diagnostic HTTP **400**, invalid-request/schema rejection, **3,354.445 ms**; (3) after singleton-enum compatibility adjustment, HTTP **400**, schema-complexity reason tokens, **3,419.794 ms**; (4) reduced choice grammar, HTTP **200**, Pydantic passed but grounding rejected, **6,405 input / 1,752 output**, **27,258.330 ms**; (5) explicit existing grounding instructions, the accepted result above. Only the fifth result was accepted. Diagnostics since the original request used one attempt each. Model calls stopped on acceptance. Known returned usage across the two HTTP-200 attempts totals **13,233 input / 3,429 output tokens**; rejected requests had no reported usage. No automatic or unbounded retry loop was added.

The initial transport grammar had 25 optional-property occurrences after local-reference expansion. Requiring declared properties removed those optional branches but did not itself fix the live rejection; converting literals to singleton enums also did not fix it. Moving repeated multi-value enums into descriptions, with original Pydantic enforcement retained, removed the observed schema rejection. The exact provider error body was not published; safe status, bounded MIME/body metadata and allowlisted reason tokens were captured. This establishes the successful compatibility change, not proof that every earlier rejected keyword was independently unsupported. [Anthropic documents compiled-grammar limits and simplified transport schemas with original application validation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

Claude-specific instructions now state existing revision/course identity, title-only abstention, citation quote/scope, source-date limitations and summary-count rules explicitly. No response was repaired to obtain a pass. The successful raw synthetic JSON remains an ignored diagnostic artifact. It contained redundant `offline_synthetic` limitation tags despite `result_mode=live_model`; these conservative extra tags are a reporting-quality limitation, not evidence that a mocked provider generated the response. All programme insights are still rebuilt deterministically from validated course findings and the frozen packet.

| Regression / infrastructure check | Result and practical limit |
|---|---|
| Exact final Replit offline suite, Python 3.12.12 | **750 passed, 13 PostgreSQL-only skipped**, one existing Starlette/httpx warning, **35.68 s**; mocked provider tests and offline fixtures, no live calls |
| Diagnostic harness | **17 offline scenarios passed**, including gzip/oversize errors, success-body preservation, secret canaries, strict request/output/attempt bounds; zero real API calls |
| Ruff lint / formatting | **PASS** over tracked Python plus new compatibility tests and ignored diagnostic runner |
| Dependency integrity / whitespace | `pip check` and `git diff --check` **PASS** |
| Current-source PostgreSQL regressions | Exact downloaded source plus unchanged synthetic fixtures from shared base `7dce033de2980ff6f758030df616a2e78b90fe73`, Windows Python **3.13.13**, isolated loopback PostgreSQL **16.15**: **13 passed, 750 deselected**, **25.19 s**; separate run, mocked models, no live calls; test server stopped |
| Alembic | Offline PostgreSQL SQL compilation **PASS**, single head **`0005_programme_analysis`**; migration integration tests passed, no application migration added |
| Baseline comparison | Claude branch offline baseline **743 → 750** passing tests; 13 integration cases unchanged. Gemini's historical 794-test branch is a different source baseline, not a directly comparable test count |
| Full live worker → Claude → PostgreSQL → protected FastAPI | **PENDING**; isolated live CLI and offline PostgreSQL/API tests are separate evidence, not a single live end-to-end run |

Verification setup failures were corrected rather than hidden: the first direct targeted run inherited ambient SQLite outside test mode and failed collection; an initial full offline run with SQLite overrides produced 12 settings-related failures; clean PostgreSQL-shaped offline configuration then passed all 750 tests. The first downloaded-source PostgreSQL run passed 12 tests and failed one because the review archive omitted its synthetic fixture; restoring that unchanged shared-base fixture made all 13 pass. No application fix was made to accommodate these harness issues.

Replit source branch: **`codex/replit-managed-ai`**; observed checkpoint HEAD **`1b75e7fab2f53a68f08d5c1e9deb49a95019afc0`**, with later tested provider/tests in the working tree. Exact tested provider SHA-256: **`8a450689e1810f95e5707b0c79e7eedec697a486cec77364ab5fc32f9f657203`**. Credential-free source/review archive SHA-256: **`c1dee99a1f00a153a2a9dc1bd380aa7be8b4432cd24eea8387357be7957cf9c0`**. These fingerprints identify tested contents without claiming an uncreated commit. GitHub `codex/replit-managed-ai` remained **`7dce033de2980ff6f758030df616a2e78b90fe73`** at the last read-only check. No push, merge, deployment, main/Gemini branch change or Phase 5 implementation occurred during this diagnosis.

Browser access was temporarily interrupted after the successful live test. The owner restored access and this reviewed record was then saved in the correct Replit development checkout on 24 October 2026. The code fix and accepted audit were preserved throughout. GitHub publication of this diagnosis remains pending. The connected Replit account had resolved a different same-named app during the interruption; that app was not modified. No additional live request was made to restore browser access or save these records.

Remaining Phase 4 limits: one synthetic course and one legacy permitted excerpt do not demonstrate real curriculum accuracy, current Malaysian demand or discipline-wide coverage. Brave live verification and a fresh approved billable worker/database/API proof remain pending. Do not declare Phase 4 fully verified or start Phase 5 implementation yet. Keep the persistent external-processing gate false; obtain the separately requested explicit budget/consent for a further live end-to-end call.

## Historical Phase 4.2 first-request verification attempt — 24 October 2026

The owner supplied consent for **exactly one** synthetic-only Replit-managed Claude Opus 5 request with a **$1 budget**. No further live requests are authorized. The ordinary zero-call preflight had been blocked by the false external-processing gate. Before the request, a zero-call preflight in the same temporary process configuration returned `configuration_ready`: both managed Anthropic variables were present, the base URL was valid, `replit_claude` and `claude-opus-5` were selected/enabled, and the unchanged `C-ESCO-V103` source policy passed. The shared `.replit` gate stayed false; `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=true` was process-only.

The existing verification helper made one actual attempt using one fictional irrigation course and one attributed public ESCO v1.0.3 excerpt; no private documents were sent. It made no retry, repair, fallback, or search request. The sanitized outcome is **failed**, helper error `provider_response_invalid`, with one provider request. Requested model was `claude-opus-5`; returned model and token usage were unavailable. Schema and grounding validation were false, citations were zero, and no output was accepted. The five dimension uncertainty statuses are unavailable because no schema-validated result was returned. The sent packet was title-only, retained `needs_syllabus_confirmation=true` and `title_only_not_taught_content`, and cannot produce a final curriculum verdict.

The request-wrapper timing was **8,052.512 ms** (UTC start `2026-10-24T12:37:54.947Z`, end `2026-10-24T12:38:03.000Z`); CLI elapsed time was **8,059.635 ms**. The run did **not** retain HTTP status or an upstream error type/code. `provider_response_invalid` is the only saved sanitized helper code; it does not establish a root cause. Do not blame credentials, model availability, or schema support without evidence, and do not repeat the request to recover diagnostics.

`observed_cost` remains `null`: no per-request invoice was available and billing may post later. No cost is confirmed as zero, and no provider-price estimate is treated as a bill. The previous ambient SQLite database configuration failed `Settings` validation outside test mode. An inert process-only PostgreSQL-shaped URL was used solely for settings validation; `verify-claude` exits its configuration path before creating a database engine. No database was provisioned or contacted. A real isolated PostgreSQL database is still required for any later worker/API end-to-end proof.

Current checks are separate:

| Check | Result |
|---|---|
| Replit complete offline pytest after the request | **743 passed, 13 PostgreSQL-only skipped, 0 failed**; credentials/runtime provider flags removed, `TEST_DATABASE_URL` unset; no PostgreSQL connection; one existing Starlette/httpx deprecation warning |
| Replit focused offline Claude/Phase 4/source-policy pytest | **267 passed, 1 integration-marked test deselected**, one existing warning |
| Owner-supplied Codex local PostgreSQL verification | Windows Python **3.13.13** using an archive of exact source commit `7dce033de2980ff6f758030df616a2e78b90fe73`; archive confirmed as the Claude source, not Gemini checkout. Fresh isolated loopback PostgreSQL **16.15**: **13 integration passed, 743 deselected**, **30.81 s**, mocked providers, zero live calls; server stopped. Ruff lint/format for `src`, `tests`, `alembic`, `pip check`, offline Alembic SQL and single head `0005_programme_analysis` passed. This is not a single 756-pass run. |

The ignored preflight, CLI stdout/report, and supplemental audit remain under `data/local/`. No live worker, migration, PostgreSQL, protected API, Gemini, Brave, research, merge, deployment, or GitHub push was performed. No application code, configuration, or source permissions changed. The product decision is Claude primary for the MVP, Gemini not enabled, and Brave research pending. Live acceptance is **BLOCKED**. Any diagnostic request to capture a safe HTTP status/upstream code needs separate explicit approval; do not switch models silently.

## Historical Phase 4.1 managed setup and zero-call baseline — 24 October 2026

The owner-approved native Replit AI setup was run **inside this NORDYC project** on the existing `codex/replit-managed-ai` branch:

```javascript
setupReplitAIIntegrations({ providerSlug: "anthropic" })
```

The native setup succeeded and provisioned `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` and `AI_INTEGRATIONS_ANTHROPIC_API_KEY`. A secret-presence-only check reported both **PRESENT**; their values were not read or printed. Do not use a personal Anthropic key, copy credentials from another project, or substitute a general connector for this native setup.

These non-secret shared settings are configured:

```text
ANALYSIS_MODEL_PROVIDER=replit_claude
CLAUDE_ENABLED=true
CLAUDE_MODEL=claude-opus-5
ANALYSIS_GEMINI_FALLBACK_ENABLED=false
ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=false
```

At the Phase 4.1 stop boundary, the zero-call command `python -m shiftos.cli verify-claude` (without `--live`) returned **blocked**, exit 1, with `provider_requests=0`. It confirmed the adapter was selected, Claude enabled, the preferred model configured, the managed credential and bridge base present and valid, and the existing `C-ESCO-V103` source permission passing. Its only blocker was `external_processing_not_approved`. That historical consent boundary was followed by the single Phase 4.2 attempt documented above; it does not authorize another request. Source permissions were not changed.

The clean offline pytest subprocess passed **743 tests** and skipped **13 PostgreSQL-only tests** because `TEST_DATABASE_URL` was unset. SQLite fixtures and mocked providers/workers were used; no PostgreSQL connection, migration, real worker, model, research, or search request was made. `ruff check` and `ruff format --check` each passed over all **97 Git-tracked Python files**, including six Alembic files. Repository-wide checks also scan `.local` skill material: `ruff check .` reports two existing issues in `.local/skills/meta-devices/files/ray-ban/favicon-generator.py`, while `ruff format --check .` reports 10 unformatted `.local` skill files. These generated helpers are not Git-tracked and were not changed.

The connection-fix commit `629f8bba0e3908bde5ff8a700d4fef36714e9e0b` was reviewed against parent `d3babf9245cee7bd020d62b16d9bf9e1f0b54fc5`: its complete changed-path set is `.replit`, `STATUS.md`, and this runbook only. `.replit` contains the requested non-secret flags; no application code or source-permission file changed. A secret-pattern scan of the commit and working diff passed without displaying candidate values. `git diff --check` passed for both the commit and working diff.

## Initial local availability snapshot (historical)

At the initial snapshot on 24 October 2026 this work ran in a local Windows checkout, not an authenticated Replit runtime. Neither managed Anthropic environment variable was present there, and no Replit connection/configuration had been discovered. That historical local blocker predates the successful native setup documented above; it did not establish whether managed access worked in Replit.

[Replit's official catalogue](https://docs.replit.com/features/integrations/replit-ai-integrations), checked on this date and labelled last updated 2 October 2026, lists **`claude-opus-5`** and older Opus alternatives. These are catalogue entries, not successful requests here. Keep `claude-opus-5` preferred and confirm it in the actual workspace. Any alternative requires an explicit model setting and a recorded reason. Compatibility of older models, including Opus 4.1, with [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) must be checked separately.

Replit documents paid-plan access, organization controls and an approval flow for adding **Anthropic (Replit managed)** to an existing app. Its public documentation confirms Messages API support, but not this adapter's bridge variable/path contract. Managed credentials and an endpoint must actually be provisioned; a paid account alone is insufficient. [Replit AI Integrations](https://docs.replit.com/features/integrations/replit-ai-integrations).

## Historical Phase 4.1 Replit handover

The import example below describes the older Phase 4.1 baseline. For the current Claude development branch, isolated PostgreSQL setup and completed live acceptance, follow [Phase 4.2](25_PHASE42_LIVE_BACKEND_VERIFICATION.md). Preserve divergent Replit changes; do not pull or switch to main for this work.

The implementation was published to `origin/main` as [ec9b7f79ea26760a75f84e3c98cef8d4ce71bcfb](https://github.com/RikoHalim/NORDYC/commit/ec9b7f79ea26760a75f84e3c98cef8d4ce71bcfb), with the exact remote SHA verified after push. A subsequent documentation-only publication record may be the branch tip. Compare the imported tip with the final publication report; the linked implementation is the tested code baseline, not a reason to discard later documentation. [STATUS](../STATUS.md) records the checks and publication scope.

Use a separate development workspace and database for this verification. Import [RikoHalim/NORDYC](https://github.com/RikoHalim/NORDYC) through **Import → GitHub**, selecting `main`, after the publication report confirms the new commit. Replit's [GitHub import instructions](https://docs.replit.com/build/import-from-providers) describe connecting the repository. For an already imported workspace, inspect local changes and use the [Git pane's Pull action](https://docs.replit.com/features/workspace-tools/git-interface). Do not overwrite divergent work. The Shell equivalent below stops if a fast-forward is impossible:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main
git rev-parse HEAD
```

Confirm the branch is `main` and compare the full SHA with the publication report. Source import transfers neither the local Windows PostgreSQL contents nor ignored files. Replit needs its own configured database, secrets and explicit reference imports. Do not upload `data/private`, `data/raw`, restricted MQA/research documents, `.env`, local reports or database dumps through Git.

Open **Shell** in the project root. Select/provision Python 3.12 in the workspace configuration if it is missing, then install this project's locked dependencies into its own environment. Do not replace the lock with automatically guessed latest packages. Replit documents [Shell dependency installation](https://docs.replit.com/features/project-setup/dependency-management); these commands use this repository's pip/setuptools configuration:

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e '.[dev]'
python -m pip check
```

In Replit's Database tool, select the **development** PostgreSQL database intended for this isolated check, then inspect **Settings** for its actual connection details. Use the provisioned host, database, user, credential and SSL options, without substituting guessed values. Replit documents the supplied [`DATABASE_URL`](https://docs.replit.com/features/data-and-storage/connection-details). NORDYC requires SQLAlchemy's `postgresql+psycopg` driver prefix. If the managed value starts with `postgres://` or `postgresql://`, the following Shell-only normalization preserves its actual connection details and prints no credential. Repeat it in each new Shell used for migrations, API or worker; do not change the provider-managed database configuration:

```bash
shiftos_db_url="$(python - <<'PY'
import os
from sqlalchemy.engine import make_url
try:
    url = make_url(os.environ['DATABASE_URL'])
    if url.drivername not in {'postgres', 'postgresql', 'postgresql+psycopg'}:
        raise ValueError
    print(url.set(drivername='postgresql+psycopg').render_as_string(hide_password=False))
except Exception:
    raise SystemExit('Configure the actual isolated PostgreSQL DATABASE_URL in Secrets') from None
PY
)" && export DATABASE_URL="$shiftos_db_url"
unset shiftos_db_url
python - <<'PY'
from shiftos.core.config import Settings
Settings()
print('Settings validated; connection credentials were not printed')
PY
```

If either step fails, correct the supplied configuration before continuing. Keep any manually supplied database URL, managed credential and separate random `ANALYSIS_WRITE_TOKEN` and `CATALOGUE_WRITE_TOKEN` values in **Secrets**. Use a password manager to generate the tokens. Replit makes Secrets available as environment variables; non-sensitive flags can use its Configurations section. Never paste secret values into code, prompts, reports or browser URLs. [Secrets documentation](https://docs.replit.com/core-concepts/project-editor/app-setup/secrets).

Apply existing migrations to this isolated database:

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic history
```

The expected head is `0005_programme_analysis`; the chain contains `0001_foundation`, `0002_catalogue_sources`, `0003_curriculum_ingestion`, `0004_reference_evidence` and `0005_programme_analysis`. A successful upgrade creates schema, not evidence records. An unrelated existing database requires its own backup/review before migrations.

For a workspace-local API preview, keep this process running in one Shell:

```bash
source .venv/bin/activate
# Repeat DATABASE_URL normalization above in this Shell if needed.
python -m uvicorn shiftos.main:app --host 127.0.0.1 --port 8000
```

From a second initialized Shell, `curl --fail http://127.0.0.1:8000/health/ready` checks the database connection; `http://127.0.0.1:8000/docs` serves API documentation inside the workspace. This runbook uses loopback requests, without publishing the service. Replit's browser Preview uses [port forwarding](https://docs.replit.com/core-concepts/project-editor/app-setup/ports); do not infer that a forwarded port is private or change the server to public binding for this check. The worker is a separate process, started explicitly below.

## Configuration and controls

| Setting | Default / purpose |
|---|---|
| `ANALYSIS_MODEL_PROVIDER` | `gemini` preserves Phase 4 behavior; set `replit_claude` to select managed Claude |
| `CLAUDE_ENABLED` | `false`; explicit enable gate |
| `CLAUDE_MODEL` | `claude-opus-5`; configurable bounded Claude model identifier |
| `CLAUDE_MAX_OUTPUT_TOKENS` | `16384`; bounded to 1–16384 |
| `AI_INTEGRATIONS_ANTHROPIC_API_KEY` | Managed server credential; absent by default, never returned/logged |
| `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` | Exact provisioned bridge base; absent by default |
| `ANALYSIS_GEMINI_FALLBACK_ENABLED` | `false`; optional Claude-to-Gemini fallback for operational failures only |
| `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED` | Existing global approval gate; remains `false` by default |

Existing `ANALYSIS_PROVIDER_TIMEOUT_SECONDS`, bounded attempts and byte limits apply. Endpoint validation rejects embedded credentials, query/fragment injection, malformed/traversal paths and unsafe HTTP destinations; redirects are forbidden. Safe operator-provisioned bridge prefixes are supported; there is no guessed endpoint or public endpoint override. The managed endpoint is administrator-controlled server configuration, never request/user input. Source-specific processing permissions and admitted evidence remain mandatory for both providers; approving an integration does not authorize private university documents. Brave discovery, cache rules, source allowlists and deterministic workforce services are unchanged.

Claude uses the Messages API with `output_config.format` and a copied provider-compatible JSON schema. Unsupported schema constraints remain enforced by the original application Pydantic schema and grounding validator. [Anthropic documents this schema transformation pattern](https://platform.claude.com/docs/en/build-with-claude/structured-outputs). Native Anthropic citations, tool use, web search and prompt caching are not enabled; NORDYC retains its existing citation IDs, exact excerpts, course associations and rights validation. Thinking blocks are not persisted as findings. Incomplete/refused/malformed responses cannot become accepted course results.

Optional fallback occurs only after Claude unavailability, bounded deadline or rate-limit failure. It requires explicit opt-in and separately enabled/configured Gemini access. Authentication/privacy/configuration/protocol failures and invalid schema/citations do not trigger cross-provider fallback. A grounded-output repair stays on the same provider. Fallback is disclosed and the job remains PARTIAL; it never claims verified Claude output when Gemini supplied the findings. Remaining failures preserve all courses with deterministic insufficiency.

## Native managed Claude setup

After owner approval, use Replit's native AI integration setup in the target project:

```javascript
setupReplitAIIntegrations({ providerSlug: "anthropic" })
```

This native setup provisions the managed integration for that project. Confirm only whether the resulting `AI_INTEGRATIONS_ANTHROPIC_API_KEY` and `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` variables are present; never display their values. These variable names are the adapter contract. Do not use a personal `ANTHROPIC_API_KEY`, copy credentials from another project, invoke the general connector catalog, guess a host, or point at Anthropic's direct endpoint. The adapter appends `/v1/messages` once; if the native bridge contract differs, retain a blocker rather than weakening endpoint validation.

The current non-secret shared settings are:

```text
ANALYSIS_MODEL_PROVIDER=replit_claude
CLAUDE_ENABLED=true
CLAUDE_MODEL=claude-opus-5
ANALYSIS_GEMINI_FALLBACK_ENABLED=false
ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=false
```

Keep external processing disabled unless the owner separately approves it. Before any later live request, re-check the exact source-specific processing/output permissions and their basis; do not broaden permission to private documents. Managed integration approval is not source permission or external-processing consent. The source permission file was not changed during the current setup.

## Zero-call preflight and bounded one-course check

Configuration inspection makes **zero network requests** and needs no database connection:

```bash
python -m shiftos.cli verify-claude --report data/local/phase41-claude-preflight.json
```

Missing/disabled configuration returns a structured `blocked` report and exit code 1. `configuration_ready` means configuration passes preflight, not that connectivity, authentication, model availability or proxy schema support has been verified. The current Replit preflight is blocked only by `external_processing_not_approved`, reports that the existing ESCO permission passes, and confirms zero provider requests. Do not pass `--live` without separate authorization.

Only after Replit provisions access, the following explicitly opts into one synthetic course request:

```bash
python -m shiftos.cli verify-claude --live --report data/local/phase41-claude-live.json
```

This helper pairs one explicitly fictional course/institution with an attributed genuine ESCO v1.0.3 skill excerpt from the permitted frozen reference pack. It preserves the original identifier, locator, edition and date limitations, and labels the copied packet as a synthetic verification lane; the source itself is not invented. The explicit `C-ESCO-V103` processing policy must allow use before any request. No real university documents are included. It caps output at 4096 tokens, disables provider fallback and transport retries, validates the existing `ProgrammeResult` plus supporting citations, and returns secret-free actual model/usage information. It is an isolated provider smoke, **not a database/API persistence proof**. Reports remain under ignored `data/local`.

Require `status=live_verified`, `provider_requests=1`, `schema_validated=true`, `grounding_validated=true` and a positive `citation_count`. Compare `requested_model`, upstream `actual_model` and `preferred_model_used`; a different returned model is disclosed, not proof that Opus 5 ran. Missing model identity, missing citations, refusal, rate limit or validation failure fails this check without an automatic second request. `observed_cost=null` is expected. If report-file export fails, the CLI preserves the completed result on stdout with `report_write_failed=true` and exits 1: retain that stdout securely, inspect its actual request count, and do not repeat a potentially billable call merely to recreate the file.

## Separate worker → PostgreSQL → protected API proof

This is a **second, explicitly initiated live check** after the dedicated helper. It exercises persistence and can incur additional usage. Keep fallback/research disabled. The ordinary worker may repair invalid output once on the same provider; with one transport attempt per generation, a one-course run can still make two requests. Do not run either test repeatedly to obtain a preferred answer.

Git has not transferred the local evidence database. Import the genuine permitted legacy ESCO subset explicitly, without network acquisition:

```bash
python -m shiftos.cli ingest-evidence --dataset C-ESCO-V103 \
  --file data/reference_packs/esco-v1.0.3.subset.reviewed.json \
  --retrieved-at 2026-10-23T19:57:05.013428+00:00 \
  --report data/local/replit-esco-real-import.json
```

A fresh successful import reports 87 normalized source records (38 occupations, 10 skills, 39 relationships); replay reports `UNCHANGED`. These are genuine legacy source records, not a current taxonomy or Malaysian demand measurement. The separate synthetic analysis lane deliberately cannot use real-lane records. Prepare one **unmodified genuine skill** as a clearly labelled verification copy and create one fictional inventory, using existing models only:

```bash
python - <<'PY'
import copy, json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from shiftos.core.config import Settings
from shiftos.db.session import create_database
from shiftos.models import Course, Institution, Programme, ProgrammeRevision

directory = Path('data/local')
directory.mkdir(parents=True, exist_ok=True)
pack_path = Path('data/reference_packs/esco-v1.0.3.subset.reviewed.json')
pack = json.loads(pack_path.read_text(encoding='utf-8'))
uri = 'http://data.europa.eu/esco/skill/700ea222-8139-4c48-95cf-014855565530'
skill = next(row for row in pack['records'] if row['kind'] == 'skill' and row['key'] == uri)
copy_pack = copy.deepcopy(pack)
copy_pack['records'] = [copy.deepcopy(skill)]
copy_pack['metadata'].update({
    'verification_copy': True, 'original_source_is_synthetic': False,
    'original_source_pack': str(pack_path),
    'adaptation_notice': pack['metadata']['adaptation_notice'] +
        ' One unchanged skill copied into a synthetic verification lane. '
        'Only the university/course association is fictional.',
})
(directory / 'replit-esco-verification-copy.reviewed.json').write_text(
    json.dumps(copy_pack, ensure_ascii=False, indent=2), encoding='utf-8')

ids = {key: uuid5(NAMESPACE_URL, 'shiftos:replit-claude-one-course-v1:' + key)
       for key in ('institution', 'programme', 'revision', 'course')}
database = create_database(Settings().database_url.get_secret_value())
try:
    with database.session_factory() as session:
        def ensure(model, key, **values):
            row = session.get(model, ids[key])
            if row is None:
                row = model(id=ids[key], **values)
                session.add(row)
                session.flush()
            else:
                assert all(getattr(row, k) == v for k, v in values.items()), 'Fixture conflict'
            return row
        ensure(Institution, 'institution', name='SYNTHETIC Replit Verification University',
               country='MY', is_synthetic=True)
        programme = ensure(Programme, 'programme', institution_id=ids['institution'],
            name='SYNTHETIC Bachelor of Water Engineering', discipline_key='engineering',
            is_synthetic=True)
        ensure(ProgrammeRevision, 'revision', programme_id=ids['programme'],
               version_label='synthetic-claude-verification-v1', is_synthetic=True)
        assert programme.active_revision_id in (None, ids['revision']), 'Revision conflict'
        programme.active_revision_id = ids['revision']
        ensure(Course, 'course', programme_revision_id=ids['revision'],
               course_name='SYNTHETIC Irrigation Systems', year=1,
               detailed_syllabus_available=False, is_synthetic=True)
        session.commit()
finally:
    database.engine.dispose()
(directory / 'replit-claude-inventory.json').write_text(
    json.dumps({key: str(value) for key, value in ids.items()}, indent=2), encoding='utf-8')
print('Prepared one fictional course and one attributed, genuine-source verification copy')
PY
python -m shiftos.cli ingest-evidence --dataset C-ESCO-V103 --synthetic \
  --file data/local/replit-esco-verification-copy.reviewed.json \
  --retrieved-at 2026-10-23T19:57:05.013428+00:00 \
  --report data/local/replit-esco-copy-import.json
```

The copy import must report one skill or `UNCHANGED`. Its `is_synthetic=true` identifies the isolated verification copy; its actual ESCO text, concept URI, source locators, edition, attribution and partial-archive limitations remain genuine. No invented ESCO source or fictional academic standard is added. Do not clear existing real/synthetic records or change the lane filters.

Before spending on the worker, prove that the normal internal retrieval path admits the exact quote under the configured source policy. This makes no model/search request:

```bash
python - <<'PY'
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID
from shiftos.core.config import Settings
from shiftos.db.session import create_database
from shiftos.services.analysis.claude_verification import inspect_claude_configuration
from shiftos.services.analysis.retrieval import retrieve_evidence
settings = Settings()
assert inspect_claude_configuration(settings)['status'] == 'configuration_ready'
ids = json.loads(Path('data/local/replit-claude-inventory.json').read_text())
policy = json.loads(settings.analysis_permissions_path.read_text())['sources']
database = create_database(settings.database_url.get_secret_value())
try:
    with database.session_factory() as session:
        packet = retrieve_evidence(session, UUID(ids['revision']), datetime.now(UTC),
                                   permitted_sources=policy)
    assert packet.is_synthetic and len(packet.courses) == 1
    refs = [r for r in packet.references if r.kind == 'skill'
            and r.facts.get('external_id') ==
                'http://data.europa.eu/esco/skill/700ea222-8139-4c48-95cf-014855565530']
    assert len(refs) == 1 and refs[0].model_eligible
    assert refs[0].excerpt == 'irrigation systems: The methods and systems management in irrigation.'
    assert refs[0].id in packet.courses[0].reference_ids
    Path('data/local/replit-claude-admitted-packet.json').write_text(
        packet.model_dump_json(indent=2), encoding='utf-8')
    print('One genuine-source quote admitted; title/content, historical and date limits retained')
finally:
    database.engine.dispose()
PY
python -m shiftos.cli analyse-programme \
  --programme "$(python -c "import json; print(json.load(open('data/local/replit-claude-inventory.json'))['programme'])")" \
  --mode live --no-research --idempotency-key replit-claude-one-course-v1 \
  > data/local/replit-claude-queued.json
python -m shiftos.cli worker --once
```

Use an otherwise idle verification database: `worker --once` processes the next eligible queued job, not a requested job ID. Check that its printed ID matches `job_id` in the queue report. Keep the loopback API process running with the same database, policy and tokens. Read the persisted run and owned course through protected HTTP, with token values supplied from Settings rather than printed in a command:

```bash
python - <<'PY'
import json
from pathlib import Path
from uuid import UUID
import httpx
from sqlalchemy import select
from shiftos.core.config import Settings
from shiftos.db.session import create_database
from shiftos.models import AnalysisRun, CourseFinding, Job
settings = Settings()
queued = json.loads(Path('data/local/replit-claude-queued.json').read_text())
run_id = queued['analysis_id']
headers = {'X-Analysis-Token': settings.analysis_write_token.get_secret_value()}
with httpx.Client(base_url='http://127.0.0.1:8000', headers=headers, trust_env=False) as client:
    response = client.get(f'/api/v1/analyses/{run_id}')
    response.raise_for_status()
    run = response.json()
    response = client.get(f'/api/v1/analyses/{run_id}/courses')
    response.raise_for_status()
    page = response.json()
    assert run['is_synthetic'] and run['status'] == 'SUCCEEDED', 'Inspect failed/partial run'
    assert not run['needs_evidence_revalidation'], 'Recheck current rights/source status'
    assert run['summary_json']['result_mode'] == 'live_model'
    assert page['total'] == 1
    finding = page['items'][0]
    detail = client.get(f"/api/v1/analyses/{run_id}/courses/{finding['course_id']}")
    detail.raise_for_status()
    assert detail.json() == finding
    dimensions = ('foundational_relevance', 'ai_transformation', 'workforce_alignment',
                  'curriculum_currency', 'future_resilience')
    citations = [citation for name in dimensions
                 for citation in finding['result_json'][name]['citations']]
    references = {r['id']: r for r in run['manifest_json']['packet']['references']}
    assert citations, 'No citation returned; citation smoke remains unproven, do not auto-retry'
    assert all(c['reference_id'] in references and
               ' '.join(c['quote'].split()) in
               ' '.join(references[c['reference_id']]['excerpt'].split()) for c in citations)
    assert finding['result_json']['needs_syllabus_confirmation']
    assert finding['result_json']['is_final_curriculum_verdict'] is False
    model = run['manifest_json']['model_processing']
    assert model['status'] == 'verified_output' and model['request_count'] >= 1
    assert all(r['provider'] == 'replit_claude' and r['actual_model'] for r in model['responses'])
    database = create_database(settings.database_url.get_secret_value())
    try:
        with database.session_factory() as session:
            stored = session.get(AnalysisRun, UUID(run_id))
            assert stored is not None and stored.fingerprint == run['fingerprint']
            rows = session.scalars(select(CourseFinding).where(
                CourseFinding.run_id == stored.id)).all()
            assert len(rows) == 1 and str(rows[0].course_id) == finding['course_id']
            assert session.get(Job, stored.job_id).status.value == run['status']
    finally:
        database.engine.dispose()
    Path('data/local/replit-claude-persisted-api-proof.json').write_text(
        json.dumps({'run': run, 'courses': page}, indent=2), encoding='utf-8')
    print(json.dumps({'status': run['status'], 'model_name': run['model_name'],
                      'responses': model['responses'], 'course_count': page['total'],
                      'citation_count': len(citations), 'fingerprint': run['fingerprint']}))
PY
```

These HTTP reads are backed by the migrated PostgreSQL records. Check the same run ID in the Database tool's `analysis_runs` and the one owned row in `course_findings`; `job_id` links its terminal `jobs` record. Re-run the **same queue command** with the same idempotency key only to confirm it returns the identical analysis/job IDs; it must not create another queued model job. Inspect model metadata instead of treating an HTTP 200, `SUCCEEDED` or an offline insufficiency result as evidence Claude ran. If a provider call, quote, permission check or database/API assertion fails, retain the report and mark that step blocked/failed. Never manufacture a source, citation, syllabus or usage amount to complete the checklist.

## Persistence, usage and costs

No new tables, migrations, HTTP routes, dependencies or academic result fields are required. Existing `analysis_runs.manifest_json.model_processing.responses` stores whitelisted per-invocation provider/requested model/returned model/token usage/request count/status. Error codes and fallback transitions are explicit. Model-generation invocations are distinct from actual HTTP attempts. `analysis_runs.model_name` records returned model identifiers only; the selected provider/model remains separate in the manifest. Request/response bodies, headers, credentials and chain-of-thought are excluded from this audit metadata. Protected API retrieval uses the existing source-text redaction/revalidation path.

If policy/inventory changes prevent final publication after a response, a still-running job retains sanitized model usage on its failed run/job without publishing source text or findings. Already terminated jobs reject late writes. Abrupt process loss or cancellation before accounting persists can leave an audit gap; reconcile those requests with Replit's external usage page rather than treating the local manifest as a complete billing ledger.

`observed_cost` remains null when no actual billing amount is available. Token counts do not establish a billed amount. Reconcile actual request timestamps and the relevant app against Replit's external [usage page](https://docs.replit.com/features/integrations/replit-ai-integrations#viewing-your-usage), which documents credit billing by app. Keep any observed charge separately identified with its billing window; do not convert direct-provider price estimates into a claimed Replit invoice. No billing statement is accessible in the local Windows workspace, no actual model has run there, and no cost or model-quality claim is made from mocks.

## Historical Phase 4.1 measured results and stop boundary

The final local suite passed **756 tests**, including **13 PostgreSQL integration cases**, with zero failures/skips; see [STATUS](../STATUS.md) for the measured environment, remaining warning and exact live-test status. Automated provider/worker/database/API tests use explicitly synthetic fixtures and mocked responses; PostgreSQL persistence is verified separately from provider connectivity. All five embedded Python examples were syntax-checked. The fictional-course preparation, explicit 87-record genuine-pack import, one-skill synthetic-lane copy import and exact-quote internal retrieval were also executed successfully in a disposable local PostgreSQL schema, then cleaned up, with zero model/search requests. These checks do not verify Linux/Replit execution or the later live API proof. A blocked preflight is a correctly reported access limitation, not a successful Claude integration smoke.

At the Phase 4.1 stop boundary, live verification was incomplete. The later single Phase 4.2 attempt above did not produce validated structured output or supporting citations, and no worker-to-PostgreSQL-to-API round trip has been run. Live acceptance remains blocked; do not repeat a request without separate approval or start academic actions/pathways.
