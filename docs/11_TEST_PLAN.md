# Test and acceptance plan

## Phase gates

1. **Foundation:** application starts; migrations up/down on a clean test DB; CRUD on institution -> multiple programmes -> multiple courses; nullable year/elective; documented errors; no API key required.
2. **Discovery:** official-like HTML fixtures representing several disciplines; year parsing; link provenance; missing semester remains null; parser failure visible; idempotent re-import; timeouts and rate limits mocked.
3. **Evidence pipeline:** source dates and provenance persisted; multiple dated snapshots; source claims and unit types checked; occupation-level metric not cast as skill statistic; deterministic offline fixture import.
4. **Relevance:** whole-programme returns **all available course appearances** even if insufficient evidence; PostgreSQL retrieval precedes controlled research on important gaps; original claims and permitted cache/version lineage are verified; one configured LLM is grounded and validated; title-only never yields definitive obsolete/update verdict; no reliable evidence -> `insufficient_evidence`; standard != teaching evidence; trends remain deterministic. See the Phase 4 matrix below.
5. **Actions:** valid primary recommendation and alternatives incl `no_change`; high-evidence gate for redesign; missing data yields review not invented action; attendance alone cannot increase assessed skill coverage.
6. **Scenario/report:** two scenario results; date-stamped evidence replay changes only affected results; SDG reasoning not empty; reports distinguish verified and provisional outcomes.
7. **Hardening:** duplicate prevention, cross-programme isolation, input validation, SQL injection mitigation, request logging free of secrets, offline deterministic run, end-to-end fresh setup reproducibility.
8. **UI:** select XMUM -> see all programmes -> run full-programme analysis -> navigate to course evidence -> compare AI-suggested action vs no change -> run scenario -> report. Show meaningful empty/unknown states.

## Critical negative tests

- Input official course title only -> **no claim of actual taught topics**.
- Unverified publisher/URL -> **cannot cite as verified campus fact**.
- Changing irrelevant labour signal -> **should not alter unrelated major findings**.
- Source removed/invalid -> system flags inadequate evidence instead of hallucinated citation.
- Synthetic snapshot -> UI and API label it as synthetic.
- If LLM returns unknown JSON or fabricated URL -> reject/correct by grounding validator.
- Same document imported twice -> zero duplicate courses/sources (unless legitimate different years/tracks).

## Phase 4 hybrid retrieval tests (planned)

The authorized Phase 4 implementation now supplies pytest coverage for these boundaries; actual results/limits are in STATUS and the [runbook](21_PHASE4_COURSE_RELEVANCE.md). The original planning revision alone did not run these tests. Use labelled synthetic fixtures/mocked providers and separate genuine-data checks; do not equate them with live Gemini/Brave acceptance. Preserve Phase 1–3 regressions and PostgreSQL migration/history coverage.

