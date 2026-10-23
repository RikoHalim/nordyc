# Synthetic test fixtures — NOT XMUM FACTS

All fixtures are fabricated for local development and cross-disciplinary tests. Example programme names are generic; no fixture represents a real current XMUM syllabus, actual workforce statistic or accredited MQA curriculum.

- `synthetic_university_catalogue.json`: one imaginary university with **three distinct academic fields**, course titles, years, intentionally missing data.
- `synthetic_evidence_snapshots.json`: two fictitious time-stamped changes for selected occupations/task evidence; numbers are made up solely to verify deterministic scenario replay.
- `expected_test_behaviours.md`: mandatory conservative conclusions and negative tests.

Codex must not cite these as evidence about XMUM or Malaysia. UI/API must set `synthetic_demo: true` and visually label generated results.

## Phase 1 format boundary

These revised cross-disciplinary catalogues and evidence snapshots are acceptance specifications for later phases. They are not input to the preserved Phase 1 CLI. Use `python -m shiftos.cli import-fixture examples/sample_programme.json` for the working offline foundation import. Current catalogue API records use `is_synthetic: true` and computed `data_quality: synthetic`; `synthetic_demo` is the evidence class.
