# Phase 2 — curriculum discovery and ingestion

Implemented 2026-10-24. This phase ends at source-backed catalogue retrieval. Standards/evidence ingestion, AI relevance, recommendations and frontend remain later work. Read [dataset research](DATASET_RESEARCH.md), [the acquisition plan](DATA_ACQUISITION_PLAN.md), [schema](03_DATA_MODEL.md) and [API contract](10_API_CONTRACT.md) alongside this handoff.

## What runs

FastAPI validates and queues PostgreSQL-backed jobs; a separate `python -m shiftos.cli worker` process performs acquisition. Requests do not wait for official websites. The queue reuses `jobs`, catalogue snapshots reuse `programme_revisions`, and existing Phase 1 routes/fixture imports remain supported.

The `xmum` provider discovers links from the official [undergraduate directory](https://www.xmu.edu.my/undergraduate-programmes), rather than a fixed programme list. It follows explicit undergraduate `/courses/` links and parses each public **Main Courses** section. Another institution needs a reviewed provider origin and parser implementing `CurriculumParser`, plus its fetch allowlist entry; it does not need new tables or catalogue endpoints. Only XMUM has a live provider today. The structured import works for other official institution hosts now.

The parser supports year accordions, explicit semester labels, elective/compulsory headings, shared elective pools, bilingual labels and year-column tables. It retains exact public titles, original labels, CSS locators and short title excerpts. Missing year/semester/code stay `null`; missing classification stays `UNKNOWN`. Combined year labels remain raw text with no invented numeric year. No credits, learning outcomes, descriptions, academic cohort dates or detailed syllabi are inferred. An elective quota is not a semester or a newly invented course. Ambiguous/composite/truncated labels are retained with review notes.

## Setup and live discovery

Use the existing README setup, PostgreSQL and pinned dependencies. Back up the intended database, confirm `DATABASE_URL`, then apply `python -m alembic upgrade head`. Additive migration `0003_curriculum_ingestion` preserves original records and migrations. Downgrade refuses to discard populated Phase 2 metadata/jobs; export before a planned rollback.

Live retrieval is disabled by default. Review publisher terms, robots and permitted reuse and record the date/decision in your operations log before enabling both flags in the **worker's environment**:

```powershell
$env:DISCOVERY_ENABLED = 'true'
$env:DISCOVERY_TERMS_REVIEWED = 'true'
python -m shiftos.cli worker
```

Start FastAPI in another terminal with the same database:

```powershell
uvicorn shiftos.main:app --app-dir src --host 127.0.0.1 --port 8000
$job = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/catalogue/discover `
  -ContentType application/json -Body '{"provider":"xmum","idempotency_key":"xmum-review-001"}'
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/catalogue/jobs/$($job.id)"
```

The Uvicorn command occupies its terminal; issue HTTP commands in a third terminal or use Swagger. The global discovery route creates/reuses the official nonsynthetic XMUM institution. An existing matching institution can instead use `POST /api/v1/institutions/{id}/discover`. A key returns the same job for the same payload; reuse with a different payload returns 409. Use a fresh key for a new acquisition attempt. Replaying a failed job's old key does not restart it.

Configure a **nonempty** `CATALOGUE_WRITE_TOKEN` and send `X-Catalogue-Token` on the four new POST routes when a server is shared. Production mode disables those writes with 503 when no token is configured; wrong/missing tokens return 401 when configured. Empty/whitespace tokens are rejected at startup. Local development/test can omit the token. This guard covers catalogue job submissions only; Phase 1 manual CRUD, reads, deployment/network authentication and CLI operator privileges remain separate concerns. Bind local development to localhost; this is not a production identity system.

## Access boundary and failure behavior

- HTTPS, reviewed exact hosts, public DNS addresses, pinned outbound IP with original TLS hostname verification; no caller-selected arbitrary URL fetching.
- Per-host robots checks, including redirects; unreadable/missing robots deny by default. No CAPTCHA, denial or login bypass. The configured provider does not override absent-robots policy.
- Environment proxies are ignored by the fetcher. A private-address result or private network gateway is refused; use an independently reviewed file instead of disabling the destination check.
- Minimum two seconds between requests, including robots/retries/redirects; honor longer crawl delays/request rates. Maximum three attempts, three redirects, 20-second request timeout, two-million-byte HTML response, 128KB robots file. Compression not honoring `Accept-Encoding: identity` is rejected.
- Up to 100 programme links per run and a ten-minute budget checked between programme fetches. One in-flight bounded request may extend the budget. Retry/backoff pauses longer than 30 seconds require an operator retry later.
- Directory success records discovered programmes, not course coverage. Each programme commits atomically; individual failures produce a `PARTIAL` result with source pointers/error codes and retain older course snapshots. Directory failure gives `FAILED`. No empty successful inventory is fabricated.

The worker commits claim/status before network work, serializes writes per institution and stores per-programme progress. PostgreSQL row locks fence late workers against operator recovery and avoid duplicate same-institution execution. Other institutions' jobs can proceed. After a confirmed worker crash, `python -m shiftos.cli fail-stale-jobs` explicitly marks running catalogue jobs older than one hour failed. It does not silently retry them; submit a new request. Retained imports are safe to replay. No automatic scheduler or external queue service is required for this phase.

## Reviewed structured-file fallback

Obtain the official page/brochure manually through permitted access. Transcribe or parse its facts into the manifest, preserving its actual URL, retrieval date, locator and exact title excerpt. Cross-check ambiguous labels. A manifest cannot assert syllabi, descriptions or arbitrary extra fields. Input is limited to 1MiB, 100 programmes, 1,000 appearances per programme and bounded strings. Larger imports must be split. `content_hash`, when supplied, is the source-file SHA-256; when omitted, the system hashes normalized supplied facts and does **not** claim a downloaded-file hash.

`reviewed: true` is an accountable operator assertion that source facts were checked. It is not proof of publisher authenticity or taught content. Leave it false for candidates; they persist as `NEEDS_REVIEW`/inference and no verified titles. Extraction warnings also prevent individual titles from being counted verified. Synthetic imports require a separate synthetic institution and always remain synthetic/unverified.

Minimal nonsynthetic programme object within `{"is_synthetic":false,"programmes":[...]}`:

```json
{
  "name": "<copy exact official programme name>",
  "canonical_url": "https://<official-institution-host>/<programme-path>",
  "source_url": "https://<official-institution-host>/<source-path>",
  "source_locator": "Main Courses / Year 1",
  "retrieved_at": "<actual ISO 8601 timestamp with timezone>",
  "license_status": "rights_unconfirmed",
  "reviewed": false,
  "notes": ["Record specific limitations here"],
  "courses": [
    {
      "course_name": "<copy exact public course title>",
      "year": null,
      "semester": null,
      "course_type": "UNKNOWN",
      "source_locator": "<CSS selector or PDF page/list position>",
      "source_excerpt": "<exact excerpt containing the course title>"
    }
  ]
}
```

The placeholders above require real values; they are not a verified data sample. [The executable synthetic manifest](../examples/curriculum_import.synthetic.json) demonstrates the format without attributing invented courses to XMUM. Optional course fields include `course_code`, `raw_year_label`, `raw_semester_label`, `elective_group`, `review_notes`; allowed classification values are `UNKNOWN`, `COMPULSORY`, `ELECTIVE`. Generate the authoritative schema directly when needed:

```powershell
python -c "import json; from shiftos.schemas.ingestion import CatalogueImport; print(json.dumps(CatalogueImport.model_json_schema(), indent=2))"
```

Create/retrieve the institution through the existing API with its real `website_url`, then queue the file and run the worker:

```powershell
python -m shiftos.cli import-curriculum path/to/reviewed.json --institution <INSTITUTION_UUID>
python -m shiftos.cli worker --once
```

`--once` handles the next eligible queued job, which may differ from the last submitted job. Poll the returned ID. The CLI needs database operator access; HTTP token configuration does not govern it. Alternatively POST the JSON to `/api/v1/institutions/{id}/imports`; the programme-scoped route accepts one programme object plus `is_synthetic`/optional key and checks target ownership/identity. Both queue the same worker path. Manual imports do not fetch URLs and work with both discovery flags false.

## Identity, snapshots and provenance

Institution/programme relationships remain unchanged. Programme identity is the normalized official canonical URL within an institution; `www` aliases/trailing slashes/fragments normalize, meaningful query strings remain. Ambiguous existing identities fail with 409 rather than merge unrelated programmes. Exact duplicate source occurrences are skipped; repeated titles in distinct years/elective groups/locators remain separate appearances with review notes when potentially duplicated. Counts are appearances, not unique course codes.

A fingerprint of normalized manifest facts, supplied source hash, parser version, review state, acquisition mode and synthetic lane identifies a revision; retrieval time alone does not duplicate it. Existing snapshots are sealed against manual API appends. Changed facts produce a new revision and preserve historical courses/anchors. Replaying an older snapshot returns its existing revision without reactivating it; a newly received older-dated snapshot is stored as historical. Missing directory links are reported, not deleted. Raw whole-page hash changes can create a new revision even when title content is unchanged; later refresh work may refine semantic change detection.

Sources retain URL, content hash, retrieval/observation time, rights status and evidence class. Publication/cohort dates are not inferred from retrieval. Immutable source IDs include canonical URL/hash/class/rights. Each imported revision has a JSON document record and exact title excerpts in anchors; the source CSS/PDF locator and URL remain on each course. The document represents a normalized extracted title inventory, **not a mirrored HTML/PDF file**. Whole source pages/brochures and copyrighted teaching material are not committed. `public_facts_only_rights_unconfirmed` records unresolved reuse rights; public access/robots permission is not an open licence.

## Retrieval and truthful coverage

Use existing `GET /api/v1/institutions`, `/institutions/{id}/programmes`, `/programmes/{id}`, `/programmes/{id}/courses` and `/courses/{id}`. New routes expose `/programmes/{id}/coverage`, `/programmes/{id}/revisions`, and `/programmes/{id}/revisions/{revision_id}/courses`. Paginate lists (default 50, maximum 100); cross-programme revision access returns 404.

Courses expose raw year/semester labels, elective group, source URL/locator, review notes, `missing_fields` and `evidence_level`. Coverage reports snapshot metadata, course appearance count, verified-title count, needs-review count and title-only count. `graduation_curriculum_complete` is deliberately false: a marketing **Main Courses** list does not certify MPU requirements, effective cohort, complete credits or what lecturers teach. An empty directory-only programme reports zero courses and missing inventory; it is not an empty degree. No obsolete/replacement verdict or relevance score exists in Phase 2.

## Actual acceptance evidence — 2026-10-24

All automated tests are offline except explicitly opted-in PostgreSQL tests; synthetic HTML spans commerce, humanities and science structures, plus computing examples. Security tests cover robots, redirects, private DNS, DNS pinning, size limits/chunked bodies, access controls, credential redaction and stale-worker fencing. PostgreSQL tests exercise upgrades from populated older revisions, schema comparison, loss-preventing downgrade guards, queue/import/replay/history and FastAPI retrieval. See STATUS for final measured test totals.

Real Uvicorn + PostgreSQL 16.15 validation used a fresh disposable local database, never a user's application database:

| Check | Actual result |
|---|---|
| Production `SafeFetcher` live XMUM directory discovery, twice | **FAILED safely**: `www.xmu.edu.my` resolved to private `10.68.12.164` in this environment; bare `xmu.edu.my` did not resolve. No source/programme/course records were persisted by these jobs; the submission route did bootstrap the institution/job records. No bypass was used. |
| Previously retrieved official HTML directory parsed locally | 25 explicit undergraduate links; all 25 facts stored through existing source/programme APIs, with official locators. This was a reviewed manual directory import, not successful live provider collection. |
| Reviewed file generated from three previously retrieved official Main Courses pages; CLI enqueue/worker with network disabled | **SUCCEEDED**: Accounting 37, Chinese Studies 62, Marine Biotechnology 42 = **141 course appearances**; all retrievable through real FastAPI HTTP calls. |
| Verification assertions | 138 title appearances marked verified; three adjacent bilingual pairs retained for human review. All 141 remain title-only; zero syllabus claims. |
| Identical file queued/imported a second time | **SUCCEEDED**, all three unchanged. Counts remained 25 programmes, 28 revisions (25 initial directory-only + 3 imported), 141 courses and four sources. |
| Remaining real-data coverage | 22 directory programmes have zero loaded course inventory in this disposable validation database. No claim that all 25 real course lists were automatically ingested. |

Official manual-fallback sources: [Accounting](https://www.xmu.edu.my/courses/bachelor-management-accounting-honours), [Chinese Studies](https://www.xmu.edu.my/courses/bachelor-arts-chinese-studies-honours), [Marine Biotechnology](https://www.xmu.edu.my/courses/bachelor-science-marine-biotechnology-honours). Directory/source snapshots were retrieved during this task; their hashes and actual file retrieval timestamps were carried into the reviewed manifest. Raw source files and local smoke scripts/results remain outside versioned product data. The repository's reproducible automated tests use clearly fictional fixtures.

## Handoff and remaining work

Run live provider validation from a network where the official hostname resolves publicly, after recording access/rights review. Use the manual manifest for blocked/unsupported pages and inspect every programme's coverage; do not claim an unrun crawl succeeded. Reconcile shared MPU, placeholder electives, bilingual pairing, ambiguous years and broken/truncated public labels against official brochures. Supporting PDF transcription is manual in this phase; there is no general PDF/JavaScript crawler. Neither semester detail nor certified full curricula are promised where publishers do not provide them.

The next development task is **Phase 3 reference evidence ingestion**: selected MQA benchmarks, occupation/skill taxonomy, two dated Malaysian workforce snapshots and cross-disciplinary AI evidence, with traceable units/dates/licences and offline fixtures. Keep AI relevance/actions/UI out until their authorised phases. Institutional/personalised-pathway/SDG/scenario hackathon waivers remain unconfirmed as recorded in STATUS.
