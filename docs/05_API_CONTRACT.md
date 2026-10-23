# 05 — Proposed HTTP API Contract (v1)

API prefix `/api/v1`. OpenAPI must expose request/response models. Prefer resource IDs and long-running `analysis_run` objects over blocking HTTP. Error shape in architecture doc. Implement incrementally per phase; this contract is a target, not a claim it already exists.

| Method | Path | Purpose / phase |
|---|---|---|
| `GET` | `/health/live` | Process health, Phase 01 |
| `GET` | `/health/ready` | DB connectivity; 503 if DB unavailable, Phase 01 |
| `POST` | `/api/v1/institutions` | Create institution, Phase 01 |
| `POST` | `/api/v1/programmes` | Create programme; link institution, Phase 01 |
| `GET` | `/api/v1/programmes/{id}` | Programme metadata and revision, Phase 01 |
| `GET` | `/api/v1/programmes/{id}/courses` | **All** extracted courses (paginated), Phase 01/02 |
| `POST` | `/api/v1/programmes/{id}/documents` | Multipart upload one or multiple files, Phase 02 |
| `POST` | `/api/v1/programmes/{id}/ingestions` | Start programme-wide extraction job, Phase 02 |
| `GET` | `/api/v1/ingestions/{id}` | Ingestion state, counts, review flags, Phase 02 |
| `POST` | `/api/v1/evidence/sources/import` | Import versioned source records, Phase 03 |
| `POST` | `/api/v1/evidence/snapshots` | Construct dated snapshot from validated passages, Phase 03 |
| `GET` | `/api/v1/evidence/snapshots` | List available evidence snapshots, Phase 03 |
| `POST` | `/api/v1/programmes/{id}/analyses` | Trigger analysis of **all** programme courses, Phase 04 |
| `GET` | `/api/v1/analyses/{id}` | Status, course counts, source versions, warnings, Phase 04 |
| `GET` | `/api/v1/analyses/{id}/courses` | Per-course results incl. `INSUFFICIENT_EVIDENCE`, Phase 04 |
| `GET` | `/api/v1/analyses/{id}/courses/{course_id}` | Course drilldown, Phase 04 |
| `GET` | `/api/v1/analyses/{id}/recommendations` | Programme and course-level primary + alternatives, Phase 05 |
| `POST` | `/api/v1/analyses/{id}/scenario-comparisons` | Moderate/accelerated comparison, Phase 06 |
| `GET` | `/api/v1/analyses/{id}/report` | Academic report JSON, Phase 06 |
| `POST` | `/api/v1/recommendations/{id}/review` | Faculty review state; require explicit actor label; Phase 06 |

## Example trigger request

```json
{
  "signal_snapshot_id": "<existing snapshot UUID>",
  "scenario": "MODERATE",
  "analysis_mode": "ALL_COURSES"
}
```

`ALL_COURSES` should be fixed for programme-level runs in the MVP. If a single-course reanalysis endpoint is later introduced, it is an **optional drilldown**, not the primary programme path.

## Example run response shape

```json
{
  "id": "<run UUID>",
  "programme_id": "<programme UUID>",
  "job_status": "SUCCEEDED",
  "programme_course_count": 12,
  "analysed_course_count": 12,
  "sufficient_evidence_count": 8,
  "insufficient_evidence_count": 4,
  "signal_snapshot_id": "<snapshot UUID>",
  "generated_at": "2026-10-23T12:00:00Z",
  "is_demo": true
}
```

Counts above are *format examples*, not actual university results. Use actual counts from data. `analysed_course_count` includes insufficient-evidence results. A job can be `PARTIAL` when parsers/LLM fail for subsets; expose errors per document/course.

## Contract behaviours

- Use 201 on resource creation, 202 for accepted async jobs, 400/422 invalid requests, 404 missing IDs, 409 incompatible state/conflict, 503 readiness down.
- Pydantic request validation; ORM data returned through response schemas, not raw models.
- Pagination on programme course listings and run results; tests verify all pages cover full inventory.
- Upload filenames sanitized, path traversal rejected. Strict MIME/extension checks and size limit.
- Each course result includes `evidence_status`, citations/anchors, caution notes and `is_demo`/synthetic source indicators.
- New evidence snapshot never mutates old analysis results; re-run returns a new ID.
- If output needed to demonstrate a recommendation but no authentic inputs are available, use **explicit `demo` fixtures**, not silently fabricated evidence.

## Implemented Phase 01 contract

This section specifies the current foundation. The earlier phase roadmap and analysis-run examples remain targets for later work. UUID and timestamp strings below are shape placeholders; use IDs returned by the API or importer. Timestamps are timezone-aware UTC ISO-8601 strings. Every resource response includes an explicit `is_synthetic` boolean.

| Method | Implemented path | Success |
|---|---|---|
| `GET` | `/health/live` | 200, `{"status":"alive"}`; no database connection |
| `GET` | `/health/ready` | 200, `{"status":"ready"}` after `SELECT 1`; 503 on DB failure |
| `POST` | `/api/v1/institutions` | 201, institution object |
| `GET` | `/api/v1/institutions` | 200, paginated institution objects |
| `POST` | `/api/v1/programmes` | 201, programme object with initial active revision |
| `GET` | `/api/v1/programmes` | 200, paginated programme objects |
| `GET` | `/api/v1/programmes/{id}` | 200, programme object with active revision |
| `GET` | `/api/v1/programmes/{id}/courses` | 200, paginated active-revision courses |

