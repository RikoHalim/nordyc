# Relational data model - current foundation and later targets

## Implemented Phase 1 and Phase 2 schema

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

## Future concepts - not implemented by this migration

Programme revisions already cover catalogue versioning; later phases should map snapshot requirements onto them before introducing a redundant snapshot table. Learning outcomes, descriptions, evidence passages, standards/skills/occupations, signal snapshots, analysis results, actions/reviews and SDG links are deferred. The following conceptual target is a planning contract, not a second required Phase 1 schema.

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
| `evidence_items` | id, source_id, excerpt, exact_locator, evidence_class, validation_status | Traceable quotes/passages and verified vs synthetic |
| `skills` | id, canonical_label, taxonomy, taxonomy_uri | Cross-major taxonomy |
| `occupations` | id, label, taxonomy_code, taxonomy | ESCO/MyNSR mapping, no employment probability |
| `occupation_skills` | occupation_id, skill_id, source_id, relationship, confidence_label | Evidence backed; don't infer from totals |
| `standards` | id, discipline_key, publisher, version, source_id | MQA benchmark by discipline |
| `standard_competencies` | id, standard_id, skill_id nullable, text, evidence_id | Normative benchmark, NOT taught claim |
| `workforce_signals` | id, occupation_id nullable, skill_id nullable, metric, value nullable, unit, geography, period_start, period_end, source_id | Occupation counts stay occupation counts |
| `ai_task_impacts` | id, occupation_id, task_text, impact_type, evidence_id, date_label, limitations | AI exposure != automation inevitability |
| `analysis_runs` | id, programme_id, curriculum_snapshot_id, workforce_snapshot_hash, scenario, model_name nullable, version, status, started_at | Reproducible input fingerprint |
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
