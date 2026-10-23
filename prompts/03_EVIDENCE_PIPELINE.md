# PHASE 3 — Academic/workforce/AI reference pipeline

Verify Phases 1–2. Read `docs/05_SOURCES_AND_DATASETS.md`, source registry and data model.

Build versioned `sources`/`evidence_items` with published/observed/collected dates; typed ingestion adapters for curated MQA standards, occupation/skill taxonomy (ESCO; MyNSR where permitted), dated DOSM/MyCOL occupational signals, and evidence on AI impact by discipline. Import only officially available, licensed/authorised data; if source cannot be imported, record availability and use explicitly synthetic **offline** fixtures. Add source-coverage diagnostics and an occupation-vs-skill unit type check. No fabricated automatic live updates.

Produce two labelled dated snapshots (actual where permitted or synthetic). Verify every item can be traced back to source and original time window. Do not call any study an exact prediction of job loss. Tests for deterministic refresh, cross-discipline mapping and missing evidence.

Update `STATUS.md` and STOP. Next Phase 4.
