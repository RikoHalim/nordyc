# SHIFT//OS — implementation status

**As of 2026-10-24:** Phase 3 evidence infrastructure and Future Workforce Radar are **FUNCTIONAL; bounded prototype evidence gates met**. Genuine PostgreSQL evidence now includes 38 legacy ESCO occupations, 10 English-described skills, 39 relationships, 12 MQA benchmark summaries, 186 official UN goal/target records, 247 workforce observations and 20 AI cards, plus 76 unreviewed PDF page references. **Ready to begin a conservative Phase 4 prototype against frozen subsets, not a complete/current all-programme evidence catalogue.** Current English ESCO, TalentCorp permission, reviewed Malaysian crosswalks and full academic coverage remain explicit restrictions. No Phase 4 analysis, academic recommendations, frontend redesign or additional AI model was implemented.

**Pilot target:** all publicly discoverable XMUM undergraduate programme/course lists. The directory parser found 25 official undergraduate links. Production live retrieval **failed safely** in this environment because `www.xmu.edu.my` resolved to a private network address; no live crawl success is claimed. A separate reviewed manual fallback stored 25 directory programme facts and **141 course appearances across three programmes** in a disposable local PostgreSQL database, retrieved through real FastAPI HTTP. The remaining 22 programmes have no loaded course inventory in that validation database. None of these records certify a complete graduation curriculum or lecturer-taught content.

| Phase | Revised deliverable | Status |
|---|---|---|
| 1 | FastAPI/PostgreSQL multi-institution foundation, provenance, migrations and tests | COMPLETE |
| 2 | XMUM discovery/parser, year/elective extraction, safe import/versioning, worker, APIs and coverage | COMPLETE — live network blocked; reviewed manual fallback verified |
| 3 | Evidence acquisition, workforce radar and independent AI task evidence | FUNCTIONAL — bounded evidence gates met; legacy/language/currentness/permission limits explicit |
| 4 | Internal-first hybrid retrieval, controlled external fallback and conservative course screening | PLANNING REVISED — implementation PENDING |
| 5 | Supported academic actions, alternatives/no change and human review | PENDING |
| 6 | Scenarios, SDG rationale and reproducible reports | PENDING |
| 7 | Integration, evaluation, change replay and security | PENDING |
| 8 | Minimal working dashboard and preliminary demo | PENDING |

## GitHub publication authorization and verification — 24 October 2026

The user subsequently explicitly requested publication to GitHub. This authorizes committing/pushing the completed Phase 3 implementation and Phase 4 planning documentation together to `origin/main`; earlier no-commit/push statements record the prior phase stop boundaries. No Phase 4 implementation is included.

Fresh pre-publication checks: **487 tests passed, zero failed/skipped**, including PostgreSQL integration, in **37.37s** using the existing disposable local validation database. One existing upstream Starlette/httpx deprecation warning remains. Ruff lint passed, formatting passed for 134 Python files, dependency integrity passed, all four PostgreSQL migrations generated successfully, and staged whitespace checks passed. No remote CI result is claimed by these local checks.

Publication excludes `.idea`, private uploads, local databases/downloads and restricted research originals/cards. Only the permitted attributed ESCO/UN reference subsets and explicitly synthetic engineering fixtures accompany the implementation. Git publication does not deploy a service, transfer the local evidence database or make all restricted evidence redistributable.

## Phase 4 planning revision — 24 October 2026

**Documentation only; Phase 4 implementation has not started.** The [hybrid evidence retrieval contract](docs/19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md), [analysis specification](docs/06_ANALYSIS_ENGINE.md), architecture, schema/API targets, roadmap, implementation prompt and testing requirements now specify:

- PostgreSQL as the primary source for occupational skills, applicable academic standards, dated workforce indicators and independent AI task evidence; claim-specific checks for quality, relevance, dates/edition, rights and completeness.
- Automatic, bounded research of authoritative original sources for important missing/stale/insufficient evidence once an approved provider and use policy are configured. Search snippets and unsupported model findings remain candidates; restricted sources retain manual/insufficient outcomes.
- Original-source claim checks with URLs, dates/precision, locators, permitted excerpts and provenance; permission-aware versioned storage/cache, immutable run manifests and correction/rights invalidation.
- One disclosed configured existing LLM for structured, citation-bounded analysis; deterministic workforce calculations; every available course returned; title-only benchmarking separated from verified syllabus content; explicit **INSUFFICIENT EVIDENCE**, without automatic obsolescence from decline or AI exposure.
- Configurable allowlists, budgets/rates/timeouts, safe transport, private-upload/egress controls, durable jobs, synthetic offline fixtures and a planned internal-only/fallback/security/cache/grounding test matrix across diverse disciplines.

