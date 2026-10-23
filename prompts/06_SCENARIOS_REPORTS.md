# CODEX PROMPT — Phase 06: Scenarios, Re-analysis and Academic Reports

Read `AGENTS.md`, `docs/04_ANALYSIS_AND_DECISIONS.md`, `docs/05_API_CONTRACT.md`, `docs/06_SOURCES_AND_PROVENANCE.md`, `docs/07_TEST_PLAN.md`. Implement Phase 06 **only**.

Tasks:
1. Two transparent scenario presets: `MODERATE` and `ACCELERATED` AI adoption. Presets are **qualitative assumptions** about adoption/impact; no invented economic or employment projections. Show differences only when evidence/assumptions support them.
2. Create scenario comparison API and immutable run snapshots. Import `SYN-Q2` after `SYN-Q1` and demonstrate re-analysis of the same curriculum, with an explanation of any changed course-level/programme-wide action.
3. Academic report as **structured JSON** listing entire course inventory count, per-course findings, primary actions, alternatives, source references/dates, unknown data, scenario contrasts, programme-wide opportunities and provisional SDG mappings with *target* and rationale. Missing justification => `NEEDS_REVIEW`.
4. Add review decision endpoint restricted to an explicitly supplied review actor/role label in demo; do not imply production-grade authentication. Action only changes on a deliberate request, never on AI generation.
5. Tests for immutable past runs, scenario determinism, uncertainty labels, no fabricated stats, report references, SDG review state and explicit approval.

Don't spend this phase on a PDF designer or UI. JSON report is the MVP contract; export formatting can follow later.