All document-upload/ingestion, evidence, analysis, recommendation, scenario, report and human-review endpoints in the roadmap are deferred and are not registered in Phase 01. The offline fixture command is a local maintenance command, not an HTTP upload or an analysis endpoint. Swagger UI is at `/docs`, and the OpenAPI schema is at `/openapi.json`.

### Institution creation and response

`POST /api/v1/institutions` accepts:

```json
{
  "name": "Synthetic Malaysian University (DEMO ONLY)",
  "is_synthetic": true
}
```

`name` is required, trimmed, nonblank and at most 255 characters. `is_synthetic` defaults to `false`. Country is fixed to `MY` by the backend; it is not a request field. Unknown request fields are rejected with 422.

The institution response shape is:

```json
{
  "id": "<institution UUID>",
  "created_at": "<UTC timestamp>",
  "updated_at": "<UTC timestamp>",
  "is_synthetic": true,
  "name": "Synthetic Malaysian University (DEMO ONLY)",
  "country": "MY"
}
```

### Programme creation and response

`POST /api/v1/programmes` accepts:

```json
{
  "institution_id": "<existing institution UUID>",
  "name": "Software Engineering (DEMO ONLY)",
  "programme_code": null,
  "academic_year": null,
  "version_label": "initial",
  "effective_date": null,
  "is_synthetic": true
}
```

Only `institution_id` and `name` are required. `programme_code`, `academic_year` and `effective_date` default to `null`; `version_label` defaults to `initial`; `is_synthetic` defaults to `false`. Names are trimmed and limited to 255 characters. Non-null programme codes/version labels are trimmed, nonblank and at most 100 characters; academic year is trimmed, nonblank and at most 50. A non-null effective date uses `YYYY-MM-DD`. Unknown fields, invalid IDs and invalid values return 422; a missing institution returns 404.

Creation stores a programme and an initial revision in one transaction, and selects that revision as active. A synthetic institution makes its created programme and revision synthetic even when the request omits the flag. Programme creation/read/list items all use this response shape:

```json
{
  "id": "<programme UUID>",
  "created_at": "<UTC timestamp>",
  "updated_at": "<UTC timestamp>",
  "is_synthetic": true,
  "institution_id": "<institution UUID>",
  "name": "Software Engineering (DEMO ONLY)",
  "programme_code": null,
  "academic_year": null,
  "active_revision_id": "<revision UUID>",
  "active_revision": {
    "id": "<revision UUID>",
    "created_at": "<UTC timestamp>",
    "updated_at": "<UTC timestamp>",
    "is_synthetic": true,
    "programme_id": "<programme UUID>",
    "version_label": "initial",
    "effective_date": null
  }
}
```

The read schema permits `active_revision_id` and `active_revision` to be `null` for a programme with no active revision. A missing programme returns 404. Revision identity and synthetic flags are persisted; these values are not analysis results.

### Pagination and complete course inventory

All three list routes accept `limit` (integer 1–100, default 50) and `offset` (integer at least 0, default 0). Items sort by ascending UUID for a stable order over an unchanged inventory. Institution and programme pages have exactly this envelope, with their corresponding response objects in `items`:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

Course pages add `programme_revision_id`. They include every compulsory, elective and unknown-type course in the programme's active revision, including inventory-only courses. The response shape with one illustrative synthetic item is:

```json
{
  "items": [
    {
      "id": "<course UUID>",
      "created_at": "<UTC timestamp>",
      "updated_at": "<UTC timestamp>",
      "is_synthetic": true,
      "programme_revision_id": "<active revision UUID>",
      "course_code": null,
      "course_name": "Synthetic Inventory Course",
      "course_type": "UNKNOWN",
      "credit_hours": null,
      "year": null,
      "semester": null,
      "inventory_source_anchor_id": null,
      "extraction_status": "INVENTORY_ONLY",
      "detailed_syllabus_available": false
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "programme_revision_id": "<active revision UUID>"
}
```

`course_type` is `COMPULSORY|ELECTIVE|UNKNOWN`. `extraction_status` is `INVENTORY_ONLY|NORMALIZED_FIXTURE|NEEDS_REVIEW`; courses without detailed syllabi remain `INVENTORY_ONLY` on fixture import. Non-null `credit_hours` serializes as a decimal string, while `year` and `semester` are nullable integers. Course codes and source anchor IDs may be unknown and remain `null`. No relevance status, competency percentage or learning outcome is inferred from this inventory response.

`total` counts all matching records before pagination, not just the current page. Increment `offset` by `limit` until the inventory is covered. An offset beyond the end returns an empty `items` array while preserving `total`. A programme without an active revision returns an empty course page with `programme_revision_id: null`. The maximum limit constrains one page and does not cap programme size. Concurrent inventory changes may affect offset pagination; use the returned revision ID to identify the inventory being read.

### Errors and operational fields

Foundation errors use:

```json
{
  "error": {
    "code": "DATABASE_UNAVAILABLE",
    "message": "Database is unavailable",
    "details": []
  }
}
```

Expected codes are `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `CONFLICT` (409), `DATABASE_UNAVAILABLE` (503), `METHOD_NOT_ALLOWED` (405) and `INTERNAL_ERROR` (500). Validation details contain `location`, `type` and a generic `message: "Invalid value"`; submitted values are not echoed. Unknown routes return 404. Responses include an `X-Request-ID` header for request log correlation. A successful readiness response checks database connectivity only and does not certify that migrations were applied.
