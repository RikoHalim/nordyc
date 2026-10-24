# Phase 6 — Academic Pathways, Scenarios and Action Plans

## Implementation boundary

Branch **`feature/phase6-academic-pathways`** starts from published Phase 5 receipt **`91a24e91401f20fc173f92c01e5042e51417271d`**. It extends the existing services, repositories, PostgreSQL schema, worker and protected FastAPI routes. Main, Gemini, Claude/Brave, Phase 5 and the original Replit checkout are preserved. Replit-managed **`claude-opus-5`** remains the only enabled-model option for this phase; Gemini stays disabled. Replit remains the future hosting platform. No deployment, frontend, student profiles or Phase 7 implementation is included.

This is an institutional proposal engine for human academic review, not an individual reskilling service, certified curriculum evaluation or learning-outcome assessment. All activities and objectives are proposals. Attendance, enrolment, seminars, resource completion and documented intent do not establish demonstrated competence. The organiser's acceptance of institutional substitutes for individual matching/pathways remains **UNCONFIRMED**.

## Exact lineage and consideration

The engine reads a completed Phase 5 `CareerRun`, validates its canonical result and source access, then selects exact persisted `CareerRecommendation` IDs, content hashes and programme revision. Each plan preserves the parent career result, occupation/requirement matrix, reviewed curriculum coverage, minimum sufficient interventions, alternatives and no-change decisions. It never infers content from a course title or changes deterministic workforce calculations.

The latest exact-version Phase 5 operator review must be `under_review` or `approved` before a substantive conditional pathway can be considered. `needs_evidence`, rejection and unresolved coverage yield evidence-review steps; `no_change`/`no_change_required` preserve the decision without fabricated training. No algorithm creates an academic approval. The existing shared token identifies an authenticated operator, not a named academic committee member or institution tenant. A plan-level review is append-only and bound to the exact final plan fingerprint.

## Pathway method

Pathways are deterministic proposals linked to their exact recommendation and skill, with occupation IDs, evidence, prerequisites, alternatives and a no-change option. Eligible interventions use procedural stages: inspect the existing recommendation and curriculum evidence; verify the supported need; consider proposed practice and assessment design; refer the plan for academic review. Practice and assessment design can be partially ordered. This order is a review workflow, not a claim that one subject is an academic prerequisite for another.

Subject prerequisites require an explicit reviewed binding, an exact admitted quotation and a persisted resource statement relating the target and prerequisite skills. The dependency graph rejects cycles, missing or self-dependencies and invalid sequence positions. Unknown prerequisites remain unknown. Neither a benchmark nor a resource description proves that a university teaches the competency.

Priority reuses Phase 5 evidence sufficiency and review status. There is no invented financial return, implementation deadline, staff capacity, admission requirement, graduate readiness score or employment probability. Resources and review evidence can be absent without the engine inventing replacements.

## Resource and duration admission

Resources reuse `EvidenceReference`, `DatasetVersion`, `Dataset` and `Source`; no second resource catalogue or skill taxonomy is introduced. An explicit reviewed resource-to-skill binding selects typed original-source metadata stored under `EvidenceReference.metadata_json.learning_resource`. Source/version/reference identity, review state, cutoff, safe original URL, withdrawal and separate internal/output/model permissions are checked. A real original benchmark can support a fictional demonstration while retaining its real source flag. Synthetic resources cannot substantiate a real programme.

Resource output contains title, original URL, publisher, type, dated verification, publication date, access status, known price/currency or unknown, licence limits and exact citations. Open access does not mean free. Known costs need a dated original-source check; inconsistent free/paid/unknown amounts are rejected. Offline fixtures explicitly describe fictional resources at `example.invalid`; they are not advertisements or verified real availability. No live resource acquisition or robots check is bypassed: only already admitted, reviewed sources are read.

Each step's effort estimate is either an exact original-source duration/component or a reviewed **planning assumption** with an explicit basis and review date. Unsupported estimates remain null. Learning/contact/assessment components stay identified, reused provider components cannot be double counted, and any unknown step prevents a complete pathway total. The known subtotal is reported separately. Effort hours do not guarantee calendar completion, student mastery or implementation feasibility.

## Two hypothetical scenarios

Both scenarios use the same frozen recommendations, revision, observations and comparison dimensions:

| Scenario | Explicit planning assumption |
|---|---|
| Gradual workforce transformation | Prioritise incremental coverage and staged review |
| Accelerated AI adoption | Prioritise assessment review when exact admitted observed-task evidence supports it |

Assumptions, rationale, optional planning horizon, supporting/contradicting citations and uncertainty are stored separately from observations. The comparison dimensions are competency coverage, evidence sufficiency, assessment review priority, academic dependencies, and minimum intervention/no change. Escalation requires properly scoped observed AI-task evidence; exposure alone does not establish replacement, and occupation counts do not measure skill demand. Contradictions prevent escalation. Neither scenario predicts probabilities, adoption rates, wages, job losses or placements.

