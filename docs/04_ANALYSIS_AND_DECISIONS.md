# 04 — Course Relevance and Decision Rules

This is the **main product**. Relevance concerns educational purpose, **not** how many tasks AI can automate.

## Three evidence layers

**A. What the university really teaches.** Course titles and programme lists establish inventory only. Detailed CLOs, course topics, assessment tasks, textbooks/activities (if present) establish learning evidence. Use extracted passages with anchors and distinguish claims from the document vs guesses.

**B. What is changing.** Time-stamped AI capabilities/limitations, tasks affected, professional practices and occupational requirements. Attribute each claim to source + date + excerpt + jurisdiction; track contradictory evidence and uncertainty.

**C. What to do academically.** Compare course aims against documented changes and coverage elsewhere in the programme. An LLM can propose a mapping, but code must validate it against actual evidence.

## Analysis dimensions (qualitative, no arbitrary 0–100 score)

- **Foundational relevance**: durable concepts students must understand to reason, critique and verify AI outputs.
- **AI transformation exposure**: tasks significantly affected by AI; `AUGMENTED`, `AUTOMATED_IN_SOME_CONTEXTS`, `NEW_TASK`, `UNKNOWN` with supporting source.
- **Current curriculum currency**: what stated CLOs/topics/assessments cover; distinguish `NOT_EVIDENCED` from definitely absent.
- **Occupation/skill relevance**: relevance to Malaysian occupations and skills; do not convert occupational job-posting counts into specific skill-demand growth.
- **Future resilience**: adaptability, critical evaluation and emerging practices, with explicit academic reasoning.

## Minimum requirements before conclusions

**Course can have a provisional `INSUFFICIENT_EVIDENCE` status** when there is only a course title, incomplete syllabus, missing assessments for a disputed competency, stale workforce evidence, contradictory sources or unverified mappings. Record why and what is needed.

**Do not conclude a course is irrelevant or recommend replacement** solely because:
- A named AI tool can generate some outputs in that field.
- The detailed syllabus doesn't contain literal buzzwords like 'GenAI'.
- A job category's posting count fell.
- LLM semantic similarity to a future skill is low.
- An elective is absent from a partial curriculum catalogue.

## Structured output contract

Each `CourseAnalysis` must contain:

```json
{
  "course_id": "UUID",
  "status": "INSUFFICIENT_EVIDENCE",
  "evidence_status": "PARTIAL",
  "foundational_findings": [{"claim": "...", "document_anchor_ids": ["UUID"]}],
  "ai_developments": [{"claim": "...", "evidence_passage_ids": ["UUID"]}],
  "curriculum_currency": {"status": "UNKNOWN", "explanation": "..."},
  "uncertainties": ["Detailed assessment information missing"],
  "recommendation_readiness": false
}
```

This is an **illustrative DTO shape**; use real UUIDs returned by the database and update exact DTOs in code/tests. Never use fabricated UUID claims. If model claims have invalid references, reject that claim and log validation error; don't manufacture new references.

## Academic actions and decision guardrails

| Action | Minimum reasoning |
|---|---|
| `KEEP_NO_CHANGE` | Adequate relevant evidence that foundations and scope remain justified; specify monitoring conditions |
| `REVISE_SYLLABUS` | Supported gap/changed practice can be addressed within existing course objectives and feasible assessments |
| `MAJOR_REDESIGN_REVIEW` | Several documented objectives/assessments merit substantial change; requires faculty review |
| `REPLACE_OR_CONSOLIDATE_REVIEW` | Exceptional; robust multi-course overlap/declining value plus explicit safeguarding of foundations; never automatic retirement |
| `NEW_ELECTIVE` | Programme-level specialist gap not adequately met by existing courses; show why revision/workshop are less suitable |
| `WORKSHOPS_AND_INDUSTRY_ENGAGEMENT` | Needs targeted training/exposure; choose subtype and **do not claim unassessed mastery** |
| `REQUEST_MORE_EVIDENCE` | Analysis lacks document/source support; not the same as no change |

The AI suggests the strongest justified primary action, and code also returns feasible alternatives (including retain/no change when support exists). `REQUEST_MORE_EVIDENCE` is the default if evidence is insufficient. Programme-level gap recommendations can coexist with course-level actions. Do not force one global programme action.

## Minimum Sufficient Intervention (differentiator)

1. Identify documented educational problem.
2. Compare **no change**, targeted syllabus revision, elective and workshops/industry engagement; allow substantial redesign review when warranted.
3. Prefer **least disruptive adequate** intervention under validated academic constraints. Optional budget, staff time/facilities and implementation dates belong HERE, not on onboarding.
4. Explain why alternatives were not recommended. User can inspect and select; final decision remains human.
5. Never invent cost, staff availability, approval or partnerships. Unknown feasibility stays unknown.

## Workshop-to-Curriculum Validation

Hands-on workshop may pilot a new skill. Measure competence only with documented assessment; synthetic demo outcomes must remain labelled. A seminar, guest speaker or career talk measures exposure or awareness, NOT technical skill attainment. A workshop need not turn into an elective.

## Scenario comparison and updates

- Provide `MODERATE` and `ACCELERATED` **assumption sets**, with explicit labels and no numerical employment predictions.
- AI model/provider may offer interpretation; different scenarios must cause traceable differences only where assumptions materially affect evidence/priority.
- Record snapshot ID. A new dated signal creates a **new run**; show reasons for changed, unchanged or uncertain actions. Never silently overwrite historical reports.

## SDGs

Map relevant academic actions and/or occupation/skill claims to specific SDG goal and *target* with a reasoned connection. For most pilots, SDG 4 and SDG 8 are candidates, **not guaranteed matches**. If links cannot be supported, mark `NEEDS_REVIEW`; don't decorate the UI with all 17 badges.
