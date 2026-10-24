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

The preserved foundation implements **create/read**, not PATCH/DELETE. Source registration does not fetch or verify external content. Phase 2 adds curriculum jobs/imports/revision routes. Phase 3 adds read-only evidence routes/explicit CLI ingestion. Phase 4 adds protected analysis jobs/history below; Phase 5 adds separate protected career-alignment, action comparison and human-review resources. Pathways, scenarios and frontend remain future work.

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

Catalogue job POST routes, including PDF upload, require `X-Catalogue-Token` when `CATALOGUE_WRITE_TOKEN` is configured. Missing/wrong tokens return `NOT_AUTHORIZED` (401). With `APP_ENV=production`, an unset token disables those writes with `CATALOGUE_WRITE_DISABLED` (503). Development/test allow them without a token when none is configured. Preserved Phase 1 write routes retain their existing behavior. POST/PUT/PATCH bodies are bounded to 1 MiB before JSON decoding, including chunked requests, except the dedicated raw PDF route's 20 MB bound; exceeding the relevant limit returns `PAYLOAD_TOO_LARGE` (413).

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

## Phase 3 reference evidence APIs

The upload-first curriculum route is `POST /api/v1/programmes/{id}/curriculum-pdf` with a raw `application/pdf` body, optional official-host `source_url`, and optional `regions` JSON query (`page,x0,top,x1,bottom`). It queues an existing catalogue worker job and returns 202/JobRead; it does not parse documents in the request or analyse courses. The catalogue token/production guard applies. Only this route permits20MB; all other write routes retain 1 MiB. Wrong media returns415, malformed origin/regions/PDF returns422, oversized content413, and unsupported PDF layouts fail visibly on the queued job. Private originals and page anchors are retained; parsed titles remain unreviewed and syllabus detail unavailable.

Paths below are under `/api/v1/evidence`. All are GET; there is **no public ingestion trigger**. List responses use `{items,total,limit,offset}` with limits 1–100 and nonnegative offsets. Historical versions are returned unless filtered; missing taxonomy/standard/SDG imports return empty pages, not invented data. Read-only access does not imply public redistribution permission for stored source text; deployment operators must restrict access according to source rights.

| Routes | Purpose |
|---|---|
| `/datasets`, `/datasets/{id}`, `/datasets/{id}/versions`, `/datasets/{id}/jobs` | Registry metadata and actual ingestion/version status |
| `/versions/{id}`, `/versions/{id}/provenance` | Frozen registry/transform metadata, source, dates, hashes, record counts |
| `/references`, `/references/{id}`, `/references/{id}/provenance` | Exact source locators/excerpts, PDF candidate text/tables, review state and lineage |
| `/occupations`, `/occupations/{id}`, `/occupations/{id}/skills`, `/occupations/{id}/tasks`, `/skills` | Version-scoped occupation requirements and relationships |
| `/workforce-observations` | Dated historical indicators, values/units/periods, source pointers |
| `/ai-impact` | AI evidence subtype, supported statement, limitations and provenance |
| `/academic-standards` | Source-attributed benchmarks, no university teaching assertion |
| `/sdg-references` | Permitted official goals/targets; no skill mappings |
| `/ingestion-jobs`, `/ingestion-jobs/{id}`, `/ingestion-jobs/{id}/logs` | Durable per-dataset outcomes and diagnostics |
| `/workforce-trends?before_id=...&after_id=...` | Deterministic source-bound directional change, scope, limitations, policy and fingerprint |
| `/occupations/{id}/ai-transformation` | Independent reviewed task/capability attribute or insufficient evidence |

List filters include `dataset_id`, `version_id`, `is_synthetic` where applicable; registry has category; workforce has `indicator`, `classification_code`, `period_start`, `period_end`; AI has `impact_type`, `occupation_label`; standards have `discipline`; SDGs have `kind`, `goal_code`. OpenAPI gives exact parameter names/availability and typed response fields. Errors retain the existing shape. Review state is a supplied engineering assertion, not academic approval. See [the runbook](17_PHASE3_EVIDENCE_INGESTION.md) for CLI access controls, supported formats and manual/rights gates.

