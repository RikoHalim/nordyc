# Future Career Alignment and Academic Reskilling Pathways — planning revision

**Implementation update, 25 October 2026:** the separately authorised Phase 5 subset is now implemented on `feature/phase5-career-alignment`; [its runbook](27_PHASE5_FUTURE_CAREER_ALIGNMENT.md) reconciles exact mappings, typed passage assertions, source permissions, additive persistence, protected career resources and review history with this plan. The original planning text below remains historical scope guidance. Phase 6 pathways/resources/durations/SDGs/scenarios remain pending and unauthorised by Phase 5 completion.

**24 October 2026 — documentation only.** These requirements extend the existing Phase 5 Academic Decision Studio and Phase 6 scenarios/reporting plans. They do not add a separate product, student platform, runtime module, schema migration or endpoint. Ongoing Phase 4 development remains the current priority. Read [academic actions](07_ACADEMIC_ACTIONS.md), [scenarios/pathways](08_SCENARIOS_SDG_AND_REPORTING.md), [compliance](09_HACKATHON_COMPLIANCE.md) and [roadmap](12_MVP_ROADMAP.md).

## Phase 5: Future Career Alignment

Compare a programme's **source-supported documented competencies** with relevant published occupation/skill requirements. Begin with programme-level comparisons, supported occupations across disciplines and Malaysian applicability. Preserve IDs, taxonomy editions, occupation–skill relationships, dates, review basis and classification bridges. Candidate title/lexical matches remain hypotheses. Emerging occupations require genuine sources and definitions; an illustrative role name is not a registered occupation.

Reuse the Phase 3 deterministic `RISING`, `DECLINING`, `STABLE`, `INSUFFICIENT_DATA` observations and independent AI-task attribute. Explain the actual advertising/employment/vacancy measure, population and periods. Broad group counts do not measure an individual role or skill; two observations do not establish a sustained trend. Exposure and predictions do not establish observed task capability or course obsolescence.

Programme comparison must distinguish documented intended coverage, assessed demonstrations supported by actual evidence, and unknown coverage. Titles cannot establish any competency. A possible mismatch is a question to investigate until curriculum content/applicability is verified. No evidence of coverage is not proof of absence. Published standards and occupational requirements remain benchmarks, not XMUM teaching facts.

Alignment scores are **optional**, not a required MVP output. If later authorized, use a deterministic versioned method with explicit eligible requirement set, weights, denominator, coverage evidence and missingness. Unsupported/unknown coverage stays unknown, never zero by default. Explain sensitivity and partial coverage, and abstain when a meaningful score is impossible. Do not present engineering weights as scientifically validated or alignment as individual employment probability. Qualitative evidence confidence must retain source/review/identity/currentness limits; it is not an uncalibrated percentage.

Use the resulting alignment/gap evidence in the existing action comparison: primary evidence-supported recommendation, alternatives, `no_change`/monitor and `request_review`, with conditions and human academic approval. Choose the minimum sufficient justified intervention rather than automatically creating courses. A claimed confirmed gap or definitive content revision needs verified curriculum evidence; weak evidence supports investigation first.

## Phase 6: ordered Academic Reskilling Pathways

Extend existing Academic Action Plans and scenario/report results with ordered, evidence-linked learning steps. Each step needs target competency, proposed intervention, proposed objectives/activities, prerequisites where supported, estimated learning duration **and basis**, verified suitable resources, occupational requirement pointers, supporting evidence, meaningful SDG links and review status. Proposed learning objectives describe a future intervention, never existing university teaching.

Supported intervention categories include preserving arrangements, updating/redesigning a course, adding a justified course/elective, assessed practical workshops, industry-led seminars, guest speakers and career talks. A seminar/talk supports exposure or awareness; attendance cannot count as technical competency. Hands-on work may contribute a demonstrated competency only through an appropriate assessed result. Do not invent partners, bookings, learner outcomes or a student-tracking function.

Duration can use a cited resource's published time, a documented institutional plan or a clearly labelled reviewer/engineering estimate with its assumptions. Otherwise use null/unknown and a verification task. Do not invent fixed weeks, prerequisites, available electives, free/low-cost pricing or learning-resource URLs. Verify original resource suitability, access/cost observation date and reuse restrictions before recommending it. No full course content is generated.