The comparison reports changed/unchanged priority bands and procedural no-regret review/no-change decisions. Source age is checked at the new plan cutoff without changing the frozen parent findings. The default synthetic fixture has distinct assumptions but no supported task evidence requiring a priority change, so unchanged actions are expected. A separate labelled synthetic observed-task case verifies conditional priority changes, unrelated-competency stability and abstention when the observation ages past the permitted window. A changed action is never forced to make the comparison look useful.

## Reviewed SDG contributions

The existing **186 official UN references** are reused, with original A/RES/70/1 text, goal/target IDs, parent-goal linkage, source dates and provenance. The reviewed local UN pack validates identifiers and text; no goal/target table or new taxonomy is created. Target and parent-goal references are separately admitted and frozen, so withdrawing either reference invalidates dependent plans. These dated normative standards are not relabelled as recent workforce observations or synthetic university facts.

Mappings require explicit review, an eligible recommendation, exact recommendation citations, a specific mechanism and a matching official target. The initial narrow mechanism rules support assessed competency access → 4.4; inclusive learning access → 4.3/4.5; research/innovation → 9.5; resource-efficient practice → 12.2. These are explicit engineering eligibility rules, not proof of causal impact. Unsupported or absent mappings stay `insufficient_evidence`/`unmapped`; SDG 4/8 are not added automatically. A possible contribution is a reviewed inference and **never measured or achieved SDG impact**.

## Structured Academic Action Plan

`PlanResult` supplies eight conceptual sections:

| Section | Fields |
|---|---|
| A — Programme overview | `overview`, exact course inventory/revision, coverage and limitations |
| B — Career alignment | Frozen `career.occupations`, workforce/AI context |
| C — Competency coverage | Frozen `career.competencies`, known/partial/gap/unknown findings |
| D — Academic recommendations | Version-bound `recommendations`, alternatives, no change and review receipts |
| E — Academic pathways | `pathways`, proposed steps, prerequisites, `resources`, effort bases |
| F — Future scenarios | Two `scenarios` and consistent `comparison` |
| G — SDG alignment | Reviewed `sdg_alignments`, official targets and uncertainty |
| H — Academic review | `review`, append-only external review history, dependencies and next evidence |

Optional `phase4_analysis_id` links a completed, permitted analysis of the same programme revision and retains a safe summary/status context; absent Phase 4 detail is explicitly reported, never synthesized. The exact Phase 5 career findings remain authoritative. Typed JSON supports a future report/dashboard; PDF export and React are deferred.

`previous_plan_id` optionally compares a new explicit run against a completed immutable plan of the same programme. Dependency fingerprints identify affected/unchanged recommendation/pathway links without overwriting history. This is operator-requested version comparison, not automatic evidence monitoring or automatic curriculum refresh.

## Persistence and asynchronous API

Additive migration **`0007_academic_action_plans`**, after `0006_career_alignment`, adds only:

| Table | Contract |
|---|---|
| `action_plan_runs` | Exact career/revision/job lineage, frozen input/manifest/result, method/schema/model usage and fingerprint |
| `plan_recommendations` | Composite FK to the exact parent recommendation ID/run/revision/content version |
| `action_plan_reviews` | Append-only operator decision for exact plan/revision/fingerprint |

PostgreSQL guards prevent mutation/deletion of published history; downgrade refuses populated history. Institutions and existing job `ACTION_PLAN` processing are locked using the existing worker. Source/review signatures are frozen at submission and revalidated after expensive processing, before atomic persistence; stale attempts cannot overwrite another worker. Source withdrawal or changed parent review history flags and withholds source-derived JSON, excerpts and model choices. Review creation then fails closed until a new valid version is generated. Public metadata retains operational scalars only.

All routes below require the existing configured `X-Analysis-Token`; they do not provide production tenant isolation:

| Method | Route (under `/api/v1`) |
|---|---|
| POST / GET | `/career-analyses/{career_run_id}/action-plans` — queue/idempotent replay and history |
| GET | `/action-plans/{id}` — persisted job/result/lineage |
| GET | `/action-plans/{id}/pathways` |
| GET | `/action-plans/{id}/pathways/{key}/steps` |
| GET | `/action-plans/{id}/resources` |
| GET | `/action-plans/{id}/scenarios` |
| GET | `/action-plans/{id}/comparison` |
| GET | `/action-plans/{id}/sdg` |
| GET | `/action-plans/{id}/evidence` |
| POST / GET | `/action-plans/{id}/reviews` — exact fingerprint required on writes |

Submission body is `PlanRequest`: offline/live mode, optional idempotency key/cutoff, selected recommendation IDs, optional Phase 4/previous-plan IDs, reviewed resource/duration/prerequisite/SDG bindings and scenario assumptions. Lists, text and processing are bounded. Empty selected IDs mean all exact parent recommendations. The API returns a durable job immediately; run the existing separate `python -m shiftos.cli worker --once` process to execute it. Check CLI help for the continuous worker option and existing infrastructure runbook. No new queue service is required.

