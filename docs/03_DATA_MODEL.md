# Relational data model - current foundation and later targets

## Implemented Phase 1 and Phase 2 schema

Additive Phase 5 migration **`0006_career_alignment`** adds `career_runs`, `career_recommendations`, and `career_reviews`. Runs reference existing programme/revision/job identities and store frozen requests, source/policy hashes, method/schema/model lineage and validated results. Recommendation rows reference their exact run/revision and a content-version hash. Composite review foreign keys bind decision, server-authenticated actor, reason and timestamp to that exact recommendation version. Completed runs and recommendation/review history are immutable through ORM checks and PostgreSQL triggers; populated downgrade refuses data loss. Existing tables and migrations are preserved. See [Phase 5](27_PHASE5_FUTURE_CAREER_ALIGNMENT.md) for contracts and practical limits.

All eight application tables use UUID primary keys, timezone-aware UTC `created_at`/`updated_at` and `is_synthetic`. PostgreSQL is the runtime target. Original migration `0001_foundation` and its seven tables are preserved; additive `0002_catalogue_sources` adds source attribution, and `0003_curriculum_ingestion` extends those tables for versioned curriculum imports and durable jobs. No separate curriculum snapshot table was introduced.

| Table | Implemented fields and relationships |
|---|---|
| `institutions` | `name`, `country='MY'`; nullable `website_url`, `source_id`, `source_locator` |
| `programmes` | Institution FK, `name`, optional `programme_code`, `academic_year`, `active_revision_id`, `level`, `discipline_key`, `canonical_url`, source FK/locator; new nullable `ingestion_key` |
| `programme_revisions` | Programme FK, `version_label`, optional `effective_date`, `fixture_id`, `fixture_sha256`; new nullable `import_fingerprint` and nonnull `metadata_json` |
| `courses` | Revision FK, title, optional code/credits/year/semester/anchor, type/extraction status/syllabus flag, source FK/locator and `is_verified`; new nullable `raw_year_label`, `raw_semester_label`, `elective_group`, `source_url`, and nonnull `review_notes` |
| `documents` | Revision FK and optional same-revision course link, filename/kind/format, content hash/parser version, storage path/status, JSON metadata, upload timestamp |
| `document_anchors` | Document FK, exact excerpt/locator, optional page/paragraph/section/character offsets |
| `jobs` | Nullable revision FK and new nullable institution FK; kind/status/timestamps/error; new optional `idempotency_key` and nonnull `payload_json`, `result_json`; separate CLI worker processes curriculum jobs |
| `sources` | Publisher/title, URL, source kind, evidence class, license status, optional publication/observation/collection timestamps and content hash |

The relationship remains institution -> many programmes -> many revisions -> many courses. The active-revision composite FK prevents selecting another programme's revision. Documents' optional course links are constrained to the same revision. Existing anchors/IDs/hashes remain valid. There are no delete cascades erasing provenance.

`CourseType` retains `COMPULSORY|ELECTIVE|UNKNOWN`: `UNKNOWN` represents missing classification. Course `year` and `semester` remain nullable positive integers; programme `academic_year` is an optional free-text catalogue label. Phase 2 preserves explicit raw labels: `Year 3/4` can have `year=null` and `raw_year_label='Year 3/4'`. A shared elective pool has no course-year assignment unless the source states one. Programme discovery is not restricted to a hardcoded list of disciplines. Course codes and titles remain non-unique across year, programme and choice-group contexts.

The new `programme_revisions.metadata_json`, `courses.review_notes` and `jobs.payload_json`/`result_json` columns use PostgreSQL **JSONB**; ORM SQLite tests use JSON variants. Empty object/list defaults preserve existing rows without inventing a retrieval date, import fingerprint, source URL or extraction result. Existing document metadata keeps its previous JSON representation.

## Curriculum identity, snapshots and job execution

Programme ingestion uses a canonical URL hash (`ingestion_key`) unique within an institution. URL identity normalizes the `www` alias and trailing slash, preserves query strings and drops fragments. Existing manually created records can be matched by URL, or by an exact case-insensitive name when they lack a URL; ambiguous matches are refused. Real and synthetic institution/import lanes must agree. Imported canonical/source URLs require HTTPS on the institution's official host, without credentials or a nonstandard port.

