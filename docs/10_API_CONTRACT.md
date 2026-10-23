# HTTP API contract - implemented catalogue and future phases

JSON UTF-8, `/api/v1` resource prefix, UUID IDs and timezone-aware timestamps. Health endpoints are unprefixed. The preserved error envelope is `{ "error": { "code": "...", "message": "...", "details": [] } }`; shorthand `{code,message,details}` in older planning text refers to the inner object.

## Implemented Phase 1 endpoints

| Method | Path | Result |
|---|---|---|
| GET | `/health`, `/health/live` | 200 `{"status":"alive"}`, no DB |
| GET | `/health/ready` | 200 `{"status":"ready"}` after `SELECT 1`, structured 503 on DB failure |
| POST / GET | `/api/v1/institutions` | 201 created / 200 page |
| GET | `/api/v1/institutions/{id}` | 200 institution / 404 |
| POST / GET | `/api/v1/programmes` | Preserved 201 global create / 200 page |
| GET | `/api/v1/programmes/{id}` | 200 programme with active revision / 404 |
| POST / GET | `/api/v1/institutions/{id}/programmes` | 201 nested create / 200 institution programme page |
| POST / GET | `/api/v1/programmes/{id}/courses` | 201 active-revision course create / 200 active-revision inventory page |
| GET | `/api/v1/courses/{id}` | 200 course / 404 |
| POST / GET | `/api/v1/sources` | 201 metadata registration / 200 registry page |
| GET | `/api/v1/sources/{id}` | 200 source metadata / 404 |

The preserved foundation implements **create/read**, not PATCH/DELETE. Source registration does not fetch or verify external content. Phase 2 adds the curriculum jobs/imports/revision routes below. Workforce/standards/AI evidence ingestion, analysis, academic actions and frontend APIs remain future phases.

Academic resource lists accept `limit` 1-100 (default 50), `offset` >=0 (default 0) and return `{items,total,limit,offset}` sorted by UUID. Course pages add `programme_revision_id`. `total` counts the full matching inventory, not one page. Every known course is retrievable across pages; page limit is not a programme cap. Course lists include compulsory/elective/unknown-type records and those without syllabi. No active revision yields an empty course page; creation requires a mutable active revision. Checksum-protected fixtures and fingerprinted imported revisions refuse course additions with 409. General course POST creates one inventory entry; the Phase 2 import routes perform deduplication and versioned ingestion.

## Implemented Phase 2 endpoints

| Method | Path | Result |
|---|---|---|
| GET | `/api/v1/catalogue/providers` | 200 `{items:[{key,name,website_url,directory_url}]}`; currently `xmum` |
| POST | `/api/v1/catalogue/discover` | 202 discovery job; resolves/creates the configured official institution |
| POST | `/api/v1/institutions/{id}/discover` | 202 discovery job for an institution matching the provider; 409 on synthetic/mismatched lineage |
| POST | `/api/v1/institutions/{id}/imports` | 202 job for a structured JSON batch of programme manifests |
| POST | `/api/v1/programmes/{id}/imports` | 202 job for one structured programme manifest; URL/name must match its target |
| GET | `/api/v1/catalogue/jobs/{id}` | 200 durable job status/result, or 404 |
| GET | `/api/v1/programmes/{id}/coverage` | 200 selected revision coverage; optional `revision_id`; wrong/missing explicit revision returns 404 |
| GET | `/api/v1/programmes/{id}/revisions` | 200 `{items,total,limit,offset}` sorted by creation timestamp then UUID |
| GET | `/api/v1/programmes/{id}/revisions/{revision_id}/courses` | 200 historical course page; revision ownership checked, otherwise 404 |

Discovery bodies are `{"provider":"xmum","idempotency_key":"optional-request-key"}`; `{}` selects `xmum`. The HTTP request only persists a queue record. Start the separate worker with `python -m shiftos.cli worker` (or `worker --once` to process at most one eligible job). Live source retrieval is disabled until both `DISCOVERY_ENABLED=true` and `DISCOVERY_TERMS_REVIEWED=true` are configured. The fetcher still enforces official-host allowlists, HTTPS/public DNS, robots rules, response limits, rate limits and bounded retries. Failed policy/network/parser checks produce job failures with structured-import guidance; a 202 is not evidence of collection. No PDF or CSV upload endpoint is implemented.

Phase 2 POST routes require `X-Catalogue-Token` when `CATALOGUE_WRITE_TOKEN` is configured. Missing/wrong tokens return `NOT_AUTHORIZED` (401). With `APP_ENV=production`, an unset token disables those writes with `CATALOGUE_WRITE_DISABLED` (503). Development/test allow those routes without a token when none is configured. This protection covers the new enqueue routes; preserved Phase 1 write routes retain their existing behavior. All POST/PUT/PATCH request bodies are bounded to 1 MiB before JSON decoding, including chunked requests; exceeding it returns `PAYLOAD_TOO_LARGE` (413).

