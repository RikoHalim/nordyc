# Phase 3 evidence acquisition and ingestion

Implemented/completed within a bounded prototype scope on 24 October 2026. This is reference intelligence, not a course relevance/recommendation engine. Read [the measured report](PHASE3_INGESTION_REPORT.md), [radar methodology](18_WORKFORCE_TRENDS.md) and STATUS for actual source availability. Genuine legacy/multilingual taxonomy, narrow MQA summaries, official UN document text and expanded research are now imported. Current English ESCO, reviewed Malaysian crosswalks, full standard coverage and TalentCorp permission remain explicit limits.

**Planned Phase 4 integration:** the [hybrid retrieval contract](19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md) specifies internal PostgreSQL evidence first, controlled research on important gaps, original-source verification and permitted versioned reuse. That automatic research/model workflow is not implemented by Phase 3 or this documentation revision. It should reuse these adapters/tables and retain source-class, version-local identity, review-state and access/rights constraints. Current CLI behavior and the absence of startup acquisition/public evidence-ingestion triggers remain unchanged.

## Boundaries and operation

`data/dataset_registry.csv` remains the primary catalogue. Its research verification status is separate from acquisition and import status. `data/evidence_acquisition.json` selects supported adapters and records the per-source access/reuse/storage decision. An absent rule does not mean an invented download URL: curriculum rows are skipped here; other sources require manual acquisition/review. Registry metadata for every row is persisted when the command runs, even if acquisition fails.

External reference ingestion is explicit administration through the local CLI: no public external-evidence trigger, startup download, scheduler, LLM or API-key requirement. Run it separately; no slow retrieval occurs in API handlers. The distinct curriculum upload HTTP route only queues private documents in the existing catalogue worker. Shell/database access must be limited to administrators; the upload route reuses catalogue token protection.

```powershell
python -m alembic upgrade head
python -m shiftos.cli ingest-evidence --dataset D-JMI-Q1-2026 --dataset D-JMI-Q2-2026 --live --report data/local/workforce-report.json
```

Without `--dataset`, all registry entries receive an outcome. Without `--live`, automatic retrieval stays disabled. `--live` alone cannot override a source rule's review gates, robots, private DNS, format, login or rights checks. Outcomes are `SUCCEEDED`, `UNCHANGED`, `FAILED`, `SKIPPED`, `MANUAL_REQUIRED`; exit code 1 means at least one failed dataset, while manual-required/skipped outcomes are explicitly reported without claiming success.

For a permitted manually saved **original** file:

```powershell
python -m shiftos.cli ingest-evidence --dataset D-EMPLOYMENT-SECTOR --file data/local/employment_sector.csv --retrieved-at 2026-10-23T19:10:27.288562+00:00 --report data/local/manual-report.json
```

Replace that example timestamp with the file's actual original retrieval time. One dataset per local-file invocation is required. Timestamps must be timezone-aware and not future-dated. Local import does not authenticate the supplied file or prove publisher permission. It keeps its checksum, original registered endpoint and operator retrieval assertion. No failed download triggers synthetic substitution.

## Acquisition safeguards

The existing Phase 2 transport is reused, with its HTML defaults preserved. A separate dataset subclass allows only reviewed DOSM, ESCO, ILO, MQA and UN hosts and accepted data media types/extensions. HTTPS, public DNS/IP pinning, checked redirects, readable permissive robots, timeouts (20 seconds), one request per host at least every two seconds, at most three attempts and Retry-After bounds remain enforced. Missing/unreadable robots blocks by default. Policies can explicitly permit an absent robots file after review; this is not used to evade an explicit denial. Responses are limited to 5 MB and HTML/login/challenge bodies are rejected as data. Larger reports require targeted manual extraction instead of raising the ceiling indiscriminately.

Allowed originals are retained at `data/raw/evidence/<registry-id>/<SHA256>.<format>` outside Git. Both raw and reviewed local files are ignored. ZIP expansion/member/cell limits apply before XLSX parsing. PDF candidates are bounded to the first 120 pages; missing text/scans, truncation and unresolved interpretation remain warnings. No OCR or factual interpretation is implied. Extracted text and tables are available in evidence-reference metadata, with the document metadata on the version.

## Transform contracts and limitations

