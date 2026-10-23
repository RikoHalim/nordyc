# CODEX PROMPT — Phase 04: Whole-Programme Course Relevance Engine

Read `AGENTS.md`, `docs/01_PRODUCT_SCOPE.md`, `docs/03_DATA_MODEL.md`, `docs/04_ANALYSIS_AND_DECISIONS.md`, `docs/05_API_CONTRACT.md`, `docs/07_TEST_PLAN.md`, `examples/expected_behaviours.md`, and current code. Implement Phase 04 **only**.

**Most important rule:** A run analyses **every course in the programme revision**, not one chosen course. Each course produces a result, including `INSUFFICIENT_EVIDENCE`.

Implement:
1. A testable pure analysis service that accepts structured document facts + skill/occupation evidence + dated snapshot and yields `CourseAnalysis` records with supported citations and uncertainty reasons. Separate extraction, source matching, LLM assistance, and evidence validation.
2. Five qualitative dimensions: foundational relevance; AI-transformed tasks; occupational relevance; curriculum currency; future resilience. Do not output arbitrary relevance percentages. Differentiate `NOT_EVIDENCED`, `UNKNOWN`, and `ASSESSED`.
3. Optional LLM interface `AnalysisProvider` with a safe offline `SyntheticDemoProvider`/stub (explicitly tagged as demo) and a real provider adapter only if configured. Typed structured JSON; no LLM output accepted with evidence references absent from input context. If no real provider/key configured, never imply one ran.
4. Evidence sufficiency validator. Course titles alone -> `INSUFFICIENT_EVIDENCE`; 'AI can do task' alone never results in course obsolete. Contradictions and stale sources -> uncertainty flags.
5. Programme-wide aggregation across all courses: potential unaddressed competencies, cross-course connections and insufficient-evidence count; do not falsely report missing skills if source set or syllabus set is partial.
6. `POST /programmes/{id}/analyses`, `GET /analyses/{id}`, `GET /analyses/{id}/courses`, `GET /analyses/{id}/courses/{course_id}`. Store input snapshot IDs and model/prompt versions. Avoid a long blocking request for production-scale jobs; make worker/job strategy realistic, independently testable.
7. Tests: N input courses -> N results; no detailed syllabus; invalid citations; no AI provider; contradictory evidence; change of evidence; immutable run.

Do **not** implement final academic action choice or frontend; Phase 05 handles actions. At end print a sample JSON analysis of full programme + tests, labelling demo outputs.