| Area | Required cases and expected outcome |
|---|---|
| Internal retrieval and coverage | Every course appearance returned, including ambiguous/title-only/missing inputs; select exact evidence versions and correct discipline/qualification/geography. Sufficient local evidence makes **zero external calls**. An unrelated discipline's evidence does not change the finding. |
| Sufficiency and freshness | Missing, outdated, conflicting, corrected/retracted and unknown-date evidence trigger a recorded gap for time-sensitive claims. Retrieval time cannot refresh publication age. Legacy/multilingual taxonomy and narrow standards retain limits; no guessed translation/crosswalk. Historical claims remain eligible under their dated scope. Policy/cutoff decisions are frozen for replay. |
| Review-state compatibility | Structured official `needs_review` values retain provisional source-attributed status and exact parser/version scope; raw PDF `needs_review` pages cannot become factual findings. Engineering-reviewed cards do not become academic approval. AI transformation retains stricter reviewed task/identity gates. |
| Automatic fallback | An important gap invokes only the configured approved search adapter within budgets; verified imports are re-retrieved internally. Cache hits avoid repeated searches. Missing credentials, disabled research, timeouts, quota/refusal, partial results and budget exhaustion preserve courses and explicit insufficiency reasons without silent provider/synthetic substitution. |
| Original-source verification | Search snippets, aggregator summaries, nonexistent URLs and model memory cannot satisfy a claim. Verify publisher/title, actual passage/table, locator, dates/precision, units/population, edition, limitations and original/derived hashes. A genuine source with an unsupported quote/claim fails. Ambiguous PDF tables/scans stay candidates; material disagreements/corrections remain visible. |
| Access and security | Reject unapproved hosts, private DNS/IPs, credential-bearing URLs, redirect escapes, oversized/corrupt documents and archive expansion. Respect robots/terms, paywalls/login/CAPTCHA and 429/Retry-After within finite retries/deadline. Model/document prompt injection cannot change tools, host policy, secrets, scope or budgets. |
| Rights and privacy | Separate original retention, excerpt/output reuse and external-model processing permissions. Unknown/prohibited use yields bibliographic metadata/manual guidance or insufficiency, without retained restricted text. No private uploads, personal identifiers or credentials in search queries/logs; no unauthorized private-document egress. Analysis submission/results enforce access boundaries and expose no arbitrary-URL research trigger. |
| Persistence, cache and lineage | Permitted verified findings survive import/query with source/version/reference links and complete provenance. Unchanged imports/retries/concurrent jobs remain idempotent; changed bytes/parser/context preserve earlier versions. Cache hits retain the original retrieval date. Cache keys/admission include query scope, provider, freshness, source/rights/review policies; negative entries expire. Rights withdrawal/corrections invalidate future admission and flag affected prior findings. |
| Run reproducibility and workers | Freeze curriculum revision, evidence manifest, gaps, attempts, policy/cutoff, radar inputs/thresholds and model/prompt/schema versions. Replay performs no research; refresh creates a new run and affects only linked findings. Worker retries/interruption/cancellation cannot overwrite terminal results or duplicate facts. Expensive work remains outside HTTP handlers; errors use the existing sanitized envelope. |
| Single-model grounding | One adapter/model only; missing configuration or provider failure is explicit. Validate both draft JSON and final serialized findings: course IDs, permitted references, quotes, claim class/scope, dates, uncertainty and insufficiency. Reject invented citations, extra fields and valid-looking JSON with unsupported content. Bounded repair cannot add evidence or a second model. Offline deterministic output stays visibly synthetic. |
| Academic safeguards | Title-only benchmarks require syllabus confirmation; uploaded unverified content cannot be called a verified syllabus. Standards do not prove teaching. Broad occupation-group advertising is not individual-role/skill demand; two observations are not a sustained trend. Decline, exposure, forecasts and observed capability stay distinct and cannot imply automatic obsolescence, replacement or AI causation. Radar mathematics/thresholds remain unchanged. |

Add PostgreSQL persistence/API/migration tests for any actual Phase 4 schema or endpoint change. A completed run and course drill-down must expose coverage, research outcomes, provenance, limitations and explicit insufficient-evidence results. Test protected asynchronous submission/idempotency and unauthorized reads/writes according to the selected MVP deployment access policy.

Separately perform an **opt-in real-data smoke test** with an approved search provider and the single configured model, permitted original sources and a bounded programme subset. Demonstrate internal retrieval, a real gap → search → original-source check → permitted import/query → cited finding, repeat/cache reuse and one honest blocked/insufficient outcome. Record actual provider/model, source dates/versions, imported counts, citations, request outcomes and unresolved gaps. Missing credentials or permissions block that live gate; mocked tests cannot pass it. Avoid any accuracy or cross-discipline completeness claim from this smoke test alone.

## Evaluation: don't claim model accuracy without a labelled benchmark

### Planned Phase 5–6 enhancement tests

These requirements are documentation only; no alignment/pathway functionality is implemented. Phase 5 must test requirement-to-curriculum support across disciplines, reviewed mappings, title-only unknowns, possible-versus-confirmed gaps, optional deterministic score denominators/weights/missingness, minimum sufficient primary intervention, alternatives/no change and human review. Alignment must never become individual employment probability.

Phase 6 must test ordered/acyclic prerequisites, proposed-versus-existing objectives, unknown duration without a basis, original-source resource suitability/access/cost verification, no fabricated partnerships, meaningful goal/target rationale, and assessed practical work versus attendance-only awareness. Scenario assumptions must not overwrite observations; changed evidence affects linked findings/steps only and no forced action flip is required. Reports retain evidence, limitations, resource/duration dates and approval status. Domain 1 institutional substitutions remain UNCONFIRMED; any individual contingency needs separate authorization, labelled fixtures and no real student tracking.

Compare output on a hand-reviewed set of public/synthetic cases from at least 3 disciplines; report agreement rates, citation accuracy, abstention on missing data, false-confidence examples and limitations. Avoid arbitrary thresholds disguised as independently validated performance.

## Demo reproducibility

No live external API calls required for baseline demo. One command sequence starts DB, applies migrations, seeds **synthetic** fixtures and runs tests, documented in README after implementation. Optional live source can be switched on to demonstrate genuine dated refresh.