Jobs expose `id`, `institution_id`, nullable `programme_revision_id`, `kind`, `status`, `is_synthetic`, `created_at`, nullable `started_at`/`completed_at`/`error`, and `result`. States are `QUEUED`, `RUNNING`, `SUCCEEDED`, `PARTIAL`, `FAILED`. Result summaries report provider/directory provenance, discovered/imported/unchanged/failed programme counts, course/verified-title counts, missing-directory IDs, per-programme entries and limitations. Entry states include `discovered`, `imported`, `unchanged`, `historical`, `failed`, with nullable IDs, source URL, counts, `active`, `error_code` and `message`. A directory-only programme can have no revision and zero imported courses. Programme failures retain previous snapshots and do not erase successful imports from the same job.

Optional idempotency keys contain 1-100 letters/digits or `_.:-` and are scoped to institution plus job kind. Repeating the same key and payload returns the existing job; changed payload returns 409. A terminal failed job is not automatically requeued by repeating its key: submit a new key or omit it after resolving the limitation. Worker recovery is explicit via `python -m shiftos.cli fail-stale-jobs` for abandoned running jobs older than one hour. See [the Phase 2 handoff](16_PHASE2_CURRICULUM_INGESTION.md) for access policy and operation.

## Structured curriculum import contract

`POST /institutions/{id}/imports` accepts `CatalogueImport`: `is_synthetic=false`, optional `idempotency_key`, and 1-100 `programmes`. `POST /programmes/{id}/imports` accepts one programme manifest directly, plus those same two request fields. `python -m shiftos.cli import-curriculum PATH --institution UUID` queues the institution-batch JSON file with the same validation and a 1 MiB file limit. All values remain source assertions; manual import makes no network request.

| Manifest level | Fields and limits |
|---|---|
| Programme | Required `name` (1-255), `canonical_url`, `source_url`, `source_locator` (1-500), timezone-aware `retrieved_at`, and 1-1000 `courses`; optional 64-character lowercase-hex `content_hash`; `license_status='rights_unconfirmed'`, `reviewed=false`, `notes=[]` (at most 30 notes of 1-500 characters) |
| Course | Required `course_name` (1-255), `source_locator` (1-500) and `source_excerpt` (1-4000); optional `course_code`, `raw_year_label`, `raw_semester_label` (1-100 each), strict integer `year`/`semester` (1-100), nullable `elective_group` (at most 255); `course_type='UNKNOWN'`, `review_notes=[]` (at most 20 notes of 1-500 characters) |

Unknown fields are rejected. The course title must occur in its excerpt after whitespace/case normalization. Missing year/semester/type is retained as null/`UNKNOWN`; the importer does not infer it from a title. Retrieval dates more than five minutes in the future are rejected. Both source and canonical URLs must be HTTPS on the institution's official host, without embedded credentials or a nonstandard port. Import synthetic flags must match the institution. A batch cannot repeat the same canonical programme identity.

`reviewed=true` on a manual nonsynthetic manifest is a caller-supplied review assertion. It can produce `is_verified=true` for a catalogue title when no extraction warnings remain; it does not establish actual taught content. Unreviewed imports stay unverified. Placeholder/truncated/composite/bilingual-pairing/duplicate-conflict flags remain `NEEDS_REVIEW`. Synthetic manifests always remain synthetic and unverified. A supplied page hash is stored as asserted; without it the importer hashes validated manifest facts. Exact source locators are preserved separately from normalized manifest excerpt anchors.

Identical validated facts/parser/acquisition mode yield the existing revision without duplicate programmes/sources/courses. Changed facts create a new immutable revision. Replaying an existing older snapshot does not reactivate it, and a newly supplied older retrieval timestamp creates a historical snapshot. Exact duplicate source rows are skipped; distinct year/elective-group/locator appearances are preserved. These are curriculum inventory semantics, not course relevance results.

Coverage responses contain `programme_id`, nullable `programme_revision_id`, `course_count`, `verified_title_count`, `needs_review_count`, `title_only_count`, `is_synthetic`, `graduation_curriculum_complete=false`, and revision `metadata`. No active revision returns zero counts and an explicit no-import note. Coverage counts describe persisted records and cannot certify full graduation requirements.

## Create request fields

Unknown fields are forbidden. Trimmed names are required/nonblank, <=255 characters; short metadata strings <=100 and programme academic-year labels <=50. URLs use HTTP(S). IDs must be valid UUIDs; optional fields default to null unless stated otherwise.