Revisions keep unique `(programme_id, version_label)` and add unique `(programme_id, import_fingerprint)`. The SHA256 fingerprint covers validated normalized manifest facts, parser version, acquisition mode and synthetic flag; retrieval time alone does not create another snapshot. An identical import returns its existing revision. Replaying an older revision does not reactivate it over a newer one; newly supplied evidence with an older retrieval timestamp is stored as historical. Imported revisions reject course additions through the manual course API. Exact duplicate rows within a manifest are skipped; distinct years/groups/locators are retained. Conflicting facts at the same locator and repeated equivalent entries at different locators receive review warnings.

Revision metadata records the programme name/canonical URL, source ID/URL/locator, retrieval timestamp, parser version, acquisition mode, review assertion, limitations, duplicate count and course count. `effective_cohort` remains unknown and `graduation_curriculum_complete=false`. A public Main Courses list establishes no complete graduation curriculum.

Jobs require at least one revision or institution target. Curriculum jobs use `CURRICULUM_DISCOVERY` or `CURRICULUM_IMPORT`, with request JSON and persisted result/progress JSON. Optional request keys are unique by `(institution_id, kind, idempotency_key)`; reuse with a different payload is rejected. PostgreSQL row locks serialize imports per institution. A separate worker claims queued work with `SKIP LOCKED`, commits `RUNNING`, then fetches outside the request transaction and commits one programme at a time. Jobs finish `SUCCEEDED`, `PARTIAL` or `FAILED`; per-programme outcomes retain failures and manual-import guidance. Explicit stale-job recovery fails abandoned jobs older than one hour. Writes check that the owning job is still running, preventing a recovered stale worker from continuing to persist results. See [the Phase 2 handoff](16_PHASE2_CURRICULUM_INGESTION.md) for operation and replay.

## Provenance and validation

Evidence classes are `verified_university_fact`, `published_standard`, `occupation_requirement`, `dated_workforce_signal`, `dated_ai_capability`, `inference`, `synthetic_demo`. General source registration remains caller-supplied metadata and performs no fetch. The Phase 2 worker can acquire official curriculum HTML under its explicit provider/access policy; structured manual imports instead retain a caller-supplied review assertion and do not fetch their URLs.

Source creation requires publisher/title. Defaults are `source_kind='manual'`, `evidence_class='inference'`, `license_status='unknown'`. Nonsynthetic sources require an HTTP(S) URL. Synthetic sources require both `is_synthetic=true` and `evidence_class='synthetic_demo'`; one flag cannot silently stand for the other. Dates are optional timezone-aware timestamps; missing publication/measurement dates remain unknown. Content hash, when present, is 64 hexadecimal characters. Registry rows are not downloaded artifacts, evidence excerpts, access licences or completed evidence pipeline imports.

Catalogue `source_id` and `source_locator` remain nullable for backwards-compatible incomplete/synthetic records. Read schemas expose computed `data_quality`: `synthetic`, `source_attributed`, `incomplete`; courses also expose `verified_catalogue` when `is_verified=true`. A URL/link alone is not validation of actual syllabus content. API requests cannot set computed quality fields.

Course verification assertions require a nonsynthetic course, an existing nonsynthetic source classified `verified_university_fact`, and an exact locator. Validation preserves synthetic lineage from source/parent records. The database prevents verified rows with missing provenance or synthetic flags; cross-record source-class checks are enforced by the service. In the import path, reviewed nonsynthetic manifests may produce verified **catalogue titles** when no extraction warnings remain. `title_only` and `needs_syllabus_confirmation` are informational caveats; unresolved elective placeholders, suspected truncation, bilingual pairing, composite labels and conflicting/duplicate source occurrences require review. An unreviewed manual manifest stays unverified. No course import establishes taught outcomes or syllabus detail. Legacy source-less rows remain `incomplete` or `synthetic`.

