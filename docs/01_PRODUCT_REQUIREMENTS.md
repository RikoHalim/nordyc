# Product requirements and scope

## User / decision

Institution-facing application for university career centres, working with programme directors, quality-assurance units and academic committees. Main decision: **Which courses within our programmes warrant review in response to AI and workforce changes, and what is the least disruptive justified academic response?** AI informs; authorised academics decide. Do not imply career centres approve syllabus changes alone.

## Primary user journey

1. Select an institution/programme, beginning with XMUM in Malaysia.
2. Upload available university curriculum/brochure or syllabus documents. Detailed syllabi are optional. Public website discovery is a secondary way to acquire programme/course lists.
3. See every extracted course and explicit year/elective information; review ambiguous PDF candidates and correct missing data with provenance. Scans/unsupported layouts use explicit extraction regions or reviewed structured import.
4. Run programme-wide benchmarking against relevant accreditation/discipline standards, occupational skills, dated AI developments and Malaysian workforce evidence.
5. See an **evidence coverage overview** first: verified catalogue, description-only, title-only, unavailable syllabus, matched disciplines, affected roles.
6. View a course review priority list: verified continuing relevance, potential review needed, insufficient evidence. Drill into course details with precise citations and uncertainty.
7. Review AI-recommended academic actions and compare with alternatives, including `no_change`: syllabus revision, course redesign/consolidation (high evidence bar), new course/elective, workshops & industry engagement.
8. Compare moderate vs accelerated AI developments, optionally input budget/time at **intervention feasibility** step (never in onboarding).
9. Export an academic action proposal **for review**, with human approval workflow/status and source bibliography.

## Scope guardrails

- **All publicly discoverable XMUM undergraduate programmes in the catalogue**, deep engine evaluation on a small **cross-disciplinary validation subset** during early MVP. Do not claim complete deep analysis until source support exists.
- Multi-institution architecture; **discover on demand** elsewhere in Malaysia. Never preharvest entire Malaysia.
- Missing detailed course outcomes => `unknown`; cannot pronounce course obsolete or verified fully current.
- Source freshness and evidence classes visible. No fabricated scores, job forecasts, assessment outcomes, partnerships.
- No full course-content authoring, chat assistant, student tracking, hiring workflows, workshop booking, payment, bespoke model training or giant live spider in MVP.

## Desired outputs

- University/discipline/programme coverage report, not a leaderboard of real colleges.
- Programme-level skill/topic areas to investigate, not fictional competency gaps.
- Per-course evidence trail and review flags.
- One defensible primary action recommendation, legitimate alternatives, relative academic disruption + feasibility assumptions; compare against **no change**.
- Scenario sensitivity and dated source re-evaluation.
- Observed `RISING`, `DECLINING`, `STABLE` or `INSUFFICIENT_DATA` indicators, with `AI-TRANSFORMING` as a separate task-evidence attribute. Broad group statistics never become individual occupational trends; two quarters show only short-term change.
- SDG rationale with evidence where genuinely appropriate.

## No false certainty

For title-only courses: recommend **review the coverage of X in the syllabus**, or **monitor the topic**, never `remove course because AI can do it`. Any provisional academic action is labeled `conditional`; final recommendation needs deeper evidence/validation.