Radar accepts configurable finite nonnegative `percent_threshold` (default5, max1000) and `absolute_threshold` (default0, max10^18). Response classifications are `RISING`, `DECLINING`, `STABLE`, `INSUFFICIENT_DATA`; `AI-TRANSFORMING` is a separate nested attribute, never a fifth demand class. Results contain both full observations/version/source/reference inputs, exact decimal deltas, policy/method version, compatible dimensions and a reproducibility fingerprint. Results are computed without overwriting or adding source observations. Two-point comparisons never claim a sustained trend. Missing identities return404; invalid query values422; insufficient/incompatible observations return200 with explicit abstention/reasons. See [the methodology](18_WORKFORCE_TRENDS.md) for units/populations/periods and independent AI admission gates.

## Phase 4 analysis APIs — implemented bounded MVP

All routes below are under `/api/v1` and require `X-Analysis-Token`, compared against `ANALYSIS_WRITE_TOKEN`. Missing server configuration returns503; missing/wrong supplied token returns401 before resource lookup. This is an operator access boundary, not full tenant identity. The legacy `/catalogue/jobs/{id}` also applies this guard to analysis jobs, preserving curriculum job reads.

| Route | Behavior |
|---|---|
| `POST /programmes/{id}/analyses` | Queue and freeze a nonempty programme revision/inventory;202 with run/job identifiers; no provider work in request |
| `GET /programmes/{id}/analyses` | Paginated analysis history |
| `GET /analyses/{id}` | Job state/times, mode, request, frozen manifest, summary/insights, research outcomes, fingerprint and disclosed model/schema/prompt versions |
| `GET /analyses/{id}/courses` | Paginated findings for every available frozen course appearance |
| `GET /analyses/{id}/courses/{course_id}` | One owned course result with five dimensions, scoped citations, fixed review questions and limitations |

Submission accepts optional `revision_id`, optional bounded `idempotency_key`, `mode='live'|'offline'` (defaultlive), `research=true` and optional aware historical `as_of`. Unknown fields are rejected. Repeating identical intent/key returns the same run even when the active catalogue changes; changed intent/key returns409. Wrong/missing revision404, empty/inconsistent inventory409. The existing separate worker and `analyse-programme` CLI are described in [the runbook](21_PHASE4_COURSE_RELEVANCE.md).

Responses expose `needs_evidence_revalidation` and `evidence_access_limitations`; current permission-policy/source-state checks can withhold source text while preserving pointers/history. The run's `summary_json` contains deterministic counts/insights and `result_mode`; model/research processing outcomes remain distinct from source sufficiency. Offline genuine records disclose `deterministic_insufficiency`, synthetic fixtures `offline_synthetic`. Live processing failure yields visible partial/fallback outcomes, never a false model-success claim. No live Gemini/Brave verification occurred without keys.

Phase 4.1 preserves these routes, request/academic finding schemas and authorization. Provider/model selection is server configuration, never a client-supplied credential or endpoint. The existing run manifest additionally discloses selected provider/model, `model_processing.responses` (sanitized actual model, token usage, HTTP request count and validation/error status), explicit `fallbacks`, and `observed_cost: null`; actual billing reconciliation is external. `model_name` records returned models only. Preflight and the bounded synthetic Claude smoke are explicit CLI administration, not public HTTP triggers; [live Claude access is blocked here](23_PHASE41_REPLIT_CLAUDE.md).

`insufficient_evidence` dimensions display **INSUFFICIENT EVIDENCE**; title-only courses retain `needs_syllabus_confirmation` and `is_final_curriculum_verdict=false`. Citation validation checks exact associated admitted references, quotations, dates/scope/rights and curriculum evidence level. No relevance scores, definitive obsolete/replacement verdicts, academic actions or free-form factual claims are accepted. See OpenAPI for exact typed fields and [the retrieval design](19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md) for policy boundaries.

## Implemented Phase 5 career alignment and academic review

