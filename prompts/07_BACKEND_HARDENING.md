# PHASE 7 — Backend integration, evaluation and security

Verify Phases 1–6. Read `docs/11_TEST_PLAN.md`, `docs/14_SECURITY_AND_OPERATIONS.md` and fixtures.

Create one-command reproducible offline demo setup, database reset/seed scripts, end-to-end tests, source/LLM grounding checks, deterministic fixture mode, and explicit error states for inaccessible websites. Implement basic secure external-source access (host allowlisting, SSRF/redirect checks, limits) and no leaked keys/logs. Measure evidence coverage and abstention over at least three synthetic disciplines; show actual test results, no fake accuracy stats. Ensure backend runs without private API keys and source update replay is testable.

Update STATUS and stop. Next is a minimal dashboard, not production enterprise frontend.
