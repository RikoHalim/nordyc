# PHASE 4 — Programme-wide conservative relevance engine

Verify prior phases. Read `docs/06_ANALYSIS_ENGINE.md`, `docs/11_TEST_PLAN.md` and `fixtures/expected_test_behaviours.md`.

Implement one analysis job for **all courses in one selected programme**, including courses with little information. Combine verified catalogue and dated cross-disciplinary evidence, map appropriate academic standards, produce qualitative `review_flag` and short evidence-backed rationale for each course, plus programme-level investigation areas. **Never infer actual syllabi from titles**. Title-only courses must remain preliminary, with explicit unknowns and targeted review questions. Include citations/locators and evidence class in every finding; LLM use optional/provider-gated; offline deterministic fixture evaluator required. Rule/evidence validation must reject invented citations, auto-obsolete results and arbitrary percentages.

Tests: multi-major input; title-only abstention; all courses returned; no false missing skill assertions; provenance; snapshot version. Update STATUS; STOP.