**Implementation prerequisites remain open:** there is no runtime LLM connection/provider/model configured in this repository and no automatic research adapter yet. Select/configure one approved existing model and approved search provider, establish source/use/privacy policies and implement the documented Phase 4 contracts only when authorized. Phase 3 source/identity/currentness limitations below are preserved; a new plan does not fill them.

This revision changes documentation only: no runtime code, tests, dependencies, configuration, data, migrations or Phase 1–3 behavior were changed. No new research, source import, model call or database migration was performed. The 487-test result below remains the historical Phase 3 completion result, not a new Phase 4 test pass. Documentation checks are reported separately for this revision. No commit or push was performed; stop before implementation.

Documentation validation: **PASS** — 12 revised/new Markdown files, 55 local links/anchors, balanced code fences and UTF-8 checks; `git diff --check` passed. SHA256 comparison against this task's starting snapshot found **zero changes in 96 implementation/data/configuration files**. Read-only review reconciled official-description evidence with optional syllabus evidence. Pytest was not rerun for this documentation-only revision; no Phase 4 tests or live integration pass are claimed.

## Phase 3 completion and measured readiness

The initial 405-test implementation was functional but lacked genuine taxonomy, standards and SDGs. This authorized completion preserved those components and filled a bounded real-data baseline. Read [the complete ingestion report](docs/PHASE3_INGESTION_REPORT.md), [runbook](docs/17_PHASE3_EVIDENCE_INGESTION.md) and [workforce methodology](docs/18_WORKFORCE_TRENDS.md) for exact source scopes and commands.

- **Registry/acquisition:** 75 rows (original 73 + explicit legacy ESCO and official UN resolution artifacts); latest source research and actual `phase3_*` outcomes remain separate. Interactive browser was unavailable; official web reads and legitimate normal downloads/manual imports were used. No SSRF, robots, CAPTCHA/login, rights or size safeguard was weakened.
- **Taxonomy:** 38 real occupations, 10 skills with actual English descriptions, 39 source essential/optional relationships from **ESCO v1.0.3**. Four occupation labels are source-English and 34 retain Arabic; no translations were invented. Complete Arabic CSV ZIP integrity verified; only complete relevant English blocks from a **partial** same-edition Turtle retrieval were used. Current English ESCO remains unavailable; old-edition/currentness limits are prominent. Exact joins queried and replay unchanged.
- **Benchmarks:** 12 narrow MQA bachelor summaries across Computing, Accounting, Business and Biotechnology, actual pages/edition/hash/date precision preserved. Scoped attributed prototype research, not a full-text redistribution licence, institutional teaching assertion or independent academic validation.
- **SDGs:** official A/RES/70/1 resolution supplied 17 goals + 169 targets; source-public-domain basis distinguished from API database rights. No skill/occupation-to-SDG links inferred.
- **AI:** 20 source-backed cards across ILO, OECD, HBS consulting, METR computing and corrected A-Lab materials workflows. Exposure, observed capability/practice, study/model dates, disagreements and corrections remain distinct. OECD contextual findings retain their workforce source class; no occupation demand is inferred from them.
- **Workforce Radar:** deterministic `RISING`, `DECLINING`, `STABLE`, `INSUFFICIENT_DATA` with absolute/% changes, thresholds, source IDs/versions/excerpts, strict compatible populations/periods/units/classifications and fingerprints. Zero/missing values and unsupported sector shares abstain. Two observations never establish a sustained trend.
- **Independent AI attribute:** `AI-TRANSFORMING` requires reviewed observed task/capability evidence and occupation identity. Exposure/forecasts cannot activate it. Exact bridges for the acquired taxonomy are still unreviewed; real examples correctly retain insufficient evidence. Synthetic tests cover both rising+AI and declining+AI combinations.
- **Upload-first workflow:** select a programme → protected private PDF upload → existing separate worker → every extracted course candidate. Supported explicit year-column detection with manual-region fallback; original PDF/hash/page anchors persist atomically. Detailed syllabi are optional; no taught content is invented. Public discovery remains secondary.
- **Compatibility:** no extra migration beyond additive 0004; existing Phase 1–3 functions/history are preserved. Explicit CLI reference imports, offline synthetic fixtures and permitted genuine frozen ESCO/UN reference packs remain available. No default startup download or public external-evidence import endpoint.

Actual local environment: **Python 3.12 / PostgreSQL 16.15**, retained disposable `shiftos_phase3_validation` database on loopback port 55433. No existing application/user database was migrated, and no remote CI pass is claimed.

