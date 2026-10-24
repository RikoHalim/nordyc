# Phase 4.2 — live backend acceptance

**24 October 2026: PASS / COMPLETE for the bounded backend verification.** The actual protected FastAPI submission → separate CLI worker → Replit-managed `claude-opus-5` → PostgreSQL commit → protected FastAPI retrieval passed. This is a software integration proof on fictional courses, not validation of real curriculum quality. Brave live acceptance remains a separate pending gate. Phase 5–8 are not implemented by this work.

## Source and publication

Work is isolated on `codex/replit-managed-ai` in [RikoHalim/shift-os](https://github.com/RikoHalim/shift-os/tree/codex/replit-managed-ai). The previously accepted Claude compatibility fixes were reviewed against the exact Replit file hashes and published as [a33e5795823367147084368d870aa5ba4b74735c](https://github.com/RikoHalim/shift-os/commit/a33e5795823367147084368d870aa5ba4b74735c). The final live-tested acceptance controls, scripts, tests and documentation were published as **[e36ab065b48957419355c13b6248ec4b58aa087b](https://github.com/RikoHalim/shift-os/commit/e36ab065b48957419355c13b6248ec4b58aa087b)**, with the exact remote SHA verified. This subsequent receipt changes documentation only; main and the Gemini branch are unchanged. See STATUS.md for the publication checks.

Development, review, tests and Git publication used an isolated local Claude checkout. The original local Gemini checkout remained unchanged. Replit supplied the existing managed Anthropic connection and ran the Linux acceptance workflow. Its divergent native checkpoint history was preserved; no reset, pull-overwrite, merge, force-push or public deployment was used. No credential or private dataset was copied into the local checkout.

## Actual observations

The owner explicitly approved **one** end-to-end request with a **$1** spending limit. No historical isolated smoke was repeated. The worker alone received a process-scoped true external-processing gate. The API and parent process kept the gate false; `.env`, Secrets and the persistent `.replit` gate were not changed.

| Check | Observation |
|---|---|
| Environment | Replit Python **3.12.12**, isolated loopback PostgreSQL **16.15**, database `shiftos_phase42_e2e` |
| Migrations | Existing revisions applied through **`0005_programme_analysis`**; live `alembic check` and offline SQL compilation **PASS**, no application schema change |
| Protected submission | Missing token **401**, authorised POST **202**, correct programme/revision, durable job **QUEUED** |
| Actual execution | Separate `python -m shiftos.cli worker --once`, **one** adapter invocation and **one** HTTP attempt, no retry/repair/fallback/research |
| Model | Requested and returned **`claude-opus-5`**, HTTP **200**, model processing `verified_output` |
| Coverage | **2/2** courses validated from the real model, **0** deterministic fallback courses, job **SUCCEEDED**, result mode `live_model` |
| Structured result | JSON, original Pydantic schema, course identity and grounding validation **PASS** |
| Citations | **3** valid occurrences of the one admitted ESCO quote; exact text and scope, source/version/reference identities and rights checked |
| Uncertainty | Both title-only courses retained `needs_syllabus_confirmation=true`, final verdict false, all five dimensions `insufficient_evidence`; the unmatched course had no citations |
| Aggregation | Existing application-derived programme counts/insights validated; inventory **2**, returned **2**, review required **2**, insufficient evidence **2** |
| PostgreSQL | Run, both findings, frozen provenance, actual model, tokens and job timestamps committed; a new independent engine/connection read the committed state |
| Protected retrieval | Authorised run and course-list GETs **200**; missing/wrong token **401**; both stored courses returned; evidence revalidation flag false |
| Usage | **6,718 input**, **2,496 output**, **0 cache creation**, **0 cache read** tokens |
| Timing | Provider generation/transport measurement **25,540.276 ms**; worker subprocess **27,477.066 ms**, including startup/database work |
| Job timestamps | Started **2026-10-24T15:08:08.380840+00:00**, completed **2026-10-24T15:08:34.371685+00:00** |
| Observed billing | **Unavailable**, `observed_cost=null`. No invoice or account-usage charge was verified |

At the published [Opus 5 standard rates](https://platform.claude.com/docs/en/models/opus-5/overview) of $5/million input and $25/million output tokens, the returned counts imply **$0.09599** as an uncached token-price estimate. It is not an observed charge. [Replit documents public API pricing billed through credits](https://docs.replit.com/features/integrations/replit-ai-integrations). Neither this successful request nor earlier rejected requests is asserted free. The software enforces request/token/byte limits, not an account-level dollar cap.

The zero-call rehearsal also passed the real loopback HTTP API → worker → PostgreSQL → protected retrieval path: **2** findings, independent database read, original schema/grounding checks, **0** model calls, worker **1,619.491 ms**. This is separate from the live result above. This acceptance made **1** new live Claude request, **0** Gemini requests and **0** Brave requests. The five older diagnostic attempts remain historical observations in STATUS.md.

## Fixture and evidence limitations

The fictional institution is `SYNTHETIC Phase 4.2 University`, programme `SYNTHETIC Bachelor of Water Engineering`. Its two year-one title-only courses are `SYNTHETIC Irrigation Systems` and `SYNTHETIC Engineering Ethics`. There are no invented syllabi, learning outcomes, workforce numbers or real-university teaching assertions.

The sole admitted quote is **“irrigation systems: The methods and systems management in irrigation.”** Its real origin is the European Commission's [ESCO concept](http://data.europa.eu/esco/skill/700ea222-8139-4c48-95cf-014855565530), legacy **v1.0.3**. This service uses the ESCO classification of the European Commission. The unchanged excerpt and attribution come from the existing reviewed subset and isolated Claude fixture. Publication date is unknown, currentness unproven, and the original archive retrieval was partial. Its copy and fictional association are labelled synthetic; database metadata retain original non-synthetic source identity, locator, edition, artifact hashes, attribution, adaptation notice and permissions.

Only `C-ESCO-V103` is admitted under the existing three explicit processing/output grants. The normal database retrieval and sufficiency path ran. It reported missing academic standards, occupations, workforce observations, dated AI evidence, source dates and syllabus confirmation. Missing families were not filled with artificial statistics. This narrow run verifies safe abstention and a benchmark citation, not substantive academic/workforce findings or accuracy across disciplines. Deterministic workforce calculations remain unchanged and are tested separately.

Brave credentials are **absent**, `RESEARCH_ENABLED=false`; the configured research policy retains **9** allowlisted dataset IDs. Offline discovery/provenance/permission regressions passed. No search was called and no snippet was admitted. Live Brave still requires its key, applicable source/storage permissions and separate spending approval.

## Reproduce only after new approval

The committed scripts are acceptance tools, not a new analysis implementation:

```bash
# Inside a dedicated Replit development checkout with PostgreSQL tools installed:
.venv/bin/python scripts/phase42_database.py prepare
.venv/bin/python scripts/verify_phase42.py prepare
.venv/bin/python scripts/verify_phase42.py rehearse
# STOP: obtain fresh explicit approval and a spending limit before live execution.
# Never repeat this command on an existing completed acceptance case.
.venv/bin/python scripts/verify_phase42.py live --approved-budget-usd 1
```

`phase42_database.py` uses only its marked cluster under ignored `data/local/phase42-e2e`, loopback port **55445** and database/role **`shiftos_phase42_e2e`**. It ignores ambient `DATABASE_URL`, verifies `SHOW data_directory`, refuses an existing unowned cluster/occupied port and never deletes data. Local trust authentication is confined to this disposable loopback test cluster and private socket directory; it is not a deployment database configuration. The API binds loopback **18542** and is terminated after the test. No port is exposed publicly.

`verify_phase42.py` applies the existing migrations, seeds labelled records, measures the actual outbound request offline with MockTransport, then exercises the existing protected endpoints and CLI worker. The measured request was **15,874 bytes**, below its **24,576-byte** cap; output cap **6,144**, timeout **60 seconds**, transport and validation-attempt caps both **1**. Research, Gemini and cross-provider fallback are false. A private local operator token is generated without printing it. A live receipt is exclusively reserved before submission; an existing receipt prevents another request even after a failure. Do not delete receipts to bypass this safeguard. Inspect saved results and obtain new approval before preparing a different paid case.

Reports, API token, PostgreSQL files, worker/API logs and synthetic outputs remain ignored under `data/local`. Re-running prepare makes no model request; rehearse/live are acceptance cases with stable IDs/idempotency keys, not repeated benchmarks. Stopping the isolated cluster retains its data:

```bash
.venv/bin/python scripts/phase42_database.py stop
```

After all regressions, another connection confirmed both live findings still present. The temporary API had already terminated; the isolated PostgreSQL cluster was then stopped successfully with **data retained**. It can be restarted with prepare without making any model call. The live receipt remains reserved.

## Regression and hosting assessment

- Full local suite: **770 passed**, **0 failed/skipped**, **13** real PostgreSQL cases included; Python **3.13.13**, PostgreSQL **16.15**, **87.27 s**. One existing Starlette/httpx deprecation warning.
- Full Replit suite: **770 passed**, **0 failed/skipped**, the same **13** PostgreSQL cases included; Python **3.12.12**, PostgreSQL **16.15**, **50.35 s**. One existing warning. Test subprocess credentials were removed; API calls were mocked. This is separate from the one accepted live request.
- The prior exact Claude source passed **763** tests before seven bounds/metadata regressions were added. Gemini's historical **794** tests belong to a different branch; that count is not a regression target for this source tree.
- Ruff lint/format, dependency integrity and Alembic checks passed for application sources/tests/migrations/scripts. Replit-wide lint initially also inspected unrelated `.local/skills` metadata and found two pre-existing issues there; those files were preserved and the complete project scope was checked explicitly.
- Existing migrations and permission, citation, worker/API and publication-fence regressions remain intact. No new dependency, table, endpoint or academic schema was added.

Replit remains the official future host. Managed Anthropic credentials/base URL stay provisioned by Replit. Development and production need a separately configured `postgresql+psycopg` URL with actual credentials/TLS options, operator tokens and explicit source-use policy. The ambient Replit `DATABASE_URL` is presently rejected by Settings outside test mode; it was not used or changed. This isolated proof does not configure the ordinary app's persistent database or transfer Windows data. Before normal development startup, choose the intended development PostgreSQL database explicitly; production setup and public deployment remain later work.

Run existing Alembic upgrades against the selected environment before starting FastAPI, and run the existing durable worker separately. Production ports/secrets, worker supervision, persistent database service, network access to the managed bridge/Brave and application-level authentication/security need the later hosting/integration phase. Preserve timeouts, source gates, safe error metadata and false persistent external-processing gate. This loopback cluster is a test tool, not production provisioning.

Phase 4.2's bounded backend completion criteria are met. Phase 5 may be planned after owner review, with genuine syllabus/benchmark/workforce admission, conservative evidence gaps and pending Brave acceptance carried forward. No Phase 5 implementation is authorised by this result.

## Later Phase 7 compatibility note

The historical ordinary-runtime DATABASE_URL rejection above describes Phase 4.2, not a new failure result. Phase 7 now normalizes explicitly configured standard PostgreSQL URIs to the existing psycopg3 driver and adds non-billable runtime/access/schema inspection. It does not provision, access or migrate the original Replit database or transfer local data. See [the current operations contract](29_PHASE7_INTEGRATION_EVALUATION_SECURITY.md).
