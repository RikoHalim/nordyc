# Continue the existing SHIFT//OS repository

This checkout already contains Phase 1. Do not create a new repository, re-run a greenfield foundation prompt, reset Git history or replace working components. `STATUS.md` records tested completion; later specifications are not implemented features.

## Scope audit or Phase 1 maintenance prompt

```text
Read AGENTS.md, README.md, STATUS.md, docs/00_READ_ME_FIRST.md, docs/03_DATA_MODEL.md, docs/10_API_CONTRACT.md and docs/15_PHASE1_MIGRATION_AUDIT.md. Inspect code and migrations before changes.

Audit the current Phase 1 foundation against revised requirements. Preserve its factory, sessions, error envelope, existing APIs, immutable fixture importer, revisions, documents, anchors and migration 0001. Make only necessary additive compatibility corrections, with migrations and tests. Do not recreate the repository, implement Phase 2, build an AI engine/frontend, or commit/push automatically.

Report preserved/changed components, actual test output, migration safety and remaining gaps. Update STATUS.md honestly and stop after the approved phase.
```

## Next prompt — only when explicitly authorised

Use `prompts/02_CURRICULUM_DISCOVERY.md`, which replaces the upload-first Phase 2 prompt. Target all publicly discoverable XMUM undergraduate programmes and source-backed course titles/year grouping, with bounded access and manual import fallback. Syllabi are optional. Phase 2 is not part of the Phase 1 migration.

Continue one phase at a time: inspect -> smallest plan -> authorised implementation -> tests/migrations -> docs/STATUS -> report -> stop. Never mark future work complete because its specification or fixture exists.
