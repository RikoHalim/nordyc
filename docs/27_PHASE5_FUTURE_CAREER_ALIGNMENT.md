# Phase 5 — Future Career Alignment and Academic Recommendations

**25 October 2026 — COMPLETE for bounded backend implementation and synthetic/software acceptance.** Development is isolated to `feature/phase5-career-alignment`, based on the verified published Claude/Brave commit `b8b5e3ae315f656390eae3d0a45256c4884e450c`. This extends the [Phase 5 plan](22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md), without implementing Phase 6, frontend, deployment or a learner-profile module. Replit-managed `claude-opus-5` remains the only selected MVP model. Gemini remains disabled. Replit remains hosting. No new live provider or real academic-accuracy acceptance is claimed.

## Evidence methodology

The engine reads the selected programme revision and every course from PostgreSQL. The request supplies bounded, explicitly reviewed programme-to-occupation mappings and passage-to-skill assertions. These are recorded operator interpretations with reviewer reference, date, rationale and Malaysian applicability; they are not automatically inferred crosswalks or independently certified academic approvals. A name or title match cannot establish occupational identity, skill coverage or Malaysian demand.

Occupation identifiers, taxonomy and external IDs must agree with existing records. Requirements come only from persisted same-version `OccupationSkill` relationships and their linked skill and source records. Essential versus optional requirements remain explicit. The service does not duplicate the occupational taxonomy or invent requirements for familiar role names. No mapping or eligible requirements yields `insufficient_evidence` and review guidance.

Admission retains source/version/reference identity, original URL, hash, locator, dates, review state, synthetic lane and explicit permissions. Rejected, withdrawn, inconsistent, future or disallowed material cannot support a finding. Legacy edition, language, geographic, observation-period and classification limits remain visible. A recently downloaded old taxonomy is still old. International benchmarks do not establish Malaysian vacancies or skill demand.

Currentness screening requires a known publication day and uses conservative engineering ceilings: **1,825 days** for occupational benchmarks, **550 days** for workforce publication/observation periods and **730 days** for AI evidence. Real curriculum currentness additionally needs its revision effective date within **1,825 days**. Unknown/imprecise dates remain context; these defaults are not publisher-certified validity windows or statistically calibrated confidence. All tests preserve the stored source dates rather than refreshing old facts by downloading them again.

Curriculum assertions identify an exact course, skill and reviewed document anchor, with a quote present in that anchor. A document must belong to the selected revision and course. `content_reviewed=true` is an explicit operator assertion. Assessment demonstration additionally requires `demonstration_reviewed=true` and the bounded reviewed passage; a syllabus objective alone cannot establish demonstrated attainment. Current real packs contain no student assessment outcomes. The fictional fixture labels its demonstration separately and establishes no real graduate competence.

| Coverage evidence | Requirement result |
|---|---|
| Reviewed full bounded demonstration | `supported`, with the assessment/synthetic scope retained |
| Documented intended coverage or partial demonstration | `partial`; intent stays distinct from attainment |
| Possible title/metadata association, missing or rejected support | `unknown`; request syllabus/assessment confirmation |
| Reviewed explicit programme-wide deficiency audit | `documented_gap` only with exact negative passage, complete course scope and explicit reviewer confirmation |

The last case requires a programme-level document, `gap_reviewed=true`, the exact skill in `negative_skill_ids`, and all selected-revision course IDs in the request's covered scope. Missing evidence never becomes absence. Conflicting positive and negative evidence requires investigation. Electives cannot establish universal compulsory coverage. All courses remain accounted for, including those with no syllabus.

Workforce calculations reuse the existing deterministic methodology. Only compatible occupation-level observations can describe that occupation's indicator; broad sectors/groups, stale periods and unresolved classification bridges remain context or unknown. AI evidence is independent: exposure is not observed capability or displacement probability. No falling advertisement count or AI exposure automatically removes a course.

## Calculation, ranking and actions

The versioned method is `phase5-requirement-coverage-1`. The optional measure uses an explicitly complete reviewed essential-requirement set, equal engineering weights of 1 per essential requirement, a demonstrated-support numerator and an essential-requirement denominator. Optional requirements remain visible separately and do not enter this essential-only denominator. It reports assessed and unknown essential counts separately. Unknown or partial essential coverage, stale/inapplicable sources or incomplete requirements cause abstention rather than a fabricated zero or a favourable reduced denominator. An explicit reviewed deficiency may contribute a known zero; a missing syllabus cannot. Engineering weights are not scientifically validated; the measure is not employment probability. Candidates without comparable requirement/evidence sets remain unranked. Positive synthetic support does not justify ranking unrelated occupations.

