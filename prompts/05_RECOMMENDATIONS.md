# CODEX PROMPT — Phase 05: Academic Recommendation Engine

Read `AGENTS.md`, `docs/04_ANALYSIS_AND_DECISIONS.md`, `docs/03_DATA_MODEL.md`, `docs/07_TEST_PLAN.md`. Implement Phase 05 **only** after Phase 04 works.

For each sufficiently grounded course/programme finding, recommend a defensible **primary academic action first** and return alternatives. Use transparent business guards, not a vague prompt to 'decide which course is outdated'. Required actions: `KEEP_NO_CHANGE`, `REVISE_SYLLABUS`, `MAJOR_REDESIGN_REVIEW`, optional strongly evidenced `REPLACE_OR_CONSOLIDATE_REVIEW`, `NEW_ELECTIVE`, `WORKSHOPS_AND_INDUSTRY_ENGAGEMENT`, `REQUEST_MORE_EVIDENCE`.

Tasks:
1. Create action enums and deterministic qualification functions. Prefer the **minimum sufficient intervention**; expose why other choices are less suitable. AI can supply explanations but cannot bypass evidence guards.
2. Explicitly distinguish (a) course-level actions and (b) programme-wide gaps that may justify new electives or workshops. Never recommend an elective simply because one course did not include a skill.
3. Industry engagement subtypes: hands-on workshop, industry seminar, guest speaker, career talk. Attendance at talks is not skill achievement; workshop skill impact needs assessment evidence. A workshop can be standalone or optional pilot, not always before an elective.
4. Optional budget, implementation timing, resources and staffing constraints are **considered in this studio**, not initial upload forms.
5. Primary recommendation, alternatives, evidence refs, caveats and `PROPOSED` review status; academic approval remains human.
6. Tests for no-change, targeted update, missing evidence, new elective with programme-level justification, replacement review safeguards, workshop type outcome guards, unapproved by default.

Demo should show recommendations for a whole programme with at least one insufficient-evidence course. Do not implement simulation or frontend yet.
