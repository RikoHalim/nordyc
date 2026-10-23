# Academic Decision Studio — recommendations and comparison

## Principle

AI generates the **primary evidence-supported recommendation first**, without asking staff to preselect an action. Staff can inspect the reasoning and compare other choices. `no_change` is a genuine counterfactual. Human staff decide.

| Action | Prerequisites | Default caution |
|---|---|---|
| `no_change` | Positive sufficient evidence that existing curriculum meets identified requirement OR defensible monitor status | Title-only supports `monitor pending review`, not validated "no change necessary" |
| `revise_syllabus` | Verified current content/outcomes AND credible relevant new capability/standard | Title-only -> `consider syllabus review`, not definite rewrite |
| `redesign_or_consolidate` | Strong content-level evidence and academic approval path | Never infer from AI automation alone |
| `add_course_or_elective` | Programme-level missing coverage verified or plausible and well documented | Title-only gaps remain hypotheses; don't invent course availability |
| `workshops_and_industry_engagement` | Skill/exposure need with justified rationale | Hands-on skills may be assessed; seminar/talk attendance does not prove technical competency |
| `request_review` | Evidence missing/conflicting | Valid, honest system outcome |

## Activity subtypes (single category)

- Hands-on practical training: practical evaluation possible; programme/course impact requires evidence.
- Industry-led seminar: exposure to trends, knowledge-check optional.
- Guest speaker: professional insight; no skill proficiency attribution from attendance.
- Career talk: occupation awareness/pathways; no technical skill uplift credited.

Workshop may be standalone **or** a pilot for future curriculum revision. Neither role is assumed. No partnership or guest booking claim without proof.

## Minimum sufficient intervention

Compare academic disruption, speed, source strength, verification requirements and learning-outcome relevance. Prefer the **least disruptive adequately justified** intervention, not the highest impact-looking option. No invented budget savings or percentage labour-market results. Budget and schedule optional *at comparison step*.

## Output schema shape

`{primary_action, alternatives:[...], no_change_option, evidence_ids, conditions, risks, missing_evidence, confidence_label, reviewer_status}`.

An action can have `condition: pending_detailed_syllabus_review`. Frontend should distinguish investigation candidates from academically approved actions.
