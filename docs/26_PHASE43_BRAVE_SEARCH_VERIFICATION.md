# Phase 4.3 — Brave Search and evidence verification

**24–25 October 2026: PARTIAL. Live Brave API: PASS. Live original-source admission: BLOCKED.** One approved request succeeded, but no returned URL matched an exact registered source endpoint. A separate attempt to acquire the existing approved DOSM original stopped at `robots_unavailable`. No new source facts were admitted. These outcomes preserve the evidence contract; they are not successful end-to-end external evidence acceptance.

Phase 4.2's real Claude/worker/PostgreSQL/API proof remains complete. This phase makes **zero** real Claude or Gemini calls, changes no academic schema and implements no Phase 5/6, frontend or deployment. Work and publication remain confined to `codex/replit-managed-ai`.

## Configuration and consent

The owner added **`BRAVE_SEARCH_API_KEY`** through Secrets in the correct NORDYC Replit app. Only key presence was inspected; the value was never printed, copied into the local development checkout or published. Brave uses its own API account and billing; Replit-managed Anthropic credits do not provision a Brave key.

| Setting / contract | Value and meaning |
|---|---|
| Endpoint | `GET https://api.search.brave.com/res/v1/web/search` |
| Authentication | Server-side `X-Subscription-Token` header; never URL/query authentication |
| Activation | Existing `RESEARCH_ENABLED`; persistent value remains **false**. The approved test's Settings object alone enabled research |
| Analysis privacy gate | `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=false` throughout; no live model invocation |
| Request parameters | `q`, `count=10`, `search_lang=en`, `result_filter=web`, `extra_snippets=false`, `summary=false` |
| Country | No country parameter is sent; Brave's documented default applies. The query names Malaysia; that does not prove geographic applicability of any result |
| Query limits | At most **600 characters / 75 words**; controlled discipline/gap templates, never uploaded prose or personal data |
| Normal configured ceilings | Up to **10** logical queries, **2** templates per gap, **10** original documents, **180 seconds** total; transport timeout/attempt settings remain bounded |
| This accepted search scope | **1 query / 1 HTTP attempt**, no retry, **20-second** search timeout; **60-second** research deadline, at most **1** registered original, original response cap **5 MB** |
| Source admission | Exact registered URL, approved access/reuse, explicit analysis permission, safe original acquisition, deterministic parsing and actual persisted source facts |
| Search-result storage | **false**; snippets, titles, unknown URLs and raw Brave bodies are not retained in audit/cache or admitted as evidence |

