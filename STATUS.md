# SHIFT//OS — implementation status

**As of 2026-10-24:** Phase 2 curriculum discovery and ingestion is **COMPLETE**, with an explicit live-network validation limitation. Phase 1 and its original APIs/fixtures/history are preserved. No AI relevance engine, recommendation engine or frontend was implemented.

**Pilot target:** all publicly discoverable XMUM undergraduate programme/course lists. The directory parser found 25 official undergraduate links. Production live retrieval **failed safely** in this environment because `www.xmu.edu.my` resolved to a private network address; no live crawl success is claimed. A separate reviewed manual fallback stored 25 directory programme facts and **141 course appearances across three programmes** in a disposable local PostgreSQL database, retrieved through real FastAPI HTTP. The remaining 22 programmes have no loaded course inventory in that validation database. None of these records certify a complete graduation curriculum or lecturer-taught content.

| Phase | Revised deliverable | Status |
|---|---|---|
| 1 | FastAPI/PostgreSQL multi-institution foundation, provenance, migrations and tests | COMPLETE |
| 2 | XMUM discovery/parser, year/elective extraction, safe import/versioning, worker, APIs and coverage | COMPLETE — live network blocked; reviewed manual fallback verified |
| 3 | Standards, occupations/skills and dated workforce/AI evidence | PENDING |
| 4 | Whole-programme conservative screening and course drill-down | PENDING |
| 5 | Supported academic actions, alternatives/no change and human review | PENDING |
| 6 | Scenarios, SDG rationale and reproducible reports | PENDING |
| 7 | Integration, evaluation, change replay and security | PENDING |
| 8 | Minimal working dashboard and preliminary demo | PENDING |

## Phase 2 delivered

- Dynamic official XMUM undergraduate link discovery; no Software Engineering-only or fixed programme list. Provider/parser configuration can expand to other institutions without new catalogue tables.
- Conservative Main Courses parsing: public titles, explicit years/semesters, elective groups, original ambiguous labels and exact source locators. Missing metadata stays null/UNKNOWN; bilingual/composite/truncated entries carry review flags.
- Durable PostgreSQL job queue and separate worker; bounded opt-in HTTPS acquisition, robots checks, rate limiting, retries, response/time limits, host allowlist/public DNS/IP pinning and sanitized failures. No network fetch in HTTP handlers.
- Reviewed structured JSON API/CLI fallback; real/synthetic lanes, supplied review assertions and missing teaching evidence remain explicit.
- Institution/programme identity reconciliation, exact-duplicate filtering, immutable source/revision fingerprints, safe re-imports, historical retrieval and older-snapshot nonreactivation. Per-programme transactions preserve successful partial progress; stale-worker fencing prevents late writes after recovery.
- Existing catalogue retrieval APIs retained; new provider/job/discovery/import/history/coverage APIs and course provenance/missing-field response fields.
- Additive migration `0003_curriculum_ingestion`; original `0001`/`0002` unchanged. PostgreSQL JSONB defaults/constraints are schema-tested; downgrade refuses populated provenance/job data loss.
- New job-submission token guard in production, bounded request bodies, no credentials in errors. Existing manual Phase 1 routes are not a production authorization system.
- Offline synthetic HTML/JSON fixtures; automated parser, persistence, API, security and PostgreSQL migration tests. Pinned Beautiful Soup added; httpx is now a runtime dependency.
- [Phase 2 runbook](docs/16_PHASE2_CURRICULUM_INGESTION.md), README, schema/API documentation, environment template and ignore rules updated.

## Actual Phase 2 verification

Local environment: Windows, Python **3.13**, portable PostgreSQL **16.15**, localhost only. A new disposable `shiftos_phase2_validation` database was used; no application/user database was migrated. PostgreSQL automated tests create/drop isolated random schemas. CI is configured for Python 3.12/PostgreSQL 16; a local pass does not itself certify a remote CI run.

