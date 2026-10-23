# 01 — Product and MVP Scope

## Positioning

SHIFT//OS helps Malaysian universities decide **which existing courses still serve their educational purpose in the AI era, which need revision, and what additional academic responses are justified**. It is a decision-support product, not an autonomous curriculum approval system.

## Intended users and power boundaries

- Primary: university career-centre analysts/administrators.
- Collaborators and decision-makers: programme coordinators, lecturers, faculty boards, academic quality / curriculum committees.
- Career centre may recommend; authorised academic owners review and approve. Never label generated suggestions as approved changes.

## Main questions

1. What does the **whole programme** currently teach? Which courses are compulsory/elective?
2. Which course foundations remain durable despite AI change?
3. What specific occupational tasks and professional practices are being changed by AI, according to dated evidence?
4. Do the actual documented learning outcomes and assessments adequately address those developments, or is the evidence insufficient?
5. What is the **least disruptive evidence-supported intervention** across the programme?
6. How could alternate AI-adoption conditions change priorities? How will a later source snapshot trigger reconsideration?

## Core backend workflow

1. Institution and programme identified; upload programme structure and available detailed syllabi; no country selector (Malaysia fixed).
2. Extract all course entries into a programme inventory; mark exact origins, duplicate course codes, compulsory/elective status, and unknown metadata.
3. Extract course learning outcomes, topics and assessments **only when visible in uploaded documents**. Missing information -> review flag, not invented data.
4. Import versioned Malaysian workforce and dated AI-development evidence; map occupational tasks/skills to courses with transparent justification.
5. For **every course**, produce foundational relevance, AI-transformation exposure, curriculum currency, evidence sufficiency and supported claims.
6. At the **programme level**, identify potential gaps, duplication for investigation, cross-course coverage, and intervention options.
7. Recommend **one primary response** where support exists, list credible alternatives and no-change where applicable; otherwise `INSUFFICIENT_EVIDENCE`.
8. Compare moderate and accelerated AI scenarios and optional later-stage constraints; produce structured academic review (not auto-approved).
9. When a dated source snapshot is updated, preserve old run and allow deliberate re-analysis.

## Academic interventions

- `KEEP_NO_CHANGE` — retain current course/programme content, review if new evidence emerges.
- `REVISE_SYLLABUS` — update topics, materials, assessments, or CLOs while preserving course foundations.
- `MAJOR_REDESIGN_REVIEW` — investigate substantial redesign; `REPLACE_OR_CONSOLIDATE_REVIEW` only with unusually strong evidence and clear human review.
- `NEW_ELECTIVE` — introduce a specialist course **only** for a programme-level gap not reasonably served by revision.
- `WORKSHOPS_AND_INDUSTRY_ENGAGEMENT` — one parent category with `HANDS_ON_WORKSHOP`, `INDUSTRY_SEMINAR`, `GUEST_SPEAKER`, `CAREER_TALK` event types.
- `REQUEST_MORE_EVIDENCE` — explicit non-action when sufficient analysis is impossible.

A workshop can be a standalone fast response or an optional evidence-gathering pilot. Attendance at seminar, guest speaker, career talk is NOT assessed competency attainment.

## MVP demo and success

- One institution, one programme, 8–12 courses in initial fixture; **no hard-coded course cap**.
- At least one course with enough **synthetic** detailed syllabus information for a review example and one course missing details to test `INSUFFICIENT_EVIDENCE`.
- At least two separately date-stamped workforce/AI evidence snapshots, with one changed signal producing visible re-assessment.
- Demonstrate retain, revise, workshop, possible elective and request-more-evidence outcomes as warranted by synthetic facts.
- One programme-wide overview, per-course drilldown data, sourced explanations, alternative actions, SDG rationale, 2 scenarios, and human-review state.

## Explicit non-goals

- Full curriculum authoring, automatic replacement/approval, student information system integration, job applications or recruitment, event scheduling, LLM-generated labour-market statistics, student CV intake, individual tracking, chatbot, payment, custom AI training, predicted employment rates.
- No frontend for the **first backend milestone**; API documentation is adequate.

## Important compliance caveat

The hackathon organising committee reportedly accepted the institutional framing and said CV upload is unnecessary. The original Domain 1 brief also described individual role-matching and personalised pathways; **do not assume those other requirements were waived** until organisers confirm. See `docs/09_SCOPE_AND_OPEN_QUESTIONS.md`.