For curriculum imports, a source version is identified by canonical source URL, content hash, evidence class and licence status. Live HTML uses the fetched-byte SHA256; a manual manifest may supply that hash, otherwise the importer hashes its validated facts. Supplied manual hashes are not independently checked against the remote page. Source observation/collection dates record the initial retrieval for that version; repeated imports do not rewrite history. Publication dates remain unknown unless separately registered.

Each new imported revision creates normalized document metadata and course excerpts, without storing/redistributing the full source HTML or PDF. `documents.content_sha256` hashes the validated manifest facts. An anchor such as `/courses/0/source_excerpt` addresses the normalized manifest, with `section_label` explaining that scope; the course separately preserves the **full official `source_locator`** and `source_url`. Locators are not silently truncated. An exact source excerpt and URL/locator establish a title pointer, not a licence or detailed syllabus.

## Upgrade and safe rollback

Run `python -m alembic upgrade head` on a backed-up existing database. Additive migrations `0002_catalogue_sources` and `0003_curriculum_ingestion` preserve original tables, IDs, fixture checksums and populated rows. The former adds source attribution; the latter adds the Phase 2 fields, unique identities, institution job FK/index and an at-least-one-job-target constraint. Legacy job revision references remain valid while the column becomes nullable for institution discovery jobs.

Downgrade from 0003 to 0002 refuses populated ingestion keys/fingerprints, revision metadata, course extraction metadata or institution job keys/payloads/results. Downgrade from 0002 to 0001 separately refuses source records or attribution metadata loss. Export/preserve data before a deliberately planned rollback; a guard failure is not permission to delete it. Empty/default-only new fields allow a safe migration roundtrip. PostgreSQL tests verify populated 0002 preservation, each new metadata guard, migrated-schema imports and historical API retrieval; [STATUS](../STATUS.md) records actual results.

## Implemented Phase 3 reference evidence

Additive `0004_reference_evidence` introduces 13 UUID/UTC/synthetic-aware tables. Existing `sources` is reused; no catalogue source/history is replaced. PostgreSQL JSONB fields use JSON variants in isolated SQLite tests.

| Table | Snapshot/provenance contract |
|---|---|
| `datasets` | Unique research registry key, name/category, full registry metadata; registration does not establish acquisition |
| `dataset_versions` | Dataset/source FKs, original input SHA256, parser/context hashes, artifact URL, UTC retrieval, raw publication-date precision and immutable metadata; unique dataset/hash/parser/context |
| `evidence_references` | Version FK, unique locator, excerpt, optional positive page, review status and candidate extraction metadata |
| `occupations`, `skills` | Version/evidence FKs, provider external IDs, taxonomy, labels/descriptions; occupation classification code nullable |
| `occupation_skills`, `occupational_tasks` | Version-local occupation/skill FKs and published relation/task text; no guessed crosswalks |
| `workforce_observations` | Population/classification/sector/geography, observation start/end, metric, nullable decimal value, unit, missing-value status and limitations |
| `ai_impact_evidence` | Occupation label/optional FK, task, statement, impact subtype, capability, limitations and study-period text |
| `academic_standards` | Discipline/title/benchmark statement/code; no university teaching claim |
| `sdg_references` | Official goal/target identifiers and text when permitted; no automatic skill-to-SDG relationship |
| `evidence_ingestion_jobs`, `evidence_processing_logs` | Separate reference-import outcomes/counts/errors and processing diagnostics; existing curriculum jobs require an institution/revision |

Every normalized fact has a version/evidence pointer; composite FKs enforce evidence and linked occupations/skills belong to the same version. Exact record identity is unique within the version. Publication strings preserve unknown/year-only/prose rather than inventing a day; observation periods use separate dates. Original file retrieval time is not publication. Parser validation enforces source evidence classes and AI subtype/limitations. API consumers must distinguish engineering review assertions from independent academic verification.

PDF extraction writes page candidates/text/tables to references, not automatic standards or AI findings. Narrow reviewed-card imports create their own checksum/version and retain original document hashes/pages and review basis in metadata. Replaying unchanged bytes/context returns the original version; source changes preserve old rows. Downgrade refuses populated Phase 3 data loss. See [the runbook](17_PHASE3_EVIDENCE_INGESTION.md) for supported adapters and unmatched classification behavior.