Recommendations are deterministic, evidence-bound proposals: inspect an outcome, review/introduce appropriate assessment or an existing exercise before proposing a larger intervention. Every recommendation has a minimum sufficient action, rationale, target competency, affected courses or programme area, an alternative, no-change option, objective, priority basis, conditions, limitations and required academic review. Missing cost, resources, staff availability, duration, effectiveness and approval remain unknown. A no-change/monitor or request-review outcome is valid. Phase 6 ordered pathways, verified resources, durations, SDGs and scenarios are excluded.

Optional Claude processing compares only already eligible options. Its strict schema permits provided recommendation keys/options, finite reason codes/review questions and exact admitted citations. The backend rejects invented options, facts, quotes, identities or extra fields. It cannot alter requirements, coverage, scores, deterministic minimum actions or approval. The unchanged Phase 4 provider default prompt is preserved; an explicit Phase 5 task instruction uses the same managed Messages transport and generic evidence-safety instruction.

`mode=offline` makes no model/search request. `mode=live` still requires the existing enabled managed integration, process-authorised external-processing consent and source-specific external permissions. A source denied external processing blocks model comparison. One attempt, no repair/fallback, at most 60 seconds, 4,096 output tokens and 49,152 request bytes are imposed; smaller configured limits win. No live Phase 5 Claude or Brave request is authorised or performed by this implementation. Model failure leaves the deterministic proposals with explicit limitations.

## Persistence and human review

Additive migration `0006_career_alignment` adds only `career_runs`, `career_recommendations` and `career_reviews`. Existing occupations, sources, curriculum revisions and jobs are reused. Composite foreign keys bind recommendations and append-only review decisions to their exact run, revision and recommendation hash. Completed runs and recommendations/reviews are protected against alteration through ORM checks and PostgreSQL triggers. Populated downgrade refuses data loss.

Submission freezes the inventory, resolved revision, cutoff and request. The existing worker claims `CAREER_ANALYSIS` jobs, validates outputs and commits the run, recommendations and completion atomically. Idempotency replays the same job/request; changed content conflicts. Running-job locks and inventory checks fence stale workers. Source/policy signatures are rechecked around model processing and on disclosure/review. Stale or restricted results retain history but withhold source-derived text and cannot become current approvals.

All routes reuse `X-Analysis-Token`. Review actors are assigned by the server as `authenticated_analysis_operator`; clients cannot impersonate named reviewers. States include `proposed`/`needs_evidence` on proposals and append-only decisions `under_review`, `needs_evidence`, `approved`, `rejected`, `no_change_required`. An approval is an authenticated operator's recorded decision, never automatic university curriculum approval. This single-operator token does not implement personal academic identity, institutional role management or multi-tenant authorisation; those remain later security work.

## API and reproduction

All paths below are under `/api/v1` and protected:

| Method | Path | Purpose |
|---|---|---|
| POST | `/programmes/{id}/career-analyses` | Queue `CareerRequest`, return 202 and job/run IDs |
| GET | `/programmes/{id}/career-analyses` | Versioned run history |
| GET | `/career-analyses/{id}` | Status, result, lineage, usage and revalidation flags |
| GET | `/career-analyses/{id}/occupations` | Occupation requirements, coverage and calculation limits |
| GET | `/career-analyses/{id}/competencies` | Requirement-level support/gap/unknown matrix |
| GET | `/career-analyses/{id}/recommendations` | Proposed actions, alternatives, no-change and version hashes |
| GET | `/career-analyses/{id}/evidence` | Permitted evidence references and provenance |
| POST / GET | `/career-recommendations/{id}/reviews` | Authorised version-bound decision / review history |

An initial title-only request may be `{"mode":"offline","idempotency_key":"review-1"}`. It produces honest insufficiency until reviewed mappings and actual passages are available. Use the typed OpenAPI contracts for `mappings`, `assertions` and `gaps`, rather than inventing UUIDs or source content. Process with the existing `python -m shiftos.cli worker --once`. HTTP requests never invoke Claude or Brave.

The labelled [synthetic scenario](../examples/career_alignment.synthetic.json) is exercised through `tests/career_helpers.py`, with three fictional occupations and four courses, reviewed intended/partial/demonstrated support, a complete explicit deficiency audit and an unknown requirement. The PostgreSQL test imports its labelled taxonomy through the existing evidence pipeline, then drives the real API and worker. The scenario is a test specification consumed by the helper, not the older Phase 1 fixture-import format.