The [official API reference](https://api-dashboard.search.brave.com/api-reference/web/search/get) supports this endpoint/header/query contract. [Brave's published Search price](https://brave.com/search/api/) was **$5 per 1,000 requests** at review: **$0.005** is the one-request price estimate, not an observed charge. Free-credit eligibility, account balance and storage entitlement were not assumed. The owner explicitly approved **one request up to $0.05** and at most one permitted DOSM original download. The software enforces request/timeout/byte limits, not an account-level dollar ceiling. Further paid calls require fresh approval.

## Actual live observations

The zero-call Replit preflight found the credential, correct endpoint, approved existing `D-EMPLOYMENT-SECTOR` source rules and all three required analysis/output permission flags. It reported `READY_FOR_SEPARATE_LIVE_APPROVAL`, with research and external AI processing persistently false and **0** provider requests.

After approval, `scripts/verify_phase43.py live --approved-budget-usd 0.05` exercised the existing `BraveSearch` and `ResearchService`, rather than an alternative search implementation:

| Observation | Result |
|---|---|
| Query | `site:open.dosm.gov.my Malaysia employment sector statistics` |
| Query category | Generic workforce context; no private course content, student data or credentials |
| Actual Brave requests | **1**, HTTP **200**, no retry |
| Search response | **10** web results, **10** filtered/deduplicated HTTPS discovery pointers; these remain candidates |
| Measured search duration | **1,156.641 ms** |
| Completion timestamp | **24 October 2026, 23:52:26.516764 Asia/Makassar** (`2026-10-24T15:52:26.516764+00:00`) |
| Returned rate metadata | Numeric allowlisted limit/policy/remaining/reset fields available; these are quota observations, not an invoice |
| Registered URL matches | **0**; `unregistered_sources_require_operator_policy`, candidate count **10** |
| Linked original attempts / imports | **0 / 0**; `version_ids=[]`, `requires_sufficiency_recheck=true`, status `INSUFFICIENT_EVIDENCE` |
| Actual billing | **Unavailable**, `observed_cost=null`; no claim that the request was free |
| Model usage | Claude **0**, Gemini **0**; no model tokens or model costs incurred by this phase's live verification workflow |

The real result demonstrates authenticated Brave transport and safe candidate handling. It does not demonstrate discovery-to-admitted-evidence success. Unknown URLs were not retained merely to create a successful report. The app's operator-owned query, aggregate counts, source decisions and safe request metadata are retained; unlicensed result text is not.

## Original-source attempt and manual fallback

The existing registered reference is DOSM / OpenDOSM **Employment by MSIC Sector and Sex**, `D-EMPLOYMENT-SECTOR`. Its catalogue is [OpenDOSM](https://open.dosm.gov.my/data-catalogue/employment_sector) and its registered artifact is [the official CSV](https://storage.dosm.gov.my/labour/employment_sector.csv). Existing acquisition rules already approve access/reuse with DOSM attribution under the recorded CC BY 4.0 terms. This is broad survey employment stock share, **not** occupation vacancies, skill demand or university teaching evidence.

Because none of the ten results exactly matched a registered endpoint, a **separate independent check** of this already registered original was performed through the existing `run_ingestion`/`DatasetFetcher` path, within the approved one-original limit. It made **no additional Brave or model request**. This check must not be described as a source selected from the returned Brave results.

Its actual outcome was **FAILED**, `robots_unavailable`: the fetcher could not establish an acceptable readable robots policy. This code does not establish the exact upstream HTTP response or a confirmed explicit `Disallow`. No protection, DNS pinning, host restriction, robots setting, content validation or source permission was weakened. **0** records were imported, and the analysis step correctly reported `BLOCKED_BY_ORIGINAL_ACQUISITION`.

The dedicated PostgreSQL database retained the source registry metadata, failed ingestion job and search operational cache. It did **not** receive a new DOSM source version, observation, evidence excerpt or supporting citation from these live attempts. Registry presence is not evidence admission. No restricted material or search snippet filled this gap.

The documented manual-original fallback remains available after an operator supplies a permitted original file with its genuine original retrieval time and provenance for review:

```bash
python -m shiftos.cli ingest-evidence --dataset D-EMPLOYMENT-SECTOR \
  --file <PERMITTED_ORIGINAL_CSV> --retrieved-at <ACTUAL_AWARE_ORIGINAL_TIMESTAMP> \
  --report data/local/phase43-manual-import.json
```

Local import preserves the original bytes/hash and registered endpoint; it does not authenticate an arbitrary file or grant rights. The current workspace has no such original available. The Phase 3 report's historical **225-record** import and checksum remain historical observations, not a fresh import in this Replit test. Do not manufacture a file, timestamp or source registration to close this gate.

## Retained research architecture and narrow changes

The existing programme worker first retrieves internal PostgreSQL evidence and evaluates the evidence packet. It avoids external research for offline, historical-cutoff, request-disabled, synthetic, no-gap and unsupported/private-discipline cases. Only configured important gaps generate allowlisted generic queries. The live acceptance driver calls that existing generic research component directly; it never relabels a fictional university as real to trigger automatic research.

Results only nominate candidates. Full registered origin/path/query matching is required; a publisher hostname alone is insufficient. The existing secure acquisition boundary checks reviewed hosts, public DNS/IP pinning, redirects, robots, rate limits, MIME, size and time. Existing deterministic source adapters, immutable source versions and citation references are reused. Successful research admission requires actual persisted, non-rejected facts and a sufficiency recheck; an ingestion status string alone cannot establish success.

This phase adds:

- Brave per-invocation metadata: actual HTTP attempts, HTTP status, duration, raw web-result count, filtered-pointer count, numeric quota fields, fixed error code and null observed cost. Request/query/body/header secrets and arbitrary upstream fields are excluded.
- Research `search_request_count`, separate from existing logical `query_count`. Cache-hit tests prove the latter may be **1** while actual new requests are **0**. Cached metadata does not impersonate another paid request.
- Deduplication of equivalent discovery pointers. Existing dataset/version/import deduplication was already present and remains intact.
- One missing `sector` field in the existing lexical candidate matcher, allowing an admitted sector observation to be associated for review. This does not establish occupation identity, demand, taught content or a substantive workforce-alignment finding.
- A receipt-guarded acceptance script and **18** additional regression cases, reusing all academic contracts and existing tables. No new dependency, migration, endpoint or application agent/provider was added.

The default research cache retains only operator-owned operational outcomes and registered original-source lineage. It rechecks permission/policy hashes, expiry, rejected references and persisted version identity. Positive verified lineage uses the existing one-hour TTL; negative operational outcomes use five minutes. Result storage is not enabled without the plan's applicable entitlement and explicit policy. Search/source content remains untrusted data, never application/model instructions.

## Automated and PostgreSQL verification

| Check | Measured result |
|---|---|
| Complete local suite | **788 passed, 0 failed/skipped**, **14 PostgreSQL integration cases included**, **88.37 s**; Python **3.13.13**, PostgreSQL **16.15** |
| Complete Replit suite | **788 passed, 0 failed/skipped**, **14 PostgreSQL integration cases included**, **50.84 s**; Python **3.12.12**, PostgreSQL **16.15**; live APIs disabled and credentials removed from test subprocess |
| New provider/research regressions | Success; 400/401/403/429/500; one-attempt accounting; disabled/missing keys; malformed replies; numeric quota sanitization; duplicate pointers; metadata reset; positive/negative cache hits |
| New PostgreSQL case | Mocked Brave → golden public DOSM excerpt → actual deterministic parser → PostgreSQL lineage → candidate retrieval → mocked Claude worker → protected API → independent committed read; fabricated quotes rejected |
| Acceptance guards | Missing-key preflight has zero HTTP; invalid/missing budget refuses before setup; an existing receipt prevents repeat execution; exact real source facts can be copied into an explicitly synthetic analysis association without altering origin |
| Existing academic/security tests | Source permissions, unknown/stale/geographic/occupation scope, SSRF, redirects/robots, snippets, prompt boundaries, all-course coverage, schema/citations, worker/API and deterministic calculations preserved |
| Other checks | Ruff lint/format, dependency integrity, existing Alembic head/SQL/migration checks and Git whitespace/credential review recorded in STATUS.md |

The PostgreSQL test's fictional programme deliberately simulates the non-synthetic query lane **only inside an isolated automated-test schema**, as existing retrieval fixtures do. It is not a real university record or a live-source/model acceptance result. The live driver's separate copy path retains the original real observation IDs/hash/date while labelling both course and association synthetic. Neither approach creates academic accuracy metrics.

The baseline is **770 → 788** passing tests, **13 → 14** PostgreSQL cases. One existing Starlette/httpx deprecation warning remains. A new fixture-import setup error was corrected before the final complete pass. Mocked tests do not close the live source-admission gate.

## Publication and workspace boundaries

The tested implementation, 18 additional regressions and reviewed documentation were published on **25 October 2026** to **`codex/replit-managed-ai`** as **[ef2b9a83db6533dc3130951895f486a0d8aba79c](https://github.com/RikoHalim/NORDYC/commit/ef2b9a83db6533dc3130951895f486a0d8aba79c)**. The remote SHA was verified. The staged 15-file review passed whitespace, credential-pattern and private-path checks; **71** local Markdown links resolved. Credentials, original files, raw reports, database files and audit receipts were excluded. This documentation-only follow-up records the implementation publication without implying that live source admission succeeded.

The root Windows Gemini checkout was untouched. GitHub main remained **`cb299325dff989a4922aefaac317cb89c0dc1193`**, Gemini remained **`a07d039ad38712fb5b5ce953077c0e279349a877`**. Reviewed public source/docs were copied to the correct Replit development checkout only after matching baseline or reviewed-content hashes, allowing Windows line endings, with backups before writing. Native Replit checkpoint history was not reset, merged or pushed over GitHub. No public deployment occurred.

## Reproduce safely and remaining gates

```bash
.venv/bin/python scripts/verify_phase43.py preflight
# STOP: explicit new approval and budget are required before another live case.
.venv/bin/python scripts/verify_phase43.py live --approved-budget-usd 0.05
```

Do not run the live command again on this existing case. `data/local/phase43-verification/live-attempt.json` is exclusively reserved before work and prevents reruns even after a failed/partial result. Preserve it; never delete it to bypass the bound. PostgreSQL setup uses only the marked loopback cluster from Phase 4.2, never ambient/shared/production `DATABASE_URL`. Reports, source bodies, tokens, database files and raw search content are excluded from publication.

Persistent research and external AI processing remain false; Gemini remains disabled; Claude Opus 5 remains the selected MVP model. Replit remains hosting. The isolated PostgreSQL server was stopped after checks; its database, audit and one-attempt receipt remain retained under ignored `data/local`. No public deployment or database transfer is implied by Git publication. Normal app startup still needs its own valid development PostgreSQL configuration as documented in Phase 4.2.

**Remaining acceptance gates:** an actual returned candidate needs exact source registration/permission review, and an acceptable original must be retrieved or independently authenticated through the permitted manual-original workflow, then persisted and rechecked by analysis. No further paid attempt is authorised by this report. Phase 4.3 is **PARTIAL**, not complete. Phase 5 planning can account for this gap, but do not treat live research evidence as available or start Phase 5 implementation automatically.