| Measured check | Actual result |
|---|---|
| Genuine PostgreSQL evidence | **75 registered datasets, 18 versions, 628 references; 38 occupations, 10 skills, 39 relationships; 247 workforce observations; 20 AI cards; 12 academic benchmarks; 186 SDGs** |
| Actual API/provenance queries | HTTP200 for all normalized categories, all 18 version provenance reads; SQL join count39 and all linked skills have descriptions |
| Genuine ESCO repeated import | SUCCEEDED87 normalized rows, then UNCHANGED0 new rows/same version |
| Real Accounting PDF API + worker, repeated | HTTP202;37 unreviewed candidates (12/14/6 by explicit Years1/2/3,5 elective-year unknown),0 verified titles,1 private PDF; second extraction/import UNCHANGED |
| Professionals Q1→Q2 2026 | 315,768→285,907; **DECLINING**, −29,861 (−9.4566%) at default 5% |
| Elementary Occupations Q1→Q2 2026 | 4,070→4,646; **RISING**, +576 (+14.1523%) at default 5% |
| Unclassified Q1→Q2 | **INSUFFICIENT_DATA**, published Q2 missing value preserved |
| Technicians/associate professionals policy demonstration | 93,987→86,512; −7.9532%; STABLE under explicit 10% threshold, DECLINING under default 5%; no statistical-significance claim |
| `python -m pytest -q --basetemp=.pytest-phase3-completion-release --tb=short` with explicit disposable `TEST_DATABASE_URL` | **487 passed, 0 failed, 0 skipped**, one upstream Starlette/httpx warning, 42.42s |
| PostgreSQL integration coverage in that suite | **8 tests passed**, including migration/history/loss guards and real pipeline → idempotent replay → API radar |
| `python -m ruff check .` / `python -m ruff format --check .` | **PASS**, 133 Python files formatted |
| `python -m pip check` | **PASS**, no broken requirements |
| `python -m alembic upgrade head --sql` | **PASS**, all four PostgreSQL revisions compile; no new migration beyond 0004 |
| `git diff --check` | **PASS** |

All real demand examples are broad occupation-group **advertising**, short-term only, not individual-role/skill demand, employment/hires or AI-causation. No genuine combined rising/declining+AI-transforming occupation result is claimed where identity bridges/detailed demand are missing. Human academic review and currentness checks are required before academic action.

Restricted originals and narrow internal research cards remain in ignored local storage with citations/rights notes; permitted ESCO/UN frozen subsets are in `data/reference_packs/`. These are genuine separately attributed data, not synthetic fixtures. The 76 automatic PDF pages remain unreviewed candidates. Real standalone occupational-task taxonomy rows remain zero; supported professional task text lives in AI cards rather than being fabricated.

Completion checks caught and corrected PDF persistence occurring before result validation, malformed/future comparison metadata, a workforce-study exposure/source-class mismatch and fixtures assuming the original 73-row registry. Targeted checks and the final 487-test PostgreSQL-enabled suite pass. Historical failed acquisition/import attempts remain observable; their corrected retries or manual alternatives do not erase source failures. The warning is an existing upstream deprecation, not an accepted test failure.