The measured deterministic demonstration returns **7** occupation–requirement findings: **2 supported, 3 partial, 1 documented gap and 1 unknown**. The fictional Query Practitioner has **1/1** demonstrated essential requirements and a **100** measure under this narrow rule; Analyst **1/2** and Secure Data Steward **0/2** essential numerators both retain **null** measures because intent/unknown coverage prevents scoring. All three remain unranked. Five competency actions include retain/no-change, assessment review, outcome review for the explicit audit, and request evidence for the unknown. These are synthetic software results, not academic quality, measured learning gains or employment probabilities. Structural positive/abstention cases also cover reviewed accounting and biotechnology discipline scopes.

```powershell
python -m alembic upgrade head
python -m pytest -q tests/test_career_engine.py tests/test_career_reasoning.py tests/test_career_api.py
# Only after selecting an isolated non-production PostgreSQL TEST_DATABASE_URL:
python -m pytest -q
python -m ruff check src tests alembic scripts
python -m ruff format --check src tests alembic scripts
python -m pip check
python -m alembic check
```

## Verification, limits and next phase

The implementation, migration, fixture, **89** new tests and documentation were published to `feature/phase5-career-alignment` as **[db8850dde2671993cbbab936cb5b1e3c0bde23d0](https://github.com/RikoHalim/shift-os/commit/db8850dde2671993cbbab936cb5b1e3c0bde23d0)**; GitHub's remote SHA was verified. The 35-file staged review found no credential-pattern/private-path issue, whitespace checks passed, and **101** local Markdown links resolved. This documentation-only follow-up records publication. Main, Gemini and `codex/replit-managed-ai` retained their original SHAs; no merge, force-push or deployment occurred. Phase 5 files were not copied over Replit's existing Claude branch.

The final complete local suite passed **877 tests, zero failures/skips**, including **16 PostgreSQL integration cases**, in **113.14 seconds** on Python **3.13.13** and isolated loopback PostgreSQL **16.15**. This is **89** added cases over the **788-test / 14-PostgreSQL** baseline. Ruff lint/format, dependency integrity, real Alembic upgrade and schema-drift check, single head **`0006_career_alignment`** and offline SQL compilation passed. Historical migration tests now compare metadata at their selected revision and verify rollback to the previously upgraded head; their original data-preservation checks remain intact. One existing Starlette/httpx deprecation warning remains.

The PostgreSQL cases drive existing evidence ETL (15 fictional records, repeat unchanged), real worker, protected FastAPI, independent committed read, exact-version human reviews, composite foreign keys, direct-SQL immutability and populated downgrade refusal. Other tests cover three reviewed discipline scopes, title-only/unknown/elective abstention, wrong identities/quotes, explicit versus apparent gaps, stale/geographic/legacy/AI-exposure limits, canonical output/score/recommendation rejection, transactional rollback, late worker fencing and source/policy withdrawal. A review-discovered usage-metadata citation leak was fixed before publication and tested with a mocked comparison followed by withdrawal. No source safeguard was relaxed to pass a test.

All new Claude comparisons use mocks. **Zero** live Claude/Brave/Gemini requests were made; no real Phase 5 token/latency or billing measurement exists. Persistent consent/research settings were unchanged. The owned test PostgreSQL server was stopped after final checks and its data/audit receipts retained under ignored `data/local`. Raw reports and synthetic outputs are excluded from publication. These checks ran locally; they are not a new Replit deployment or Linux execution claim.

[Phase 4.2](25_PHASE42_LIVE_BACKEND_VERIFICATION.md) remains the historical accepted real Claude/worker/PostgreSQL/protected-API proof. [Phase 4.3](26_PHASE43_BRAVE_SEARCH_VERIFICATION.md) remains **PARTIAL**: Brave HTTP200 transport passed, while exact registration and original robots verification prevented new source admission. Phase 5 works with research disabled; it does not close that gate.

Real dataset coverage remains bounded: legacy ESCO subset/relationships, limited benchmark summaries, broad workforce populations, incomplete course descriptions and no independently calibrated academic evaluation. Missing reviewed programme mappings, syllabi or assessment evidence yields unknown coverage. This checkout contains the existing source registry and synthetic course fixtures, but no permitted original real-course passage inventory for a new Phase 5 real-curriculum test. The title-only tests are explicitly fictional; no XMUM records were fabricated to close this limitation. The synthetic demonstration does not validate real XMUM alignment or programme quality.

The organiser's acceptance of institutional programme-level matching in place of individual intake/matching/pathways remains **UNCONFIRMED**. No waiver is invented. A future individual questionnaire adapter may reuse these evidence contracts only after separate authorisation. Phase 6 readiness is a planning decision after reviewing these limitations; this phase does not implement or authorise it.