| Command / check | Actual result |
|---|---|
| Baseline before Phase 2 | 141 passed, 3 PostgreSQL tests skipped; pip check passed |
| `python -m pip install -e '.[dev]'` | PASS with pinned dependencies |
| `python -m pytest -q --basetemp=.pytest-phase2-release --tb=short` with explicit disposable `TEST_DATABASE_URL` | **301 passed, 0 skipped, 1 upstream warning in 13.65s** |
| `python -m ruff check .` / `python -m ruff format --check .` | PASS; 104 Python files formatted |
| `python -m pip check` | PASS — no broken requirements |
| `python -m alembic upgrade head --sql` | PASS — all three revisions compile as PostgreSQL SQL |
| Synthetic JSON example and research registry | PASS — manifest schema validation; 73 registry rows retained |
| Independent implementation review and secret/generated-file audit | PASS — no unresolved blocker or exposed real credentials; only explicit placeholders, disposable CI credentials and test sentinels matched secret patterns |
| `.gitignore` probes / `git diff --check` | PASS — environment/secrets, local databases/journals, raw/local source files, temporary files, keys and validation artifacts excluded; no whitespace errors |
| PostgreSQL migration suite | **6 passed**: clean lifecycle/schema match, populated old-data preservation, each Phase 2 metadata-family loss guard, imported history/replay/API |
| Real Uvicorn + PostgreSQL health/readiness/OpenAPI | HTTP 200 |
| Production live XMUM discovery, twice | **FAILED safely**, `unsafe_source_url`: environment DNS returned private `10.68.12.164` for `www.xmu.edu.my`; bare host did not resolve. Zero programme/course/source records persisted by those discovery jobs. |
| Reviewed cached official directory -> existing source/programme APIs | **25 programme records** with official URLs/locators; manual source-backed directory import |
| Reviewed three-source JSON -> `import-curriculum` CLI -> `worker --once` with discovery disabled -> FastAPI reads | **SUCCEEDED**, 141 course appearances: Accounting **37**, Chinese Studies **62**, Marine Biotechnology **42** |
| Same real reviewed file imported twice | **SUCCEEDED**, 3 unchanged programmes; totals stable at 25 programmes, 28 revisions (25 directory-only initial + 3 imported), 141 courses, 4 sources |
| Evidence quality in that manual validation | **138 verified title assertions**, 3 bilingual pairs need review; all **141 title-only**, zero syllabus claims |

Raw official HTML, local smoke scripts/results and portable database files remain outside versioned product data. Exact source links and limitations are in the runbook. This was a disposable validation, not a production dataset release. The dynamic parser has diverse offline fixtures plus real 25-link directory validation and three real programme-page checks; the other 22 real programme-page layouts and **all-25 live automatic course acquisition remain unverified** on this network. A later operator must run it from an allowed public-resolving network or supply reviewed files.

An initial PostgreSQL check caught JSON equality/default comparison and a downgrade constraint-name issue; both were fixed and rerun successfully. Independent security review caught blank-token authorization and stale-worker write races; fixes and regressions now pass. One existing Starlette test-client warning deprecates httpx integration; it does not fail the suite. No failing test is accepted for commit.

## Dataset research completed — 2026-10-24

Research deliverables: [findings](docs/DATASET_RESEARCH.md), [priorities](docs/DATASET_PRIORITY.md), [acquisition plan](docs/DATA_ACQUISITION_PLAN.md), [feature mapping](docs/DATASET_TO_FEATURE_MAPPING.md), [gaps](docs/DATA_GAPS.md), [registry](data/dataset_registry.csv). These research snapshots contain 73 source/artifact rows (42 P0, 26 P1, 5 P2), with 55 Verified, 17 Partially verified and 1 Unverified access states. Research access is distinct from reusable licensing or completed production acquisition.

The research found 25 XMUM Main Courses sections/brochure links, inspected two actual DOSM JMI workbooks (Q1/Q2 2026), selected ESCO API responses and UN goals/targets, and catalogued cross-disciplinary standards/AI evidence. Registry validation checked IDs/columns/enum/URL syntax; remote availability and rights remain publisher-specific. Phase 3 evidence imports are not implemented.

## Phase 1 preserved and historical verification

Phase 1 retains FastAPI/settings, SQLAlchemy/psycopg, UUID/UTC models, all eight application tables, source registry, original manual create/read APIs, offline fixture IDs/hashes/anchors and loss-preventing migrations. See [the migration audit](docs/15_PHASE1_MIGRATION_AUDIT.md).

