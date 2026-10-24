# Phase 5 — Future Career Alignment and Academic Decision Studio

**Planning specification, not available functionality.** Phase 4 Course Relevance Analysis remains the current implementation priority. Implement this extension only after Phase 4 acceptance and explicit Phase 5 authorization. Reuse its versioned programme/course findings and the Phase 3 evidence infrastructure; do not create a separate career platform or student module.

## Programme-level Future Career Alignment

Help career centres and academic reviewers examine how an academic programme may prepare graduates for relevant existing and emerging occupations in Malaysia. Start with programme comparisons. A programme-to-occupation association needs a stated rationale and admissible references; label an analyst-proposed association as `inference`, and leave unsupported associations unresolved. Do not invent an occupation or its requirements because a role name sounds plausible.

For every relevant occupation, retain its source identifier/classification/edition, associated skill requirements, evidence dates, geographic applicability and limitations. Distinguish Malaysian demand evidence from an international occupational benchmark. Preserve unmatched taxonomy-to-Malaysian classification bridges; no name-only join can turn a broad-group signal into a detailed occupation measurement.

Use the existing [workforce methodology](18_WORKFORCE_TRENDS.md): `RISING`, `DECLINING`, `STABLE` or `INSUFFICIENT_DATA` is a dated, population-specific demand comparison. `AI-TRANSFORMING` is an independent attribute requiring observed professional task/capability evidence. Exposure and future predictions remain distinct. Do not force a trend, infer skill demand from occupation counts or treat declining demand or AI exposure as proof that a course is obsolete.

Compare occupational requirements with curriculum evidence using separate fields:

| Evidence state | Supported interpretation | Forbidden shortcut |
|---|---|---|
| Verified course title/year only | Catalogue presence and a preliminary coverage question | Declaring a skill taught, absent or mastered from a title |
| Verified description/syllabus/objective passage | Documented curricular intent at the passage's actual level of detail | Declaring delivery, assessment or graduate proficiency without evidence |
| Verified assessment requirement | A documented opportunity to assess the named competency | Assuming students passed or demonstrated competence |
| Appropriate assessed practical evidence, if later provided | A bounded demonstrated competency claim for the stated assessment/population | Generalising to every student, graduate or occupation |
| Missing, conflicting or unreviewed support | `unknown`, `needs_syllabus_confirmation` or `insufficient_evidence` | Treating unknown coverage as a confirmed competency gap |

Programme alignment describes supported curriculum preparation, not verified personal competence. Current MVP inputs do not include student assessment records. Record a potential gap with the occupational requirement, curriculum support or unknown state, exact references, inference rationale and confirmation needed. A confirmed curricular gap requires adequate programme coverage and reviewed content evidence; a title-only inventory supports investigation. Absence of a dedicated AI course does not prove AI is absent from existing courses.

Explain documented AI changes to relevant tasks and requirements using source-attributed evidence, separating observed capabilities/practice, occupational exposure and future predictions. Proposed competencies or learning objectives are recommendations, never claims about what XMUM currently teaches. Preserve foundational academic/disciplinary knowledge and applicable MQA benchmarks when considering change.

## Optional explainable alignment calculation

A numerical score is optional, not an MVP acceptance requirement. Prefer an evidence coverage matrix when meaningful scoring is impossible. If implemented, a deterministic, versioned rule must declare its included requirements, weights, evidence-state eligibility, numerator/denominator, coverage and missing inputs. Weights cannot be invented by an LLM or implied by occupation-level counts; declaring weights does not establish external validation. Unknown requirements must remain visible; do not silently score them as zero or remove them to inflate alignment. Define the minimum coverage and comparability gate before scoring and return `insufficient_evidence` with `score=null` when it fails.

Compare programmes only under compatible requirement sets, evidence levels and snapshots; disclose selection bias and refuse misleading rankings. A score measures the stated evidence-backed curricular alignment only. It is not an individual's employment probability, a placement forecast or a university quality ranking. Frozen inputs, rules and weights must reproduce the calculation.

## Primary action and alternatives

Generate the **minimum sufficient evidence-supported academic intervention** without asking staff to preselect an action. Explain why it addresses the supported need, then compare legitimate alternatives and `no_change`. Human academic reviewers decide; proposal generation does not approve a curriculum change.

| Action | Prerequisites | Default caution |
|---|---|---|
| `no_change` | Sufficient positive evidence of current coverage, or an explicit monitor decision | Title-only can justify monitoring pending review, not validated full alignment |
| `revise_syllabus` | Verified current content/objectives and a relevant supported requirement | With title-only evidence, propose a conditional coverage review |
| `redesign_or_consolidate` | Strong content-level evidence, coverage safeguards and an academic approval path | Never infer necessity from AI automation or exposure alone |
| `add_course_or_elective` | Reviewed programme-level coverage gap and justification against smaller options | A title-only gap remains a hypothesis; a proposed course is not an existing XMUM offering |
| `workshops_and_industry_engagement` | A supported need and a suitable activity/assessment rationale | Attendance is not demonstrated technical competency |
| `request_review` | Missing, conflicting, stale or inapplicable evidence | A valid primary outcome; identify what evidence would change it |

The unified engagement category preserves distinct activity subtypes: assessed hands-on practical workshop, industry-led seminar, industry guest speaker and career talk. Seminars/speakers/talks support awareness or insight unless appropriate assessment separately supports a narrower competency claim. Hands-on training may support demonstrated competency only with suitable assessment evidence. No partnership, speaker availability or booking is implied. A workshop can stand alone or test a potential later curriculum revision; neither purpose is automatic.

Compare adequacy, academic disruption, prerequisites, evidence strength, assessment needs and feasibility. Prefer an existing-course update or suitable workshop when it sufficiently meets the need; do not automatically create a new course. `no_change` includes monitoring conditions and risks. Budget and planning period remain optional inputs at this comparison stage, never mandatory onboarding fields. Missing costs or duration estimates stay unknown; no invented savings, placement rates or effect sizes.

## Proposed output and acceptance boundary

The future versioned response combines `career_alignment`, occupation/skill requirement pointers, `curriculum_support`, potential gaps, optional calculation metadata, `primary_action`, `alternatives`, `no_change_option`, conditions/risks, source dates, missing evidence and `reviewer_status`. Every substantive recommendation needs an admissible evidence pointer or an explicit `insufficient_evidence` outcome. Include the originating Phase 4 analysis run, programme revision, evidence manifest, rule/model versions and real/synthetic lane. Schema/Pydantic and grounding validation apply before persistence or response.

Approval remains pending until an authorized human records a decision and rationale; overrides and conditions are retained. Academic Reskilling Pathway construction is the [Phase 6 extension](08_SCENARIOS_SDG_AND_REPORTING.md), not an extra platform. Future schema/API changes are proposals in [the data model](03_DATA_MODEL.md) and [API contract](10_API_CONTRACT.md); this revision adds no migration or endpoint.

Future acceptance must cover at least three diverse disciplines; title-only/partial/contradictory evidence; source and taxonomy applicability; no false gap or competency assertion; optional-score reproducibility and abstention; primary action plus less disruptive alternatives/no change; intervention prerequisites; evidence citations; synthetic separation; and pending human review. Keep [Domain 1's individual-workflow substitution waiver](09_HACKATHON_COMPLIANCE.md) **UNCONFIRMED**. Programme alignment does not establish person-to-role matching compliance.
