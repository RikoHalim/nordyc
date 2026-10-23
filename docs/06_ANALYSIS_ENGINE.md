# Programme-wide relevance engine — evidence first

## Core question

> Are the publicly documented programme offerings plausibly aligned with current/foreseeable occupational and AI changes, and which course areas deserve academic review?

## Inputs

`programme snapshot` + `selected dated workforce/AI evidence snapshot` + `occupation and standard crosswalk` + `scenario assumptions` + `optional syllabus`

## Outputs

1. Coverage inventory: verified programmes/courses and evidence level (`title_only`, `public_description`, `detailed_syllabus`, missing).
2. Per-course **review flag** and specific evidence-based investigation question; keep uncertainty visible.
3. Programme-level **possible** missing topics, overlaps, sequences and supplementary interventions, conditioned on available documentation.
4. Evidence inspector: quote, URL, date, provenance and alternative interpretation.

## Assessment dimensions (qualitative, not fabricated score)

- Foundational educational purpose: enduring conceptual content (cannot be fully inferred from a title).
- AI/task transformation: cited capabilities and limitations affecting relevant professional tasks.
- Occupational alignment: appropriate roles/skills in Malaysian context (with crosswalk caveats).
- Curriculum currency: compare documented outcomes/topics/assessments **only if available**.
- Future resilience: transferable judgement skills and adaptability (hypothesis when title-only).

## Evidence gates

| University evidence | Allowed result | Prohibited conclusion |
|---|---|---|
| Course title + year only | Title-confirmed, possible task impacts and questions for academic review | Taught outcomes, missing AI module, outdated content, definitive replacement |
| Official description | Compare stated objectives and source-referenced requirements; provisional suggestions | Claim actual exams/assessments not published |
| Detailed official syllabus & assessments | More specific content/assessment mapping and review recommendation | Claim perfect competence / automatic hiring outcomes |
| No course evidence | Incomplete catalogue; request review | Fabricated course |

## Deterministic approach

Evidence gathering, taxonomy matching, source comparison, rule-based eligibility filters, then LLM for **citation-bounded explanations**. Data changing should recompute from versioned sources. A verdict with zero citations must fail closed.

## Recommended statuses

`monitor`, `investigate`, `needs_syllabus_confirmation`, `insufficient_evidence`, `validated_action_candidate`; never universally rank courses from title-only data.

## Relevance example (NOT an XMUM audit)

Verified: course titled `Software Quality Engineering` exists. Independently sourced: AI-assisted software testing practices are evolving. **Allowed**: "Review whether assessments cover critical evaluation of AI-generated test artifacts"; **not allowed**: "XMUM does not teach AI testing".

## Programme-level inference

Absence of a course named `Responsible AI` is **not evidence** the content is not taught anywhere else. Frame as "verify coverage of responsible AI across relevant courses".