| Adapter | Input | Persisted interpretation |
|---|---|---|
| `dosm_jmi` | Actual DOSM XLSX, English Summary Table 2 | Finds title/occupation/year/quarter headers; selects the registry quarter; preserves original occupation-group labels, total row, units, cell locators and dash/null distinction; refuses changed layouts |
| `employment_sector` | Official `date,sector,sex,proportion` CSV | Annual sector shares, sex retained in metadata; January 1 is the provider's annual period encoding, not a publication date |
| `esco_api` | Version-pinned JSON search/resource | Published URIs, labels, descriptions and supplied essential/optional links; no names-to-ID guessing or unverified local crosswalk |
| `esco_occupations_csv`, `esco_skills_csv`, `esco_relations_csv` | Official manual CSV exports | Preserve provider fields; relations require occupations and skills in the **same coherent version bundle**, otherwise reject as unmatched |
| `un_sdg` | Official goal or target JSON list | Official IDs/text/URIs; no automatic skill-to-SDG link; target endpoint must first be registered separately |
| `pdf_candidates` | Permitted PDF | Page references/text/tables with `needs_review`; creates evidence references, **zero normalized AI/standard findings** automatically |
| `reviewed_json` | Narrow source-attributed cards | Validated occupations, skills, relationships, tasks, workforce, AI, standard or SDG records with explicit operator review assertions |

For multiple ESCO CSVs, parse each file and prepare one reviewed JSON bundle containing their occupations, skills and relationships. Preserve the original artifact hashes/version/locators in metadata. Configure a local policy selecting `reviewed_json`/`json` for that registered source, retaining the actual registered endpoint. Standalone relations cannot join arbitrary older versions. This deliberate snapshot boundary prevents silent cross-edition mappings.

Reviewed JSON has `reviewed:true`, a `records` list, and optional `metadata`. Each record has `kind`, `key`, validated `data`, `locator`, `excerpt`, optional `page_number`, and `review_status:"reviewed"`. The schema is in `services/evidence/parsers.py`. AI cards require `statement`, `impact_type` (observed capability/practice, occupational exposure, or future prediction) and nonempty `limitations`. Academic cards require discipline, title and a supported statement. Review means a supplied engineering/operator assertion, not independent academic validation. Original PDF hash/URL and review basis should be retained in metadata. Different record kinds must agree with the real source's evidence class; synthetic packs remain explicitly synthetic.

Automatic structured-source references retain `needs_review`; they are source-attributed parsed observations, not independently checked academic interpretations. PDF cards cannot be promoted merely because text extraction worked. Publication precision/prose is retained as `dataset_versions.publication_date`; observation start/end and UTC retrieval time are separate fields. Null means unknown, never zero. Occupation advertising totals do not measure skills, and exposure is not replacement probability. A capability-free exposure-context card may retain a `dated_workforce_signal` source (OECD); it cannot be relabelled observed capability or activate AI transformation.

## Loading, jobs and reproducibility

The repository serializes each dataset import with a PostgreSQL row lock. Immutable version identity includes dataset, original input checksum, parser version and transformation-context hash. Parser/context changes create a new version; retrieval time alone does not. Historical rows remain queryable. Exact duplicate records are removed; conflicting duplicates or unresolved relationship IDs fail the entire dataset transaction. No partial facts/source/version survive a failed import. Errors and unmatched-classification locators remain in durable jobs/logs; upstream response content and credentials are excluded from errors.

Separate `evidence_ingestion_jobs` are necessary because the existing curriculum `jobs` require an institution/revision. Each dataset gets a durable running/outcome record; one dataset failure does not erase others. If the process is forcibly terminated, a running job can remain: inspect version provenance and rerun the same command safely. This phase has no automatic stale-job recovery or lease service. Operators should mark/record interrupted jobs in operational review; an interrupted invocation is never evidence of completed acquisition.

Migration `0004_reference_evidence` adds 13 tables and leaves Phase 1–2 tables intact. A downgrade refuses to drop populated reference tables; export/preserve evidence first. Registry metadata is copied into immutable versions, so later registry updates do not rewrite source history. No Phase 4 dependency/reassessment engine is implemented.

## Read-only API