| Resource | Fields |
|---|---|
| Institution | Required `name`; `is_synthetic=false`, optional `website_url`, `source_id`, `source_locator`; country fixed to `MY` |
| Programme | Required `name`; global route additionally requires `institution_id`, nested route takes it from path and rejects it in body; optional `programme_code`, `academic_year`, `effective_date`, `level`, `discipline_key`, `canonical_url`, `source_id`, `source_locator`; `version_label='initial'`, `is_synthetic=false` |
| Course | Required `course_name`; optional `course_code`, `credit_hours`, positive integer `year`/`semester`, `source_id`, `source_locator`; `course_type='UNKNOWN'`, `is_verified=false`, `is_synthetic=false` |
| Source | Required `publisher`, `title`; optional `url`, `published_at`, `observed_at`, `collected_at`, `content_hash`; `source_kind='manual'`, `evidence_class='inference'`, `license_status='unknown'`, `is_synthetic=false` |

Programme creation atomically creates/selects an initial revision. Synthetic parent/source lineage stays synthetic. Course creation creates inventory-only records, without taught content or syllabus evidence. Course type is `COMPULSORY|ELECTIVE|UNKNOWN`; omitted classification stays `UNKNOWN` for compatibility. Nonnegative `credit_hours` has at most six digits/two decimals and serializes as a decimal string. Effective dates are `YYYY-MM-DD`; source timestamps require timezone information. Content hashes are exactly 64 hexadecimal characters. No dates are guessed.

Nonsynthetic sources require an origin URL. Synthetic registry records require both `is_synthetic=true` and `evidence_class='synthetic_demo'`; inconsistent flags fail validation. Seven evidence classes are listed in docs 03. Missing source IDs return 404. Source/locator are required for `is_verified=true`, and the referenced source must be nonsynthetic `verified_university_fact`; unsupported verification is refused. This is a caller-supplied catalogue assertion, not an autonomous check of university facts.

## Read fields and error contract

Responses retain original fields and add metadata. All records include `id`, `created_at`, `updated_at`, `is_synthetic`. Institutions/programmes/courses expose source references and computed `data_quality` (`synthetic`, `source_attributed`, `incomplete`; courses also `verified_catalogue`). Missing provenance remains incomplete, never implicitly verified. Course responses retain `programme_revision_id`, inventory anchor, extraction status and `detailed_syllabus_available`; they add raw year/semester labels, elective group, source URL, review notes, computed `evidence_level` (`title_only`, or `synthetic_detail`/`detailed_syllabus` for synthetic/nonsynthetic records marked as having detail) and `missing_fields`. Those missing-field labels cover absent code/year/semester, unknown course type and unavailable syllabus. `INVENTORY_ONLY`, `NORMALIZED_FIXTURE`, `NEEDS_REVIEW` are extraction states, not academic verdicts. Public course imports set `detailed_syllabus_available=false`.

HTTP error codes: `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `CONFLICT` (409), `NOT_AUTHORIZED` (401), `CATALOGUE_WRITE_DISABLED` (503), `PAYLOAD_TOO_LARGE` (413), `DATABASE_UNAVAILABLE` (503), `METHOD_NOT_ALLOWED` (405), `INTERNAL_ERROR` (500). Validation details include location/type and generic `Invalid value`; submitted secrets are not echoed. Source fetch/extraction errors after acceptance appear in the job outcome/error, rather than changing its earlier 202 response. Responses include `X-Request-ID`. Readiness checks connectivity only, not schema/coverage. Swagger `/docs` and `/openapi.json` expose exact typed schemas.

## Offline create/read example

Create a synthetic institution and use its returned ID in the nested route (replace the placeholder):

```json
{"name":"Synthetic Multi-disciplinary University (DEMO ONLY)","is_synthetic":true}
```

`POST /api/v1/institutions/{id}/programmes`:

```json
{"name":"Synthetic Marine Science (DEMO ONLY)","level":"undergraduate","discipline_key":"marine_science","is_synthetic":true}
```

`POST /api/v1/programmes/{id}/courses`:

```json
{"course_name":"Synthetic Coastal Systems (DEMO ONLY)","year":2,"is_synthetic":true}
```

This creates no verified institution/course facts and requires no source fetch or API key. Use returned IDs, not invented factual university records.

## Later endpoint targets - not implemented

| Phase | Proposed endpoints | Purpose |
|---|---|---|
| 3 | `GET /evidence/sources`, `POST /evidence/imports`, `GET /evidence/snapshots` | Reuse the source registry; versioned evidence passages/dated snapshots |
| 4 | `POST /programmes/{id}/analyses`, `GET /analyses/{id}`, `/analyses/{id}/courses`, `/analyses/{id}/courses/{course_id}` | Whole-programme run and course drill-down |
| 5 | `GET /analyses/{id}/actions`, `POST /analyses/{id}/compare` | Supported primary action/alternatives including no change |
| 6 | `POST /analyses/{id}/scenarios`, `GET /analyses/{id}/report` | Reproducible scenario/review draft |

Resource paths above carry `/api/v1`; async activities return 202 and a job ID. Finalise later contracts in the authorised phase without removing compatible foundation routes. Future title-only results must expose `needs_syllabus_confirmation`, sources, dates, unknown taught content and `is_final_curriculum_verdict=false`. A proposed action is never an approved academic decision.
