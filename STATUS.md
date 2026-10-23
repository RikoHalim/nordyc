# SHIFT//OS — implementation status

**As of 2026-10-24:** Phase 1 revised-requirements migration **COMPLETE**. The existing backend at `453b79e` was adapted and its history preserved. No Phase 2 implementation was started.

**Pilot target:** all publicly discoverable XMUM undergraduate programmes/course lists; deep future engine validation on a small diverse subset. **Collected in this phase: 0 real institutions, 0 real programmes, 0 real courses, 0 live evidence imports.** All validation data is fictional and synthetic. Source registration is supplied metadata, not automated collection or verification.

| Phase | Revised deliverable | Status |
|---|---|---|
| 1 | FastAPI/PostgreSQL multi-institution foundation, provenance, migrations and tests | COMPLETE |
| 2 | XMUM programme/course discovery, year extraction, manual import and coverage | PENDING — not implemented |
| 3 | Standards, occupations/skills and dated workforce/AI evidence | PENDING |
| 4 | Whole-programme conservative screening and course drill-down | PENDING |
| 5 | Supported academic actions, alternatives/no change and human review | PENDING |
| 6 | Scenarios, SDG rationale and reproducible reports | PENDING |
| 7 | Integration, evaluation, change replay and security | PENDING |
| 8 | Minimal working dashboard and preliminary demo | PENDING |

## Phase 1 delivered and preserved

- [x] Preserve FastAPI factory/lifespan, settings, synchronous SQLAlchemy/psycopg, request IDs, typed errors and original API routes.
- [x] Retain institutions -> programmes -> revisions -> courses, document metadata/anchors, jobs and original `0001_foundation`.
- [x] Add `0002_catalogue_sources`: source registry, optional institution/programme metadata, catalogue source links/locators and course verification flag. Original records/IDs are preserved.
- [x] Add nested programme and manual course create/read APIs, source create/read APIs and `/health` alias; keep pagination and existing response fields.
- [x] Expose incomplete/synthetic/source-attributed quality and explicit catalogue verification assertions; no source-less record becomes verified.
- [x] Keep optional year/semester/code and unknown course type; no syllabus is mandatory or invented.
- [x] Preserve offline synthetic importer, fixture IDs/hashes/anchors and idempotency; reject API additions to immutable fixture revisions.
- [x] Pin dependencies and full environment in `requirements.lock`; target Python 3.12+ and update CI.
- [x] Update product, architecture, API, roadmap, continuation prompts and compliance docs; older filenames redirect to revised contracts.

Changed implementation files: `pyproject.toml`, `requirements.lock`, `.github/workflows/backend.yml`, `src/shiftos/{api/routers/academic.py,api/routers/health.py,core/enums.py,models/foundation.py,models/__init__.py,schemas/academic.py,schemas/common.py,services/academic.py}`, `alembic/versions/0002_catalogue_sources.py`, and catalogue/model/migration tests. See [the compatibility audit](docs/15_PHASE1_MIGRATION_AUDIT.md) for the comparison and [the data model](docs/03_DATA_MODEL.md) for all eight tables.

## Actual verification results

Local environment: Windows, Python **3.13**, PostgreSQL **16.15**. Installed Docker/PostgreSQL was unavailable; official portable PostgreSQL was used under ignored `.venv/pg-test-tools`, bound to localhost with a disposable synthetic database. No application/user database was migrated. The temporary server was stopped after verification.

Commands below use the activated virtual environment. PostgreSQL tests explicitly used a disposable `TEST_DATABASE_URL` and create/drop isolated random schemas.

| Command / check | Actual result |
|---|---|
| `python -m pip install -e '.[dev]'` | PASS with pinned dependencies |
| `python -m pip check` | PASS — no broken requirements |
| `python -m pytest -q tests/test_catalogue_api.py tests/test_api.py --basetemp=.pytest-api-tmp` | **55 passed**, 1 upstream warning |
| `python -m pytest tests/test_models.py tests/test_migrations.py -q --basetemp=.pytest-tmp-models` with PostgreSQL | **60 passed**, 1 upstream warning |
| `python -m pytest -q --basetemp=.pytest-tmp` with PostgreSQL | **144 passed, 0 skipped, 1 warning in 7.26s** |
| `python -m ruff check .` | PASS |
| `python -m ruff format --check .` | PASS — 83 files formatted |
| `python -m alembic upgrade head --sql` | PASS — both revisions compile as PostgreSQL SQL |
| Live PostgreSQL migration tests | PASS — clean upgrade/downgrade/re-upgrade, populated 0001 preservation across all seven original tables, schema/ORM comparison, constraints and loss-preventing downgrade guards |
| Real Uvicorn + PostgreSQL localhost smoke | PASS — health/readiness/OpenAPI 200; three synthetic programmes across computing/business/communication with six courses, nullable metadata and separate inventories |
| `python -m shiftos.cli import-fixture examples/sample_programme.json`, twice against disposable PostgreSQL | PASS — 12 courses both times; `created: true`, then `created: false`; original fixture/IDs preserved |