All paths start `/api/v1/evidence`. List responses use `{items,total,limit,offset}` with limit 1–100. Routes cover datasets and their versions/jobs, version and reference provenance, occupations/skills/relationships/tasks, workforce history, AI impacts, academic standards, SDGs and ingestion logs. Filter by version/dataset and synthetic status where applicable; workforce adds dates/indicator/classification code, AI adds subtype/occupation label, standards add discipline. The schema and error shape are documented in Swagger and [the API contract](10_API_CONTRACT.md). Consumers must select versions explicitly when comparing vintages; default lists include historical records.

## Offline demonstration

```powershell
python -m shiftos.cli ingest-evidence --registry fixtures/evidence/dataset_registry.synthetic.csv --policy fixtures/evidence/policy.synthetic.json --dataset SYNTHETIC-EVIDENCE --file fixtures/evidence/records.synthetic.json --retrieved-at 2026-10-01T00:00:00+00:00 --synthetic
```

This pack is invented test/demo content and makes no statement about XMUM, actual ESCO concepts or Malaysian labour demand. It exercises several disciplines, relationships, two workforce periods, AI subtypes, standards and SDG reference storage without network access.

## Phase 2 brochure compatibility

The primary upload path is now implemented:

```powershell
python -m shiftos.cli upload-curriculum-pdf path/to/brochure.pdf --programme <UUID>
python -m shiftos.cli worker --once
```

HTTP clients send the original binary PDF to `POST /api/v1/programmes/{id}/curriculum-pdf` as `application/pdf` (Swagger exposes a binary upload). The route returns 202 and uses the same catalogue write token/production guard. Only this route allows a 20 MB request; other catalogue writes retain 1 MiB. Optional `source_url` must be on the institution's official host. If omitted, the programme URL is only an origin pointer and the exact source remains the privately stored uploaded PDF/hash. No network fetch or verified-university assertion is made. Collection/upload time is not publication or effective-cohort time.

The worker can conservatively detect horizontal explicit YEAR columns below MAIN COURSES; it never assigns years from page-wide text order. Other layouts accept a JSON `regions` query or CLI `--regions regions.json`, containing `page,x0,top,x1,bottom` rectangles. Unknown/scanned/encrypted layouts fail visibly with manual-region/structured-import guidance. No general syllabus interpretation is promised. PDF originals, candidate inventories and source page anchors are committed atomically; integrity is checked before processing. Repeat uploads preserve one original/document and the existing revision. No table/migration is required beyond 0004.

Phase 2 originally accepted HTML or reviewed structured JSON, not raw brochures. `prepare_brochure_import` in `services/ingestion/pdf.py` now converts a local PDF plus explicitly selected `PdfCourseRegion(page,x0,top,x1,bottom)` rectangles into the existing `CatalogueImport` contract. Use one region per course column/block; no full-page automatic year association. Inspect the page and returned JSON before the normal `import-curriculum`/worker flow. Unknown years, semesters and types remain unknown; wrapped titles and ambiguous labels retain review notes. The converter always returns unreviewed candidates and never claims a syllabus.

Real Accounting brochure verification: automatic detection and the original page2 regions both yielded 37 candidates (12 Year1,14 Year2,6 Year3,5 elective-year unknown). Actual PostgreSQL/API upload+worker succeeded and repeated as unchanged, with 0 verified titles and one stored original PDF. The original explicit rectangles remain `[15,405,198,620]`, `[210,405,397,620]`, `[408,405,590,620]`; they apply only to that version. Other layouts/scans require review. No general PDF crawler or course analysis was added.

## Manual/restricted sources

Current English ESCO wizard delivery needs the operator's own consent/email; no CAPTCHA/login automation. A permitted official v1.0.3 multilingual subset is separately registered, not labelled current. MyNSR has no verified complete export. TalentCorp/MyMahir's actual Group notice requires written aggregation/network-use consent; metadata only remains available. Narrow MQA benchmark paraphrases/short attributed quotations have a scoped internal research decision, not blanket full-text/public-commercial reuse permission. Official UN resolution text is imported under its document public-domain basis; statistical API compilation rights remain separate. Large reports/landing pages are not direct downloads by default. See [permitted genuine reference packs](../data/reference_packs/README.md) for offline ESCO/UN commands and exact attribution.
