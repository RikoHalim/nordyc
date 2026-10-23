# CODEX PROMPT — Audit the current implementation (run after any phase)

Read AGENTS.md, README.md, current Phase prompt, docs/03_DATA_MODEL.md, docs/04_ANALYSIS_AND_DECISIONS.md and docs/07_TEST_PLAN.md. Audit the **actual code** against requirements; do not assume previous agent statements are true.

1. Identify concrete missing acceptance criteria, file paths and tests.
2. Look for product violations: single-course primary workflow, manual percentage sliders, made-up CLOs, ungrounded source citations, real-vs-synthetic mixing, 'AI automates tasks therefore course obsolete', recommendation without human approval, elective suggested without programme-level coverage review, seminar attendance counted as competency.
3. Run tests/linter and report exact failures.
4. Fix **critical defects in the current phase only**, add regression tests, update STATUS.md only if justified.
5. Report remaining risks in decreasing severity. Do not add dashboards/features while fixing logic.
