# HTTP API contract - implemented foundation and future phases

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

This phase implements **create/read**, not PATCH/DELETE. A source registration does not fetch or verify external content. The local fixture CLI is not an HTTP upload/parser endpoint. No discovery, evidence import, analysis, actions or frontend API is registered by this phase.

All lists accept `limit` 1-100 (default 50), `offset` >=0 (default 0) and return `{items,total,limit,offset}` sorted by UUID. Course pages add `programme_revision_id`. `total` counts the full matching inventory, not one page. Every known course is retrievable across pages; page limit is not a programme cap. Course lists include compulsory/elective/unknown-type records and those without syllabi. No active revision yields an empty course page; creation requires a valid mutable active revision. A checksum-protected fixture revision refuses API additions with 409 to preserve its idempotent import contract. General course POST is not an import/upsert API: source deduplication/versioned ingestion belongs to Phase 2.

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

Responses retain original fields and add metadata. All records include `id`, `created_at`, `updated_at`, `is_synthetic`. Institutions/programmes/courses expose source references and computed `data_quality` (`synthetic`, `source_attributed`, `incomplete`; courses also `verified_catalogue`). Missing provenance remains incomplete, never implicitly verified. Course responses retain `programme_revision_id`, inventory anchor, extraction status and `detailed_syllabus_available`; a source pointer is not a detailed syllabus. `INVENTORY_ONLY`, `NORMALIZED_FIXTURE`, `NEEDS_REVIEW` are extraction states, not academic verdicts.

Error codes: `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `CONFLICT` (409), `DATABASE_UNAVAILABLE` (503), `METHOD_NOT_ALLOWED` (405), `INTERNAL_ERROR` (500). Validation details include location/type and generic `Invalid value`; submitted secrets are not echoed. Responses include `X-Request-ID`. Readiness checks connectivity only, not schema/coverage. Swagger `/docs` and `/openapi.json` expose exact typed schemas.

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
| 2 | `POST /institutions/{id}/discover`, `GET /catalogue/jobs/{job_id}`, `POST /programmes/{id}/imports`, `GET /programmes/{id}/coverage` | Bounded discovery/manual import, job status and verified coverage |
| 3 | `GET /evidence/sources`, `POST /evidence/imports`, `GET /evidence/snapshots` | Reuse the source registry; versioned evidence passages/dated snapshots |
| 4 | `POST /programmes/{id}/analyses`, `GET /analyses/{id}`, `/analyses/{id}/courses`, `/analyses/{id}/courses/{course_id}` | Whole-programme run and course drill-down |
| 5 | `GET /analyses/{id}/actions`, `POST /analyses/{id}/compare` | Supported primary action/alternatives including no change |
| 6 | `POST /analyses/{id}/scenarios`, `GET /analyses/{id}/report` | Reproducible scenario/review draft |

Resource paths above carry `/api/v1`; async activities return 202 and a job ID. Finalise later contracts in the authorised phase without removing compatible foundation routes. Future title-only results must expose `needs_syllabus_confirmation`, sources, dates, unknown taught content and `is_final_curriculum_verdict=false`. A proposed action is never an approved academic decision.