Historical local Phase 1 result: **144 passed, 0 skipped**, PostgreSQL 16.15/Python 3.13; Uvicorn/PostgreSQL smoke and 12-course synthetic fixture re-import passed. Its Python 3.12/PostgreSQL 16 [CI run 39998532797](https://github.com/RikoHalim/shift-os/actions/runs/39998532797) succeeded for implementation `866df6c`. These historical results do not replace Phase 2 acceptance.

## Remaining limits

- Live provider acquisition must be verified on a permitted network with public DNS. A private gateway is not an excuse to weaken source restrictions; reviewed JSON remains available offline.
- Public marketing lists are not certified complete curricula. Shared MPU, course codes/credits, cohort, unstated semesters/classifications and actual syllabi require separate confirmation. No inferred obsolete/replacement verdicts exist.
- HTML structure changes can require parser review; no general PDF or JavaScript crawler is implemented. Official-file transcription supports manual fallback. Raw HTML hash changes may create a new revision even when titles are unchanged.
- Copyright/reuse permission is not inferred from public access or robots. Whole brochures/pages are not committed. Reviewed flags/manual hashes are operator assertions, not independent source authentication.
- Full production identity/access control, automatic scheduling/monitoring, backups and Docker Compose execution remain outside this local verification. New tokens govern new catalogue job writes only.
- Standards/occupation/workforce/AI imports, LLM/relevance/actions, scenarios/SDG reports and frontend remain pending. No analysis accuracy is claimed.

## Unresolved organiser clarification — UNCONFIRMED

The user reports approval of institutional framing and exemption from CV uploads. No written response/date/channel/evidence was provided for replacing individual skills intake overall, person-to-role matching, or personalised learning pathways. SDGs and multiple scenarios are not assumed waived. See [the compliance matrix](docs/09_HACKATHON_COMPLIANCE.md).

Obtain in writing: “Can programme-level profiles, occupation alignment and institutional academic interventions replace individual-profile intake, person-to-role matching and personalised learning plans for Domain 1?” Record the exact response and evidence. This gap is preserved; no learner waiver was invented.

## Next recommended prompt and stop boundary

“Read AGENTS.md, STATUS.md, the Phase 2 runbook and completed dataset research. Implement Phase 3 reference evidence ingestion only: reusable MQA benchmarks, occupation/skill identifiers and relationships, at least two dated Malaysian workforce snapshots and cross-disciplinary AI evidence. Preserve source/date/unit/licence tracking, conservative evidence classes, offline synthetic fixtures and immutable catalogue snapshots. Do not implement the relevance engine, recommendations or frontend yet. Test, update STATUS.md and stop.”

Phase 2 implementation stops here. The user originally authorised commit/push to `feature/phase-2-curriculum-ingestion` and subsequently explicitly requested merging that branch into `main` and synchronising the local folder. No next-phase implementation is authorised.

## Main merge verification — 2026-10-24

Merged Phase 2 implementation `0c0bc54` into `main`, preserving the feature branch and existing history. The earlier uncommitted local documentation revisions were saved in recoverable Git stash `codex-doc-revisions-before-phase2-merge`; they were not overlaid on the newer Phase 2 status/schema/API documents. All versioned repository folders are included in the merge, and the local virtual environment was updated from `requirements.lock` and the editable project.

- Current local suite: **295 passed, 6 skipped, 1 warning in 10.83s**. All six skipped tests require explicit PostgreSQL `TEST_DATABASE_URL`; the earlier 301-test PostgreSQL result above remains historical branch evidence, not a fresh database run.
- Ruff lint passed; formatting passed with 104 Python files already formatted.
- Dependency integrity check passed; PostgreSQL SQL generation passed for all three migrations. No application/user database migration was applied by this merge task.
- Read-only review of the migration, APIs, fetch boundary, worker/idempotency and Phase 1 compatibility found no merge blocker. Whitespace checks passed.
- Synchronising Git files does not import the earlier disposable validation database or perform live XMUM collection. The documented live-network/coverage limitations remain unchanged.
