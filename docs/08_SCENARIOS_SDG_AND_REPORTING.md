# Phase 6 — Academic Reskilling Pathways, scenarios and action reporting

**Phase 6 implementation is documented in [Phase 6 methodology and acceptance](28_PHASE6_ACADEMIC_PATHWAYS_ACTION_PLANS.md).** The following design contract remains relevant; exact executable schemas, routes and measured tests are in the runbook/STATUS. This phase adds institutional pathways/scenarios/SDG/Action Plans, with no student-facing platform or deployment.

## Ordered Academic Reskilling Pathways

When Phase 5 identifies a justified intervention, propose an ordered programme-level academic development pathway. Address the supported occupational competency need with the minimum sufficient intervention, preserving valuable foundations. `request_review` or `no_change` can end a pathway without manufactured learning steps. Unknown coverage should first trigger curriculum verification rather than automatic training or a new elective.

Every proposed step carries the following contract:

| Field | Required meaning |
|---|---|
| Order and dependencies | Stable step identifier, explicit sequence and prerequisites; no unexplained order or dependency cycles |
| Target competency | Source-linked occupational requirement or explicitly labelled proposed competency |
| Intervention | Existing-course update/review, redesign, proposed new course/elective, hands-on workshop, industry seminar, guest speaker, career talk or justified no change |
| Learning objectives | Proposed, assessable objectives; never backfilled as XMUM's taught outcomes |
| Suggested activities | Bounded activity outlines and rationale, not full course content or automatically generated syllabi |
| Assessment and claim limit | What could demonstrate the competency and what evidence is still required; attendance/completion alone is insufficient |
| Prerequisites | Verified prerequisites or clearly marked planning assumptions; unknown values stay unknown |
| Estimated duration and basis | Separate learning/contact/assessment hours where known, original provider duration or a transparent reviewer planning assumption, units, uncertainty and verification date; nullable when unsupported |
| Verified resources | Original provider/title/URL, source locator and verification date, relevant stated objectives/prerequisites/duration/cost and access limits; missing facts remain null |
| Occupational requirements and evidence | Versioned occupation/skill IDs and dates, curriculum support or unknowns, standards/AI/workforce references and inference rationale |
| SDG connections | Official goal/target IDs plus a specific defensible explanation and supporting pointers, or an explicit unmapped state |
| Review and alternatives | Conditions, academic reviewer status, feasible smaller alternatives and the originating Phase 5 action/analysis version |

All learning objectives and proposed activities remain recommendations. A syllabus is evidence of documented intent, not measured competence. Seminar, guest-speaker and career-talk attendance must not be credited as demonstrated technical competency. Hands-on work may contribute demonstration evidence only through appropriate assessment, limited to its actual participants and tested scope. The MVP does not collect or track individual student results.

Resources must be verified at their original source before being presented as suitable or available. Retain the provider's stated cost/free-access conditions and check date; do not promise that a resource remains free, accessible or endorsed. Provider-stated study time is not a guaranteed completion time. Derive any combined estimate transparently without double counting overlapping activity hours, and separate effort from calendar scheduling. If a resource, prerequisite or duration cannot be verified, flag it and leave the unsupported field unknown; do not invent organizations, instructors, partnerships, availability or hours. A useful pathway can have an explicit resource-verification task instead of a fabricated resource.

Illustrative sequence, **not an XMUM finding or a timed delivery commitment**: preserve foundational accounting knowledge; inspect current courses for documented coverage of supported AI-assisted accounting practices; consider an appropriately assessed practical workshop only if the gap is confirmed; consider an advanced elective only if the deeper requirement and need beyond smaller options are supported. Actual steps require source-linked requirements, reviewed curriculum evidence and reviewer approval.

## Scenarios and selective reassessment

Support **moderate** and **accelerated AI adoption** as explicitly labelled assumptions about relevant professional tasks and feasible academic responses. Store scenario assumptions separately from observations, with rationale, scope, author/rule version and uncertainty. They are comparative models, not numerical predictions of jobs, replacement probabilities, employment or placements. Do not invent an adoption rate to make a comparison appear quantitative.

Freeze programme revision, analysis/action/pathway versions, evidence manifests and parameter values for each scenario. Explain which assumption or source changed, which requirement or course finding it affects, and why a recommendation/pathway step changes or remains unchanged. Compare alternatives/no change under both scenarios; action flips are not required. Report unsupported sensitivity as `insufficient_evidence` rather than forcing a preferred scenario outcome.

Historical radar classifications (`RISING`, `DECLINING`, `STABLE`, `INSUFFICIENT_DATA`) retain population/metric/period/threshold/source fingerprints from [the methodology](18_WORKFORCE_TRENDS.md). Scenario assumptions cannot overwrite raw observations or relabel them as forecasts. Two quarterly endpoints remain short-term comparisons. `AI-TRANSFORMING` remains an independent observed-task attribute, not a fifth demand category or an adoption probability. Do not manufacture missing occupation-level observations from broad-group counts.

For a new workforce/AI/standard or curriculum version, record its changed fields and provenance, identify affected dependency links, and create a new reassessment version for relevant programmes/courses/actions/steps. Retain old results for audit. Unrelated disciplines should remain unchanged; unresolved source identity or applicability should trigger review rather than a guessed dependency. Expose trigger, affected IDs, prior/new evidence and reasons, including legitimate no-change results. Synthetic scenario fixtures stay explicitly separate from genuine observations.

## Meaningful SDG mapping

Use the official Phase 3 UN goal/target identifiers and descriptions. Map a pathway's proposed competency, intervention or occupational requirement only where a specific causal or educational rationale is defensible. Store the goal/target, rationale, evidence pointers, interpretation limits and review status. SDG 4 and SDG 8 may be relevant, but neither is an automatic tag for every role, skill or course. Leave unsupported links unmapped. A proposed contribution is not a measured SDG impact or achieved outcome.

## Consolidated Academic Action Plans

Produce a draft structured programme plan joining Future Career Alignment, evidence-supported or uncertain competency gaps, the primary minimum sufficient intervention, alternatives/no change, ordered pathway steps, scenarios and reassessment triggers. Include institution/programme, inventory coverage/all reviewed courses, title-only warnings, source and observation dates, curriculum-versus-benchmark distinction, confidence/unknowns/disagreements, resource verification and duration bases, SDG rationale, feasibility assumptions, approval status and next evidence required. A plan proposes academic action; it does not authorize curriculum changes or certify graduate competence.

Use versioned structured JSON and, if useful, Markdown export first; full PDF generation is optional later. Export only permitted source material, maintaining provenance even when an excerpt cannot be redistributed. Implemented persistence/API contracts are in [the data model](03_DATA_MODEL.md), [API contract](10_API_CONTRACT.md) and the Phase 6 runbook. PDF/export/UI work remains deferred.

Future acceptance covers ordered dependencies, prerequisites and duration/resource abstention; appropriate assessment limits; proposed-versus-taught objectives; evidence citations and rights; justified SDG mappings; moderate/accelerated assumptions isolated from observations; frozen version replay and selective changed-evidence reassessment; unrelated discipline stability; alternatives/no change and human review; synthetic isolation; and source-auditable action-plan export. Institutional pathways do not establish compliance with the brief's personalised individual pathways; that substitution waiver remains [UNCONFIRMED](09_HACKATHON_COMPLIANCE.md).