**Remaining source actions:** obtain a permitted current English ESCO export (operator's own wizard consent/email); secure TalentCorp written aggregation/network-use consent (Group notice §3.3, PDF page 10); review taxonomy-to-Malaysian occupation bridges, exact AI occupation associations, standard editions/applicability and full discipline coverage. Unsupported layouts/scans/detailed syllabi need explicit regions or reviewed JSON. Limited catalogue tokens are not full production identity/tenant controls; private/rights-limited data is not approved for unrestricted deployment.

At the Phase 3 completion and Phase 4 planning stop boundaries, no commit/push was performed. Subsequent explicit GitHub publication authorization is recorded above. Phase 3 functionality is preserved; Phase 4 implementation remains pending.

## Phase 2 delivered (historical handoff)

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

The research found 25 XMUM Main Courses sections/brochure links, inspected two actual DOSM JMI workbooks (Q1/Q2 2026), selected ESCO API responses and UN goals/targets, and catalogued cross-disciplinary standards/AI evidence. Registry validation checked IDs/columns/enum/URL syntax; remote availability and rights remain publisher-specific. Research-time `acquired_into_backend=No` is superseded by the explicitly scoped Phase 3 outcomes above and appended registry columns.

## Phase 1 preserved and historical verification

Phase 1 retains FastAPI/settings, SQLAlchemy/psycopg, UUID/UTC models, all eight application tables, source registry, original manual create/read APIs, offline fixture IDs/hashes/anchors and loss-preventing migrations. See [the migration audit](docs/15_PHASE1_MIGRATION_AUDIT.md).

Historical local Phase 1 result: **144 passed, 0 skipped**, PostgreSQL 16.15/Python 3.13; Uvicorn/PostgreSQL smoke and 12-course synthetic fixture re-import passed. Its Python 3.12/PostgreSQL 16 [CI run 39998532797](https://github.com/RikoHalim/shift-os/actions/runs/39998532797) succeeded for implementation `866df6c`. These historical results do not replace Phase 2 acceptance.

## Remaining limits

- Live provider acquisition must be verified on a permitted network with public DNS. A private gateway is not an excuse to weaken source restrictions; reviewed JSON remains available offline.
- Public marketing lists are not certified complete curricula. Shared MPU, course codes/credits, cohort, unstated semesters/classifications and actual syllabi require separate confirmation. No inferred obsolete/replacement verdicts exist.
- HTML structure changes can require parser review; no general PDF or JavaScript crawler is implemented. Phase 3 adds local operator-selected PDF regions for unreviewed candidate preparation; other layouts can still require transcription. Raw HTML hash changes may create a new revision even when titles are unchanged.
- Copyright/reuse permission is not inferred from public access or robots. Whole brochures/pages are not committed. Reviewed flags/manual hashes are operator assertions, not independent source authentication.
- Full production identity/access control, automatic scheduling/monitoring, backups and Docker Compose execution remain outside this local verification. New tokens govern new catalogue job writes only.
- Genuine bounded taxonomy/benchmark/SDG subsets are loaded; latest English taxonomy, full coverage and reviewed local bridges remain limited. Relevance/actions, scenarios/reports and frontend remain pending. No analysis accuracy is claimed.

## Unresolved organiser clarification — UNCONFIRMED

The user reports approval of institutional framing and exemption from CV uploads. No written response/date/channel/evidence was provided for replacing individual skills intake overall, person-to-role matching, or personalised learning pathways. SDGs and multiple scenarios are not assumed waived. See [the compliance matrix](docs/09_HACKATHON_COMPLIANCE.md).

Obtain in writing: “Can programme-level profiles, occupation alignment and institutional academic interventions replace individual-profile intake, person-to-role matching and personalised learning plans for Domain 1?” Record the exact response and evidence. This gap is preserved; no learner waiver was invented.

## Next recommended prompt and stop boundary

“Read AGENTS.md, STATUS.md, docs/19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md, the Phase 4 specification/prompt, Phase 3 report and workforce methodology. Implement the documented bounded Phase 4 proof: upload-first catalogue, every available course appearance, PostgreSQL primary retrieval with deterministic sufficiency/freshness gates, controlled approved external research on important gaps, original-source verification and permitted versioned cache, then one configured existing LLM over admitted evidence. Disclose/configure the actual single model and search provider; keep offline synthetic mode and explicit unavailable-provider outcomes. Preserve title-versus-syllabus limits, insufficient-evidence results, deterministic workforce maths and independent AI task evidence; retain source/rights/language/identity gaps. Add necessary migrations/tests, run targeted/full checks and a permitted genuine fallback smoke test, update STATUS with measured results/blockers and stop before Phase 5. Do not commit/push unless explicitly instructed.”

Historical Phase 2 stop: the user authorized its commit/push and main merge. The Phase 4 planning request authorized documentation only; subsequent GitHub publication authorization is recorded above. No Phase 4 implementation is authorized.

## Main merge verification — 2026-10-24

Merged Phase 2 implementation `0c0bc54` into `main`, preserving the feature branch and existing history. The earlier uncommitted local documentation revisions were saved in recoverable Git stash `codex-doc-revisions-before-phase2-merge`; they were not overlaid on the newer Phase 2 status/schema/API documents. All versioned repository folders are included in the merge, and the local virtual environment was updated from `requirements.lock` and the editable project.

- Current local suite: **295 passed, 6 skipped, 1 warning in 10.83s**. All six skipped tests require explicit PostgreSQL `TEST_DATABASE_URL`; the earlier 301-test PostgreSQL result above remains historical branch evidence, not a fresh database run.
- Ruff lint passed; formatting passed with 104 Python files already formatted.
- Dependency integrity check passed; PostgreSQL SQL generation passed for all three migrations. No application/user database migration was applied by this merge task.
- Read-only review of the migration, APIs, fetch boundary, worker/idempotency and Phase 1 compatibility found no merge blocker. Whitespace checks passed.
- Synchronising Git files does not import the earlier disposable validation database or perform live XMUM collection. The documented live-network/coverage limitations remain unchanged.
