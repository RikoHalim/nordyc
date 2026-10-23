# Relational data model - current foundation and later targets

## Implemented Phase 1 schema

All eight application tables use UUID primary keys, timezone-aware UTC `created_at`/`updated_at` and `is_synthetic`. PostgreSQL is the runtime target. Original migration `0001_foundation` and its seven tables are preserved; `0002_catalogue_sources` is additive.

| Table | Implemented fields and relationships |
|---|---|
| `institutions` | `name`, `country='MY'`; new nullable `website_url`, `source_id`, `source_locator` |
| `programmes` | Institution FK, `name`, optional `programme_code`, `academic_year`, `active_revision_id`; new nullable `level`, `discipline_key`, `canonical_url`, `source_id`, `source_locator` |
| `programme_revisions` | Programme FK, `version_label`, optional `effective_date`, `fixture_id`, `fixture_sha256`; unique programme/version; preserved snapshot boundary |
| `courses` | Revision FK, `course_name`, optional code/credits/year/semester/anchor; `course_type`, extraction status, syllabus availability; new nullable source FK/locator and `is_verified=false` |
| `documents` | Revision FK and optional same-revision course link, filename/kind/format, content hash/parser version, storage path/status, JSON metadata, upload timestamp |
| `document_anchors` | Document FK, exact excerpt/locator, optional page/paragraph/section/character offsets |
| `jobs` | Revision FK, kind/status, optional start/completion/error; storage only, no execution worker |
| `sources` | Publisher/title, URL, source kind, evidence class, license status, optional publication/observation/collection timestamps and content hash |

The relationship remains institution -> many programmes -> many revisions -> many courses. The active-revision composite FK prevents selecting another programme's revision. Documents' optional course links are constrained to the same revision. Existing anchors/IDs/hashes remain valid. There are no delete cascades erasing provenance.

`CourseType` retains `COMPULSORY|ELECTIVE|UNKNOWN`: `UNKNOWN` explicitly represents missing classification instead of inventing a compulsory/elective assertion. Course `year` and `semester` remain nullable positive integers; programme `academic_year` is an optional free-text catalogue label. Ambiguous year labels will need original-source preservation in Phase 2. No fixed discipline, university name or course-count limit is stored. Course codes remain non-unique because repeated codes/titles across contexts require review; import identity belongs to revision/source fingerprinting rather than global title deduplication.

## Provenance and validation

Evidence classes are `verified_university_fact`, `published_standard`, `occupation_requirement`, `dated_workforce_signal`, `dated_ai_capability`, `inference`, `synthetic_demo`. Classifying a source is metadata supplied by the caller; the API does not authenticate its publisher or inspect a URL.

Source creation requires publisher/title. Defaults are `source_kind='manual'`, `evidence_class='inference'`, `license_status='unknown'`. Nonsynthetic sources require an HTTP(S) URL. Synthetic sources require both `is_synthetic=true` and `evidence_class='synthetic_demo'`; one flag cannot silently stand for the other. Dates are optional timezone-aware timestamps; missing publication/measurement dates remain unknown. Content hash, when present, is 64 hexadecimal characters. Registry rows are not downloaded artifacts, evidence excerpts, access licences or completed evidence pipeline imports.

Catalogue `source_id` and `source_locator` remain nullable for backwards-compatible incomplete/synthetic records. Read schemas expose computed `data_quality`: `synthetic`, `source_attributed`, `incomplete`; courses also expose `verified_catalogue` when `is_verified=true`. A URL/link alone is not validation of actual syllabus content. API requests cannot set computed quality fields.

Course verification assertions require a nonsynthetic course, an existing nonsynthetic source classified `verified_university_fact`, and an exact locator. Validation also preserves synthetic lineage from source/parent records. The database prevents verified rows with missing provenance or synthetic course flags; cross-record source-class checks are enforced by the service. This is a caller-supplied catalogue assertion, **not independent automated verification**, and it never verifies taught outcomes or syllabus detail. Legacy source-less rows become `incomplete` or `synthetic`, never verified.

## Upgrade and safe rollback

Run `python -m alembic upgrade head` on a backed-up existing database. Migration `0002_catalogue_sources` creates only the new registry/columns/indexes/constraints. It does not drop the original tables, rewrite course IDs, or fabricate provenance. Existing courses default to `is_verified=false`; nullable additions preserve old data and immutable fixture checksums.

Downgrade to 0001 refuses when new source rows or added catalogue metadata would be lost. Export/preserve new metadata before a deliberately planned rollback; a guard failure is not permission to delete data. On a clean schema with no added metadata, migration tests may exercise downgrade/re-upgrade. Applying migrations and validating a live PostgreSQL database are separate from SQLite tests and offline SQL generation; STATUS records the actual evidence.

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

## Future enums (only evidence_class is implemented now)

- `evidence_class`: verified_university_fact, published_standard, occupation_requirement, dated_workforce_signal, dated_ai_capability, inference, synthetic_demo.
- `evidence_level`: title_only, description_available, detailed_syllabus, missing.
- `review_flag`: monitor, investigate, needs_syllabus_confirmation, insufficient_evidence, validated_action_candidate.
- `action_type`: no_change, revise_syllabus, redesign_or_consolidate, add_course_or_elective, workshops_and_industry_engagement, request_review.
- `decision_status`: proposed, under_review, accepted, rejected, deferred.

## Future ingestion constraints

- Unique `(institution_id, normalized programme name, source_identity)` cautiously (renames need review).
- Course uniqueness should prefer an official code + programme; avoid removing distinct titles repeated across years or elective tracks. Use source fingerprint for idempotent import.
- `source_id` may be nullable for explicit synthetic/incomplete records (Phase 1 exposes `data_quality`); verified claims cannot omit provenance.
- Store LLM extraction **candidate** separately from validated source-backed fact.
- Delete/retire source via snapshot status rather than silent irreversible loss.
