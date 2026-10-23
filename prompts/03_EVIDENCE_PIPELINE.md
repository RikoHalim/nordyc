# CODEX PROMPT — Phase 03: Versioned Workforce and AI Evidence

Read `AGENTS.md`, `docs/03_DATA_MODEL.md`, `docs/06_SOURCES_AND_PROVENANCE.md`, `docs/07_TEST_PLAN.md`, and previous implementation. Implement Phase 03 **only**.

Build the versioned **evidence ingestion** pipeline for Malaysian occupations, skills, AI capabilities/task changes and academic standards. The MVP imports curated JSON/CSV files; it does **not** scrape websites or invent live data. Use `examples/sample_evidence.json` as a synthetic test case.

Requirements:
1. Add `evidence_sources`, `evidence_passages`, `signal_snapshots`, skill and occupation mapping persistence/migrations. Store provenance fields, publication and observation dates separately, jurisdiction, licence, `is_synthetic`.
2. Importer validates schema, dates, IDs, claim type, excerpt and source integrity; prevent duplicates/version overwrites; reject orphan passage IDs.
3. Implement source/snapshot import/list APIs, source lookup and paginated evidence retrieval.
4. Support `SYN-Q1` and `SYN-Q2` versioned snapshots with changed underlying passage; verify both persist unchanged and can be compared.
5. Make rule guard explicit: a job-opening number for an occupation does not determine the demand for an individual skill. Never infer skill growth from it.
6. Provide source integrity tests, invalid payload and contradictory/old evidence tests.

Keep AI providers and course-relevance outputs out of this phase. Show local import command and provenance queries at end.
