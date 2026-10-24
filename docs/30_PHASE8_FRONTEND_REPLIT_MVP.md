# Phase 8 — NORDYC React frontend and controlled Replit MVP

## Scope and acceptance boundaries

Work is isolated to **feature/phase8-react-dashboard**, based on the verified Phase 7 receipt **a921318a2285d33c72df90582b7bdef44108d940**. Phase 7 remains the backend authority. The older **codex/replit-managed-ai** branch is a read-only design reference, not a merge source. FastAPI, PostgreSQL, existing workers, evidence rights, version-bound reviews and managed `claude-opus-5` remain authoritative. Gemini, persistent external processing and research stay disabled. No paid provider request, merge or public release is part of this phase.

The React application is a controlled operator preview. It does not establish production identity, named academic approval, real curriculum accuracy or completed original-source Brave admission. Current measured acceptance and publication receipts are in [STATUS](../STATUS.md).

**Controlled implementation acceptance is COMPLETE.** Published implementation `f8be2582f31619afafc304de8b83587c710059be` and follow-up `2b61d474204b6cdf7d33d75bf8794c6a7a99f1ec` were remote-verified; the latter passed the final Replit tests. The temporary Replit stack was stopped and the original workspace restored after acceptance. Public release remains separately blocked.

Final published executable code **c3dcfe0388844e4f52b94f164c0105f6e80e9357** passed [complete hosted GitHub verification, run 40](https://github.com/RikoHalim/shift-os/actions/runs/40128804263). All frontend/contract/backend/lint/format/dependency/migration steps succeeded. The final receipt changes documentation only and preserves that tested code.

## Design recovery report

The revised NORDYC authored source **was not recovered**. At design-reference commit **ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec**, `frontend` contains generated dependency/cache artifacts and screenshots, without the expected React source. Those artifacts were inspected, never ported. Searches covered local clones/checkpoints, reachable/reflog/unreachable Git objects, two ZIP archives and three Git bundles. The current original Replit checkout also has no authored frontend files. Its history identifies only the older generic SHIFT//OS React explorer at **0ba61629c7a812fa5c7705d48c5e5062292e0237**. That explorer is not the revised NORDYC UI and was not presented as recovered NORDYC source.

This frontend is therefore a **visual reconstruction**, with new functional React components. All seven reference screenshots were inspected:

| Original reference | Preserved pattern |
|---|---|
| [Library desktop](https://github.com/RikoHalim/shift-os/blob/ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec/frontend/test-results/revised-library.png), [mobile](https://github.com/RikoHalim/shift-os/blob/ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec/frontend/test-results/revised-library-mobile.png) | Navy wordmark, restrained top bar, editorial title, category strip/search, dashed creation card and pastel programme covers; two-column narrow library |
| [Industry desktop](https://github.com/RikoHalim/shift-os/blob/ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec/frontend/test-results/revised-industry.png), [mobile](https://github.com/RikoHalim/shift-os/blob/ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec/frontend/test-results/revised-industry-mobile.png) | Context sidebar/breadcrumbs, large heading, pale blue contextual hero, source-first supporting cards |
| [Learning journey](https://github.com/RikoHalim/shift-os/blob/ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec/frontend/test-results/revised-journey.png) | Pastel year panels, course cards, fine timeline connectors, expandable detail and academic review direction |
| [Outcome examples desktop](https://github.com/RikoHalim/shift-os/blob/ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec/frontend/test-results/course-outcome-examples.png), [mobile](https://github.com/RikoHalim/shift-os/blob/ddeb4ccb29d58bd52a3324af6f3ec30f9b6df0ec/frontend/test-results/course-outcome-examples-mobile.png) | Calm document/table presentation, mobile reading order and visible limitations; illustrative outcomes were not copied into actual course findings |

Generated package metadata confirms installed **DM Sans Variable** and **Manrope Variable 5.3.0**. The authored CSS assigning them was absent. The reconstruction uses DM Sans body/navigation and Manrope headings. Latin font files are self-hosted; other scripts use the available sans-serif fallback. No Google Fonts runtime request is needed. The package licences remain available in the installed font packages.

Recreated tokens in [styles.css](../frontend/src/styles.css): navy `#173765`, blue `#326cff`, canvas `#f6f7f9`, sidebar `#edf1f5`, borders `#d9e1ed`, pastel blue `#e9effa`, beige `#f2eee4`, lavender `#eeebf5` and science `#e4eff4`. Foregrounds were darkened during actual accessibility testing. These are reconstructed values, not claimed recovered CSS. Uncategorised programmes retain that explicit state; rotating pastel decoration does not invent a discipline. Long machine revision labels are presented as actual import dates, while exact IDs remain in requests and settings.

The simple SVG academic mark is reconstructed from the visible concept and remains provisional. `VITE_BRAND_NAME` and an optional local `VITE_BRAND_LOGO_PATH` allow approved branding to replace it. No logo is asserted final. The older green palette in [the archived concept](20_NORDYC_VISUAL_CONCEPT.md) is supplementary; the seven later screenshots govern this implementation.

Deliberate differences: illustrative workforce statistics and invented example outcomes were removed; real source insufficiency replaces them. Additional Phase 5/6 sections use the same cards, type and spacing. Eight primary workspace links and contextual plan/scenario/SDG/review navigation keep the expanded workflow manageable. Counts describe persisted inventory, never university quality. Course year/semester/credits remain unknown when absent.

## Components and working pages

| Source | Responsibility |
|---|---|
| [App](../frontend/src/App.tsx), [workspace](../frontend/src/app/workspace.tsx), [session](../frontend/src/app/session.tsx) | Routing, institution/programme/revision context, responsive navigation, scoped access and disconnect |
| [Library](../frontend/src/pages/Library.tsx) | All accessible programme pages, client search/category filtering, actual creation and optional explicit admin institution creation |
| [Overview](../frontend/src/pages/Overview.tsx) | Persisted course/evidence coverage, actual recent job states and next review links |
| [Courses](../frontend/src/pages/Courses.tsx) | Year/unknown inventory, all-page retrieval, exact-revision screening history, five dimensions, provenance and offline job submission |
| [Upload](../frontend/src/pages/Upload.tsx) | Raw PDF submission, signature/type/20 MB checks, actual queue polling, extracted inventory, reviewed JSON correction/re-import |
| [Intelligence](../frontend/src/pages/Intelligence.tsx), [result guards](../frontend/src/lib/results.ts) | Industry, careers, competency matrix, recommendations, pathways, two scenarios, SDG, eight-section plan, evidence and review history |
| [UI components](../frontend/src/components/ui.tsx), [evidence drawer](../frontend/src/components/EvidenceDrawer.tsx) | Consistent statuses/cards/forms, exact review actions, fresh permission-checked citations and accessible native source dialog |

Synthetic source inputs and explicitly mocked model execution are labelled separately from actual committed programme records. A proposed pathway is not student completion. A possible SDG contribution is not achieved impact. The UI does not infer employment probability, replacement risk or definitive course obsolescence.

## API, authentication and privacy

[OpenAPI](../frontend/src/api/openapi.json) is exported from the actual application without a database/provider request. [Generated TypeScript](../frontend/src/api/generated.ts) follows that schema; [the client](../frontend/src/api/client.ts) validates successful responses against the same JSON Schema using AJV2020. Completed career/plan/finding payloads receive additional exact programme/revision/parent checks. Pending/failed/withheld objects are not treated as completed academic results.

All browser requests are same-origin `/api/v1` through the development proxy; redirects are refused. Credentials are opaque bearer grants retained only in memory. They are never compiled into a bundle, put in a URL or saved in local/session storage. Disconnect/reload clears access. `GET /api/v1/access-context` exposes actual permissions, institution scope and safe configuration flags, without hashes, policy paths, provider endpoints or credentials. An operator alias is not named academic identity. Legacy mode does not pretend to grant an authenticated UI context.

Request cancellation, 30-second timeouts, a 4 MiB response bound, safe error codes and no automatic retry prevent accidental repeated submissions. Mutations have explicit offline mode and unique idempotency keys. A timeout has unknown outcome: inspect history before retrying. The resource hook fences programme/revision changes synchronously, aborts/unmounts safely, clears hidden-tab data, revalidates on focus and removes source-derived data after failed reads. Source-bearing results refresh while visible. No private excerpt is stored persistently in the browser.

Evidence inspection re-fetches the rights-checked career/plan evidence pages (or Phase 4 packet) and checks every page. Excerpts require current internal eligibility and explicit excerpt-output permission. Revoked/unavailable data has a withheld state; old text/links are cleared. Raw global `/sources` and `/evidence` administration remains admin-only. Search snippets never become admitted sources through the frontend.

Review controls require the actual review grant and the persisted recommendation database ID/version or plan fingerprint. They re-fetch current eligibility immediately before posting and preserve the originally displayed expected version so changes yield conflict, not silent approval of a different result. Reasons and server review history remain explicit. The server establishes the actor; the UI cannot supply one.

## Upload and analysis boundaries

PDF uploads use the existing raw `application/pdf` endpoint, not multipart. Official institution/programme origins must already be configured; no origin is invented. HTTP 202 only means queued. The UI waits for actual worker completion and retrieves committed records for the returned revision. Missing layout/fields and failed jobs remain visible. Queue age is not a worker heartbeat; the UI reports availability as unknown rather than claiming an offline worker.

There is no unsupported PATCH/approve-extraction endpoint. Corrections use a complete source-attributed `ProgrammeImport` with exact title excerpts, explicit human review confirmation and a new immutable revision. The UI does not expose private original files through a public static route. An administrator may need to inspect the original separately. Empty new career mapping inputs produce honest insufficiency. Rich supported findings require reviewed registered mappings and curriculum passages; titles cannot replace them.

## Local setup and controlled demonstration

Use Python 3.12+, compatible Node (22.12+ or supported 24), and an **explicitly owned disposable loopback PostgreSQL test database**. Never supply an unknown shared/production database. The historical Windows clusters are not Replit deployment databases.

```text
python -m pip install -r requirements.lock
python -m pip install -e ".[dev]"
cd frontend
npm ci
cd ..
python scripts/preview_synthetic.py --database-url <OWNED_LOOPBACK_TEST_DATABASE_URL> --port 8008
```

The explicit preview launcher creates a new randomly named owner-marked schema and applies existing migrations through `0007_academic_action_plans` only there. It drives the existing protected import/worker/analysis/review workflow for computing, accounting and biotechnology, six courses each. Opt-in dataset namespaces prevent one discipline replacing another's frozen fixture source. API and worker use the same injected database and private uploads. Provider credentials are cleared, all model adapters explicitly mocked, and provider HTTP is blocked. Stored evidence, job statuses, results and review versions are genuine database records; model semantics remain synthetic/mock.

The launcher writes private random scoped credentials and a credential-free receipt under ignored `data/local`. It does not print the credential. A second terminal starts Vite in `frontend` with `BACKEND_ORIGIN=http://127.0.0.1:8008`, `FRONTEND_PORT=5178`, then `npm run dev`. Enter the scoped credential privately in the password field. Never paste it into chat or commit it. Read/write/review, read-only, foreign-institution and explicit admin grants support controlled acceptance. Stop using the per-run `STOP` file; cleanup removes credentials and only its exact owned schema, after the worker stops. Private interrupted originals remain subject to administrator reconciliation.

The demo sequence is library → selected programme/revision → course inventory → source viewer → career/competency matrix → recommendation alternatives → pathways/resources → two hypothetical scenarios → SDG contribution → Action Plan and explicit review. No manual database editing between screens is required. New programme/PDF/JSON imports and offline screening exercise the real job path.

For an ordinary selected development database, configure a private scoped policy, apply migrations explicitly, and start FastAPI plus the existing worker separately. The synthetic launcher is opt-in; ordinary app startup does not seed, migrate or silently install mocks.

## Replit development preview and public release gate

The branch's `.replit` starts Vite; Python/API/worker setup remains explicit. Only frontend 5173 is mapped to the development web output. The API 8008 and test PostgreSQL 55450 remain loopback. The original Replit checkout must not be switched or overwritten: use a separate ignored Phase 8 checkout. Install dependencies there, select a newly owned local test database, then run the same explicit synthetic launcher and Vite proxy. Do not point it at ambient `DATABASE_URL` or transfer private Windows data.

Vite permits only its frontend root and explicit Replit development hostname, with no wildcard-host/CORS bypass. Private environment files, credentials, checkout-local runtime data, tests and reports are denied. The backend still enforces bearer scope even through the proxy. Node/Python runtime and actual database/worker acceptance must be observed in Replit before calling that preview complete.

The actual Replit acceptance used an ignored `data/local/phase8-preview-src` clone of the Phase 8 branch, Python **3.12.12**, official Nix Node **22.16.0**, PostgreSQL **16.15** and the provided Chromium **152.0.7977.64**. The original `codex/replit-managed-ai` checkout was not switched or pulled. A new owned loopback cluster on 55450 and database `shiftos_phase8_replit_test` supplied a randomly named, owner-marked schema. All existing migrations through 0007 ran there. API 8008 and the actual polling worker shared that database; only frontend 5173 was forwarded. Replit's older Run/Preview pane still targets the original checkout, so its “not running” message did not describe the separately started Phase 8 processes. The forwarded development hostname was checked separately and loaded the protected NORDYC login.

Replit's default `PIP_USER` prevented installation into a virtual environment. Setting **`PIP_USER=false` only for the isolated setup process** resolved this without changing account/root configuration. The equivalent separate-checkout dependency setup is:

```sh
python -m venv .venv
PIP_USER=false .venv/bin/python -m pip install -r requirements.lock
PIP_USER=false .venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
nix-shell -p nodejs_22 --run 'npm --prefix frontend ci --ignore-scripts'
```

Then select/start only an explicitly owned test PostgreSQL cluster, verifying its owner marker, resolved data directory and free loopback port first. Run the documented `preview_synthetic.py` launcher with that explicit `_test` database URL; start Vite separately from `frontend` with `BACKEND_ORIGIN=http://127.0.0.1:8008`, `FRONTEND_HOST=0.0.0.0` and `FRONTEND_PORT=5173` through `nix-shell -p nodejs_22 --run 'npm run dev'`. These steps do not copy local Windows records or select ambient `DATABASE_URL`. No private policy, provider credential or upload is transferred.

The Replit browser run used the same six checked-in cases and an **ignored configuration outside the frontend** that extended the base configuration with the observed `/repl/tools/bin/chromium` executable, absolute test/output paths and private scoped-grant file. No trace, video or credential-entry screenshot was recorded. Current installations should verify the actual provided browser/version before using that optional override; the normal local suite uses Playwright's matching Chromium 156. The final cloud run passed **6/6 in 43.9 seconds**, including actual creation/PDF/JSON/worker/screening/review reads, responsive behavior and access denial. Source-withdrawal/pending/API-failure cases remain explicitly injected tests.

An independent PostgreSQL connection verified the owned data directory/schema marker and committed migration head. After the initial and final browser runs it read **5 programme records, 30 course revision records, 18 jobs, 24 course findings, 3 career runs, 3 plans, 5 plan reviews and 246 evidence references**. Twelve jobs succeeded and six returned explicit PARTIAL evidence-limited outcomes; no failed job was observed. The polling worker completed six browser-created jobs with no last error. These counts are synthetic workflow receipts, not authentic university coverage or academic performance.

After acceptance the worker/API were stopped through the owned STOP mechanism, the exact preview schema and credential removed, frontend stopped and only the owned PG cluster stopped. The test cluster files remain private and stopped; restarting the launcher creates a new schema, seed and grant. Replit had automatically appended a 5173 port mapping to the original `.replit`. Its structure was compared against the baseline to confirm this was the only change, then the exact original bytes were restored. All **215** original tracked/nonignored file hashes and the original HEAD matched the baseline; the temporary terminal preference was also restored. A generic original-workspace Run action is not the Phase 8 launch procedure. Nothing is currently publicly deployed or left running in Replit by this acceptance.

[Replit port documentation](https://docs.replit.com/features/project-setup/ports) describes explicit local/external mappings and loopback exposure. [Vite server documentation](https://vite.dev/config/server-options) explains explicit allowed hosts, filesystem restrictions and proxying. Development forwarding is not a public production deployment. No Publish action is authorised here.

Public release remains blocked on named-user identity/appropriate authentication, operational tenant checks, selected persistent PostgreSQL, durable private shared uploads, supervised workers, backups/restore, edge limits/TLS, logging/retention and source-use acceptance. Replit Secrets remain the place for managed Anthropic and Brave credentials; no frontend variable may contain them. A new paid live Phase 5/6 test requires a fresh explicit budget and source consent.

## Verification and reproducibility

```text
python scripts/export_frontend_contract.py
cd frontend
npm run contracts
npm run typecheck
npm run test
npm run build
npm run format:check
npm audit
# Configure SHIFTOS_PREVIEW_AUTH to the ignored local auth.private.json,
# and SHIFTOS_FRONTEND_ORIGIN to the explicit loopback frontend origin.
npm run test:browser
```

The browser suite uses actual socket HTTP, the worker and owned PostgreSQL for its main journey, creation, upload, offline jobs and persisted review reads. Its tiny PDF/import input is generated from labelled synthetic source metadata and actual authorised IDs. Fault-injection tests are identified separately from genuine backend operations. Browser traces/video and automatic failure screenshots are disabled to avoid credential capture; explicit screenshots are taken only after credential entry has unmounted. Desktop/mobile/tablet, keyboard/dialog/menu behavior, Axe, console errors and real controls are checked. Screenshots prove visual observations only; functional assertions are separate.

The development preview passed **6/6 browser cases in 33.5 seconds**. The final six cases passed against the locally built production preview on loopback 5179 in **32.7 seconds**, and against Replit's development preview in **43.9 seconds**, using their actual protected API, worker and owned PostgreSQL environments. The production test verifies the built route chunks and proxy locally; it is not a production Replit deployment. Completed desktop/tablet plan Axe samples in each environment reported **zero violations at every impact**. Sampled automation is not comprehensive WCAG certification.

The development connected-library observation was **1,184 ms** (76 responses / 16 cancelled effect requests); the final local production observation was **1,091 ms** (58 responses / 2 cancelled effect requests), and Replit **1,551 ms** (74 responses / 26 cancelled effect requests). All measured sessions had **0 HTTP errors/noncancelled failures and 0 console/page errors**. These are single observations, not performance benchmarks or cloud SLAs. Credential-free local development/production observations remain separate under ignored `frontend/test-results`; the earlier production 1,036 ms / 57 / 3 observation is retained with a pre-summary-fields suffix. Replit verification/database/cleanup receipts are also ignored. None contains raw operator credentials, and they are not published as source.

Full backend acceptance: **1,098 passed**, including **21 real PostgreSQL cases**, **0 failures/errors/skips**, **201.15 seconds** in the final CI-provider-environment rerun (the earlier normal-environment run took 201.73 seconds). This preserves Phase 7's 1,078/20 baseline, adding 20 tests/one real HTTP+worker PostgreSQL case. Ruff, dependency integrity, Alembic upgrade/head/drift/offline SQL and whitespace passed. Final frontend tests **73/73** passed both locally and in Replit; types/format/build/audit also passed with zero reported vulnerabilities. The complete backend suite ran locally; the actual Replit acceptance and independent DB read are separate observations, not a claim that the full backend suite ran again in Replit. Current build sizes are recorded in STATUS. **Zero live Claude/Brave/Gemini requests** were made; no new real model token/latency/billing measurements exist. No test-only result establishes real academic accuracy.

The initial hosted CI run found three inherited-environment assumptions in old mocked-provider fixtures: the workflow selects Claude, while those fixtures intended a Gemini/unselected-Claude baseline. The two affected test files now set the intended test provider explicitly and block both sync/async HTTP. The parameterised test checks each explicit mock selection. **No application provider/default or runtime Gemini flag changed.** Targeted 51 and complete 1,098 local cases passed under CI settings; hosted **run 40 subsequently passed all checks** on the final code.

Subsequent hosted runs passed backend tests and migration/dependency checks, then found Python-version documentation labels. Comparing all status definitions against [official CPython 3.12 source](https://github.com/python/cpython/blob/v3.12.12/Lib/http/__init__.py) and the tested 3.13 standard library identified four changed reason phrases: 413/414/416/422. The exporter canonicalises only those known aliases, preserving custom descriptions and every schema, payload and endpoint. Two actual exports with the **complete** 3.12 and 3.13 phrase mappings produced identical hashes and regenerated checked-in OpenAPI/TypeScript with no diff. This is deterministic documentation metadata; CI still rejects schema/type drift. The frontend/contract steps now precede the longer backend suite so such failures surface sooner, with every existing check retained.

## Limits and final MVP acceptance

- Brave original-source admission remains **PARTIAL**; no new original is admitted by a frontend view.
- Real programme/occupation and syllabus/skill evidence, current dated signals, resource availability and independent expert assessment remain limited.
- New category filters use stored discipline metadata only; missing categories are uncategorised, never inferred from a university's title.
- Scoped operator review is not named-user approval; controlled preview is not production security.
- Organiser permission to replace individual skills intake, person-to-role matching and personalised pathways remains **UNCONFIRMED**. No CV/student data collection was added. The least additional contingency is an explicitly approved, minimal individual profile using the existing reviewed competency structures, after written scope clarification.
- Final MVP acceptance should confirm the visual comparison, all-page evidence/unknown states, actual upload/review and exact-version writes, clean test/build/security checks, the selected Replit runtime/database/worker receipt, private storage and recovery, new live-test consent if required, and written organiser scope before public release.

Stop after Phase 8 implementation, testing and feature publication. Do not merge or release publicly without separate authorisation.