Phase 3 completion reuses these tables: workforce radar calculations are read-only derived responses referencing exact observation IDs, input versions, method/threshold policy and fingerprints; no analysis/result table is introduced before Phase4. AI transformation reads reviewed task evidence independently and never rewrites occupational demand. The existing `jobs` kind `CURRICULUM_PDF_UPLOAD` queues private originals; the worker atomically writes the existing curriculum revision/course inventory, a `documents` PDF record with hash/private storage metadata, and page anchors. Catalogue evidence remains unreviewed/inference unless separately confirmed. No additional migration beyond0004 is necessary. Original Source evidence classes remain intact, including OECD workforce-derived exposure context rather than invented AI capability.

## Implemented Phase 4 persistence

Additive `0005_programme_analysis` adds three tables and preserves Phase 1–3 data/schema. Reuse existing sources/datasets/versions/references and typed evidence for permitted findings; same-version FKs and explicit reviewed identity bridges remain intact. See the [operational contract](21_PHASE4_COURSE_RELEVANCE.md).

| Table | Implemented contract |
|---|---|
| `analysis_runs` | Institution/programme/revision and unique existing job FK; mode, request JSON, frozen inventory/evidence/policy manifest, deterministic summary/insights, research outcomes, fingerprint and model/prompt/schema versions |
| `course_findings` | Unique run/course; composite run+revision and course+revision FKs prevent cross-revision associations; validated structured result JSON and synthetic lineage |
| `research_cache` | Unique policy/scope-derived cache key, policy SHA256, bounded operational/source-version metadata JSON, UTC expiry and synthetic lane; no unrestricted research-text cache |

Existing `jobs` queues `PROGRAMME_ANALYSIS` with the institution/revision target and existing state/times/idempotency. The worker validates exact frozen course coverage and publishes results/terminal state atomically with running-job fencing. Refresh creates a new run; existing fact-version identity stays unchanged. Cache hits preserve original evidence dates. Protected reads detect changed/unknown permission policy or rejected/withdrawn/corrected source status and withhold text/flag revalidation without rewriting frozen findings. Unknown rights allow pointers, not content/model sharing. Populated downgrade refuses data loss.

Phase 4.1 reuses `analysis_runs.manifest_json.model_processing` for sanitized per-invocation provider, requested/actual model, token usage, HTTP-attempt counts, validation outcomes and explicit fallback transitions. `model_name` holds only actual returned model identifiers. Observed billing cost remains null without a billing observation. Existing job/result JSON and protected retrieval expose this metadata; no table, migration or academic finding-schema change is required. See [the Claude runbook](23_PHASE41_REPLIT_CLAUDE.md).

## Original Phase 5–6 conceptual plan