All Phase 5 routes require the existing `X-Analysis-Token`; absent/wrong access returns 401, unconfigured access 503. `POST /api/v1/programmes/{id}/career-analyses` accepts `CareerRequest` and returns 202 with frozen revision/cutoff and run/job IDs. Optional reviewed mappings/assertions/audits use existing database identifiers and exact permitted passages; an empty mapping request produces explicit insufficiency. Repeating the same idempotency key/payload returns the same run; changed content returns 409. Process with the existing separate CLI worker.

`GET /api/v1/programmes/{id}/career-analyses` lists history. `GET /api/v1/career-analyses/{id}` returns job state, validated matrix, recommendations, method/model metadata, source lineage and revalidation flags. Its `/occupations`, `/competencies`, `/recommendations` and `/evidence` children return typed pages with limits 1–100, offset, job state and source-access limitations. Pending/failed jobs are distinct from completed insufficient-evidence outcomes. Restricted/stale source prose is withheld without rewriting history.

`POST /api/v1/career-recommendations/{id}/reviews` requires `decision`, nonblank `reason` and exact `expected_recommendation_version` SHA256, returning 201. Decisions are `needs_evidence`, `under_review`, `approved`, `rejected`, `no_change_required`. The actor is assigned server-side as `authenticated_analysis_operator`; client-supplied actors are rejected. Approvals require current revision, permitted unchanged evidence and a completed run. `GET` on the same path returns append-only history. A recorded operator approval does not automatically modify curricula or independently identify an academic staff member. See [Phase 5](27_PHASE5_FUTURE_CAREER_ALIGNMENT.md) and generated OpenAPI for exact contracts.

The original planned `/analyses/{id}/actions` and `/compare` spellings were reconciled into these explicit career-run resources, keeping existing Phase 4 findings unchanged. Primary action, alternatives and no-change comparison are included in each recommendation rather than a separate model call or endpoint. No existing route was removed.

## Later endpoint targets - not implemented

| Phase | Proposed endpoints | Purpose |
|---|---|---|
| 6 | `POST /analyses/{id}/scenarios`, `GET /analyses/{id}/report` | Reproducible scenario/review draft |

Resource paths above carry `/api/v1`; async activities return 202 and a job ID. Finalise later contracts in the authorised phase without removing compatible foundation routes. Future title-only results must expose `needs_syllabus_confirmation`, sources, dates, unknown taught content and `is_final_curriculum_verdict=false`. A proposed action is never an approved academic decision.

### Historical alignment plan and pending pathway extension

The [planning revision](22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md) extends Phase 5 action/comparison responses with programme `career_alignment`, reviewed occupation/skill pointers, curriculum-supported competencies, requirement-level potential gaps, confidence/limitations and optional deterministic alignment calculation metadata. A title-only comparison must report unknown coverage. Any score requires method/version, weights, eligible denominator and missingness; it is not an employment probability.

Phase 5 responses will retain primary recommended intervention, alternatives including no change, minimum sufficient rationale, evidence conditions and human review. Phase 6 scenario/report responses will add ordered `academic_pathways`/Academic Action Plans with target competency, proposed objectives/activities, prerequisites, duration and basis, verified resources, occupational/evidence pointers and meaningful SDG links. Null/unknown duration or resource verification is preferable to invented values. No attendance-based technical competency attribution is allowed.

The Phase 5 portion is now implemented through the career resources above; Phase 6 pathway/scenario/report fields remain future requirements. Keep proposed intervention objectives separate from actual taught content and scenario assumptions separate from observed indicators. Source permissions, reproducibility, protected reads/writes and structured validation continue across phases. No standalone career or student platform is introduced.

Phase 4 currently supplies scoped citations, source/version/date/rights lineage, five dimensions, fixed coverage questions and deterministic programme context. Later competency support needs typed skill/concept assertions, reviewed mappings and `documented_intent`/`assessed_demonstration`/`unknown` states. This planning revision identifies those additions; it does not expand Phase 4 into recommendations, pathways or individual matching.
