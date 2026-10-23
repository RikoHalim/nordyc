# Phase 1 migration handoff

The foundation at commit `453b79e` is retained and adapted to revised requirements. [STATUS.md](STATUS.md) records measured verification; [the audit](docs/15_PHASE1_MIGRATION_AUDIT.md) compares requirements with implementation.

## Preserved

FastAPI factory/lifespan, settings, synchronous SQLAlchemy/psycopg, request IDs, `{error:{code,message,details}}`, original APIs, Compose setup, seven original tables and migration `0001_foundation` remain. Revisions, document anchors, jobs and original synthetic fixture IDs/payloads/checksums remain usable. No provenance is invented.

The importer remains `python -m shiftos.cli import-fixture examples/sample_programme.json`. It preserves all courses, electives and missing syllabus metadata. Identical input is idempotent; conflicting IDs/content are refused. API course creation also refuses mutation of checksum-protected fixture revisions with 409.

## Adapted

Additive `0002` adds `sources`, institution/programme metadata, provenance links and a course verification flag. Nested institution/programme/course create/read routes and source operations extend the original global programme APIs. See [the API contract](docs/10_API_CONTRACT.md).

The relational path remains institution -> programme -> revision -> courses. Catalogue records can link source metadata/locators. Missing course type stays `UNKNOWN`; year/semester/code are optional. Source registration and supplied verification assertions perform no external verification.

## Run and upgrade

Use Python 3.12+ and the complete [README setup](README.md#local-setup). Set credentials and run `python -m alembic upgrade head`. Back up an existing database first, preserving 0001/history. Added fields default to unknown/unverified and upgrades do not drop old rows. Downgrade guards populated added metadata. Actual migration test results and PostgreSQL limitations belong in STATUS.

The fixture programme ID remains `693f20d6-4952-5c77-aae3-47c59928449d`. Read `/api/v1/programmes/{id}/courses` across all pages. It contains 12 invented courses and is not an XMUM audit. Revised `fixtures/` are future acceptance inputs, incompatible with the current importer format.

## Boundary and next step

No live XMUM coverage, parsing, workforce pipeline, LLM, analysis, academic decisions, scenarios or frontend is claimed. Course titles suffice for future preliminary review, never proof of taught syllabus content.

Next recommendation: **Phase 2 only**, `prompts/02_CURRICULUM_DISCOVERY.md`, after explicit authorisation. Written confirmation of remaining original final-round requirements is pending. Commit/push only when explicitly requested. Next-phase implementation requires separate authorisation.