Moderate/accelerated adoption scenarios reuse versioned historical evidence while keeping assumptions separate. Explain changed alignment priorities, intervention/pathway steps and the no-change alternative; unknown sensitivity is a valid result. A changed source should affect linked evidence/findings only. Reports consolidate curriculum coverage, career alignment, intervention comparisons, ordered steps, duration/resource bases, SDG reasoning, uncertainties and human decisions. Scenarios must not force an action flip or fabricate forecasts.

## Phase 4 output handoff and future contract changes

Phase 4 keeps its current scope. Its [implemented contracts](21_PHASE4_COURSE_RELEVANCE.md) supply all course IDs, five evidence-bounded dimensions, exact scoped citations, source/version/locator/date/rights metadata, candidate occupation/skill relationships, deterministic demand context and missing-evidence reasons. They support later interpretation; they do not already implement career matching or pathways.

| Future need | Current handoff | Required later contract extension |
|---|---|---|
| Curriculum-supported competency | Verified curriculum source quotations, if available; title-only otherwise | Typed competency assertion with source passage, course/revision, skill ID or explicit unmatched concept, mapping/reviewer basis, and `documented_intent` vs `assessed_demonstration` vs `unknown` |
| Related occupations/skills | Evidence packet preserves source record/version IDs and source-specific facts | Explicit reviewed programme↔occupation and competency↔skill mapping; taxonomy/edition and Malaysian relevance; candidate links remain separate |
| AI and workforce change | Scoped citations, limitations and deterministic radar context | Reuse exact source/observation/method pointers; keep observed capability, exposure, forecast and scenario assumption distinct |
| Potential gaps and confidence | Fixed review questions, insufficiency flags and unknowns | Requirement-level coverage state and rationale; qualitative evidence confidence with review/currentness basis; optional score only with method/weights/denominator |
| Future learning plan | No Phase 4 action or pathway output | Phase 5 primary/alternative/no-change comparison and review; Phase 6 ordered steps, prerequisite/duration/resource/SDG evidence and action-plan linkage |

These are proposed fields, not a claim that Phase 4 has inferred competencies from titles. Any later output-schema change must be additive, versioned, tested and grounded. Preserve original university fact versus benchmark/inference classes. Additional syllabus/assessment extraction must retain verified document passages and never fabricate learning outcomes.

## Planned persistence and API integration

Reuse institution/programme/revision, analysis runs/course findings, evidence sources/versions/references, occupations/skills and official SDG identifiers. Phase 5 may need normalized alignment/competency-support and action/comparison/review records. Phase 6 may need ordered pathway-step, prerequisite, duration-basis, verified-resource and justified SDG-link records. Every derived record must retain its originating run and evidence pointers. Concrete SQL design/migrations are deferred to those authorized phases; there is no universal replacement table or new standalone platform.

Extend the existing planned Phase 5 `/analyses/{id}/actions` and `/compare` responses with programme `career_alignment`, requirement-level `potential_gaps`, primary action, alternatives and human-review conditions. Extend Phase 6 `/scenarios` and `/report` with ordered `academic_pathways`, duration/resource provenance, scenario assumptions/comparisons and consolidated Academic Action Plans. Paths remain under `/api/v1`; all are future contracts. Do not suggest these routes exist before implementation. Keep optional alignment statistics and proposed objectives separate from verified university facts.

## Domain 1 risk and priorities

The original six requirements remain individual skills intake, updatable dated trends, explainable future-role matching/gaps, personalised ordered pathways, meaningful SDGs and multiple scenarios. Acceptance of the institutional concept and no-CV requirement is user-reported. Replacement of individual intake/matching/personalised pathways by programme profiles/academic pathways remains **UNCONFIRMED**. These additions improve institutional capability but do not establish full compliance. Record the exact written organiser response/date/channel/evidence when obtained; do not invent confirmation.

A lightweight individual form/questionnaire or labelled synthetic learner adapter is a contingency **only after clarification and separate authorization**, reusing the same evidence/services. Do not implement real student inputs, profiles or a new student-facing module now. The original brief PDF is not present in this repository; this revision relies on the existing brief-derived compliance review and the user's supplied six-item list, without claiming a fresh PDF verification.

Priority remains: finish and honestly validate Phase 4 → resolve live credentials/source and organiser gates → authorize Phase 5 career alignment/gaps and minimum sufficient actions → authorize Phase 6 pathways/scenarios/SDGs/action plans → later integration and minimal UI. No Phase 5/6 implementation, Replit deployment, new models/agents, automatic commit or push is authorized by this planning revision.