## Optional Claude and Brave boundaries

Offline mode invokes no model. Explicit live mode still requires the existing managed Anthropic configuration, provider enablement, all source model permissions and separately approved external processing. Persistent settings were not changed. `services/pathways/reasoning.py` permits one bounded Claude choice of an admitted scenario and fixed review question per supplied pathway, with exact citations. It cannot modify canonical paths, durations, SDG mappings, findings or approval. The wrapper uses at most one attempt, 60 seconds, 4,096 output tokens and 49,152 request bytes, with any smaller configured limit prevailing. Invalid JSON, fabricated citations, identity mismatch or provider errors preserve deterministic proposals and an explicit unavailable-review result; there is no repair or Gemini fallback.

All Phase 6 model tests are **mocked**. Actual Phase 6 live requests: **0**. Actual Phase 6 token usage/latency/billing: **not observed**, not inferred from mocks or historical Phase 4.2. No new expenditure was incurred by a live request in this work. Brave remains independent: historical transport passed, but Phase 4.3 original-source admission remains **PARTIAL**. This extension neither invokes Brave nor admits snippets/model-generated references. Further paid verification needs new consent and a bounded budget.

## Verification record

The baseline is **877 tests including 16 PostgreSQL cases**. Verification uses a separate owned loopback PostgreSQL 16 cluster and isolated per-test schemas, never Replit/shared production data. Existing migrations are applied and metadata drift checked. Local database files, raw reports, receipts and generated outputs remain ignored under `data/local`.

The labelled fixture [academic_pathways.synthetic.json](../examples/academic_pathways.synthetic.json), with `tests/pathways_helpers.py`, builds a real Phase 5 parent through the existing API/worker, explicit fictional review receipts, fictional resources, and the genuine 186-record UN benchmark pack. Acceptance exercises four fictional courses/three occupations, five exact recommendations, four pathways (three conditional intervention proposals and one evidence-review pathway), preserved no change, two fictional resources, a three-hour source-based practice subtotal with other durations unknown, two scenarios, two reviewed 4.4 contributions, alternatives and exact source/version pointers. A separate positive offline workflow links an actual Phase 4 worker result and compares a new plan: one changed workload assumption affects one pathway while the other pathways and the original plan remain unchanged. PostgreSQL tests retrieve committed results through an independent connection and protected FastAPI, and cover FK/history/rollback/withdrawal guards.

Final measured suite, quality checks and publication receipt are recorded in [STATUS.md](../STATUS.md). Software acceptance does not establish real programme accuracy, resource availability, academic approval, individual mastery or employment outcomes. Current real-data gaps, Phase 4.3 admission and organiser/security gates remain visible. Phase 7 planning can follow owner review; implementation is outside this authorization.


## Final checks and reproduction

Final measured result: **974 passed**, including **18 real PostgreSQL tests**, **0 failures/errors/skips**, **118.87 seconds**; **97 Phase 6 tests** above the 877-test baseline. Ruff lint/format, dependency integrity, Alembic upgrade/check/one-head/offline SQL and staged whitespace checks pass. One pre-existing Starlette/httpx deprecation warning remains. The only schema head is `0007_academic_action_plans`. Publication and final remote receipt are recorded in STATUS.

From an installed development checkout, configure `DATABASE_URL` and `TEST_DATABASE_URL` explicitly to an owned disposable PostgreSQL database, not a production/shared database. Apply existing migrations and run:

```powershell
python -m alembic upgrade head
python -m pytest -q
python -m ruff check src tests alembic scripts
python -m ruff format --check src tests alembic scripts
python -m pip check
python -m alembic check
python -m alembic heads
python -m alembic upgrade head --sql
```

The pytest integration fixture creates isolated schemas and verifies PostgreSQL rather than treating SQLite unit tests as migration acceptance. `tests/test_pathways_postgres.py` exercises the positive committed plan; `tests/test_pathways_reassessment.py` demonstrates actual offline Phase 4 linkage and selective immutable plan comparison. No live credentials are needed. Production setup, secure named-reviewer/tenant authorisation and public Replit deployment are later work.

## Publication receipt

The tested 37-file implementation was committed and pushed as [b711999d6c23023591eec590963ca8ee174ec703](https://github.com/RikoHalim/NORDYC/commit/b711999d6c23023591eec590963ca8ee174ec703) to **`feature/phase6-academic-pathways`**; the exact GitHub remote SHA was verified. All 110 checked local Markdown links resolved; staged credential-pattern, private-path and whitespace checks passed. This documentation-only receipt records that result. Main, Gemini, Claude/Brave and Phase 5 remote SHAs remained unchanged; the original checkouts and Replit project were preserved. The owned PostgreSQL test server was stopped and ignored verification files retained. No force-push, merge, paid request, frontend or deployment occurred.