Targeted suites overlap; counts are not added to the full suite. The localhost smoke used a one-off script under ignored `.venv/phase1_live_smoke.py`; it was not added to the product. The reproducible acceptance suite is under `tests/`.

One Starlette test-client warning deprecates httpx integration and suggests httpx2. The existing tests pass; future dependency maintenance can address it. An initial new source-date assertion exposed a non-UTC immediate response; refreshing the committed source fixed it and targeted/full suites now pass. No failing test remains.

The original checkout recorded 77 tests passing in its previous GitHub Actions run on Python 3.11/PostgreSQL 16. That historical result does **not** certify this revision.

Verified for implementation commit `866df6c` in [GitHub Actions run 39998532797](https://github.com/RikoHalim/shift-os/actions/runs/39998532797): **SUCCESS** on Python **3.12** with PostgreSQL **16**. Installation, Ruff lint, formatting, and the fixture/test suite including PostgreSQL migrations all completed successfully. Local test counts above come from captured pytest output; CI success was checked from the run and job/step conclusions.

## Remaining gaps and limits

No Phase 1 acceptance blocker remains. Generic updates/deletes are deliberately absent; Phase 1's endpoint contract is create/read. Versioned corrections/import upserts, source retirement and controlled discovery belong to later phases. Revisions provide a snapshot boundary; no second snapshot table is needed now.

Public-source verification, robots/terms handling, catalogue completeness, real XMUM coverage, executing workers, standards/evidence pipelines, LLM/relevance/actions, scenarios, reports, authentication and frontend remain unimplemented. Source classes and `is_verified` are supplied assertions constrained by schema/services, not independent verification. No analysis accuracy is claimed. Python 3.12 was validated in CI, not locally. Local checks used Python 3.13 and portable PostgreSQL; Docker Compose execution remains untested locally.

## Preliminary, final and post-hackathon

Preliminary priority: a rough reproducible key-capability demonstration, clear proposal covering intended requirements and accessible GitHub. Next steps are source-backed discovery and a narrow evidence-aware review slice. Production readiness is not required for the preliminary round.

The original final brief has six must-haves: individual skills intake, dated trends, role matching, personalised pathways, explained SDG mapping and multiple uncertain scenarios. Final rubric and replacement scope must be confirmed. See [the compliance matrix](docs/09_HACKATHON_COMPLIANCE.md).

Post-hackathon: another institution through on-demand discovery, broader academic validation and production authorisation/operations. Nationwide crawling, recruitment/payment/event booking and fabricated predictive metrics remain outside scope.

## Unresolved organiser clarification — UNCONFIRMED

The user reports approval of institutional framing and exemption from CV uploads. No written response/date/channel/evidence was provided for replacing individual skills intake overall, person-to-role matching, or personalised learning pathways. SDGs and multiple scenarios are not assumed waived.

Obtain in writing: “Can programme-level profiles, occupation alignment and institutional academic interventions replace individual-profile intake, person-to-role matching and personalised learning plans for Domain 1?” Record the exact response and actual evidence when available.

## Next recommended prompt

“Read AGENTS.md, README.md, STATUS.md and prompts/02_CURRICULUM_DISCOVERY.md. Implement Phase 2 only: bounded, source-backed discovery for all publicly discoverable XMUM undergraduate programmes/course lists, optional year/elective extraction, manual import fallback, idempotent versioning and truthful coverage. Preserve the Phase 1 APIs, provenance, original data and offline fixtures. Run tests, update STATUS.md and stop.”

This task stops at Phase 1. Commit/push was explicitly requested by the user; no next-phase implementation is authorised.