The Phase 5 subset below is now implemented through the three career tables described above and typed versioned JSON, rather than duplicating taxonomy/skill/source records. Detailed pathway/resource/SDG/scenario concepts remain Phase 6 plans. The following paragraphs retain the original planning context; [Phase 5's measured record](27_PHASE5_FUTURE_CAREER_ALIGNMENT.md) is the implementation authority.

The [career alignment/pathway plan](22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md) adds future concepts around the implemented run/evidence boundary. Programme–occupation alignment must link reviewed occupation/skill IDs, requirement sets, curriculum competency assertions and source versions. Competency support distinguishes documented intent, actual assessed demonstration and unknown coverage; title matches never populate verified support. Optional score records need method/weight/denominator/unknown-state provenance and abstention.

Future actions/comparisons/reviews link the primary minimum sufficient intervention, alternatives/no change, conditions and human decisions to the analysis/alignment evidence. Ordered pathway steps additionally need target competency, proposed objectives/activities, supported prerequisites, duration plus basis, verified resource/access/cost dates, requirement/evidence references and justified SDG target links. Scenario assumptions stay separate from observed workforce rows. Map these concepts onto existing JSON/version/run boundaries before adding tables; no Phase 5/6 migration is introduced by this planning revision.

Programme revisions already cover catalogue versioning; later phases should reuse them before introducing a redundant snapshot table. Phase 3 implements standards, skills, occupations, dated signals, source passages and SDG references; Phase 4 implements analysis runs/course findings. Additional competency-support mapping, academic actions/reviews, ordered pathways and justified SDG relationships remain deferred. The concept map below includes existing and later concepts and is not a second required schema or a claim that every listed field already exists.

### Future minimum relational concepts

Use surrogate UUID primary keys, TIMESTAMPTZ UTC timestamps, source references and migrations. Exact SQL choices are implementation details; these are the required concepts.

| Entity | Important fields | Notes |
|---|---|---|
| `institutions` | id, name, country, verified_url | Malaysia now, many institutions later |
| `programmes` | id, institution_id, official_name, level, discipline_key, canonical_url, catalog_version | One school has many programmes |
| `courses` | id, programme_id, official_title, course_code nullable, year nullable, semester nullable, type nullable, source_id, source_locator, is_verified | Course code optional; repeated names in different programmes allowed |
| `curriculum_snapshots` | id, programme_id, observed_at, source_version/hash, completeness_notes | Historical evidence and idempotent imports |
| `course_descriptions` | id, course_id, content, claim_type, evidence_id | Description and syllabi optional and must have origin |
| `sources` | id, publisher, title, url, license_status, source_kind, published_at, observed_at, collected_at, content_hash | Distinguish missing dates |
| `analysis_runs` | id, programme_id, programme_revision_id, evidence_manifest, gaps, as_of, policy/model/prompt/schema versions, status, started_at | Frozen input/result lineage; model absence explicit; scenarios remain Phase 6 |
| `course_findings` | id, run_id, course_id, finding_type, level, rationale, evidence_ids, missing_evidence | Clearly provisional with title-only |
| `programme_findings` | id, run_id, theme, rationale, evidence_ids, missing_evidence | Cross-course analysis; do not hallucinate gaps |
| `academic_actions` | id, run_id, course_id nullable, action_type, proposed, rationale, source_ids, conditions, decision_status | Includes programme-level elective and no change |
| `action_comparisons` | id, run_id, option_id, scenario, feasibility_assumptions, relative_disruption, risks | No invented absolute outcome projections |
| `reviews` | id, academic_action_id, reviewer_label nullable, status, reviewed_at, notes | Human approval; demo synthetic label |
| `sdg_links` | id, target_entity, sdg_goal, rationale, source_id | No token badges |

## Later analysis vocabulary

`evidence_class` is already persisted; Phase 2 course reads compute `evidence_level` as `title_only`, or `synthetic_detail`/`detailed_syllabus` for existing synthetic/nonsynthetic records marked as having detail. Public Phase 2 imports always set detail availability false. The broader analysis vocabulary below remains a later-phase target.

- `evidence_class`: verified_university_fact, published_standard, occupation_requirement, dated_workforce_signal, dated_ai_capability, inference, synthetic_demo.
- `evidence_level`: title_only, description_available, detailed_syllabus, missing.
- `review_flag`: monitor, investigate, needs_syllabus_confirmation, insufficient_evidence, validated_action_candidate.
- `action_type`: no_change, revise_syllabus, redesign_or_consolidate, add_course_or_elective, workshops_and_industry_engagement, request_review.
- `decision_status`: proposed, under_review, accepted, rejected, deferred.

## Future ingestion constraints

Phase 2 already implements institution-scoped URL identities, source/revision fingerprints and immutable replay. The following points guide later evidence and analysis extensions.

- Unique `(institution_id, normalized programme name, source_identity)` cautiously (renames need review).
- Course uniqueness should prefer an official code + programme; avoid removing distinct titles repeated across years or elective tracks. Use source fingerprint for idempotent import.
- `source_id` may be nullable for explicit synthetic/incomplete records (Phase 1 exposes `data_quality`); verified claims cannot omit provenance.
- Store LLM extraction **candidate** separately from validated source-backed fact.
- Delete/retire source via snapshot status rather than silent irreversible loss.
