# Data acquisition and maintenance plan

Research baseline: 24 October 2026. **Design only.** No importer, worker, table, migration, API or LLM integration was added. Source access states and exact URLs are in [dataset_registry.csv](../data/dataset_registry.csv); check them again before acquisition.

## Operating model

Maintain reusable, versioned reference packs for standards, taxonomies, workforce releases, AI evidence and SDG/resource metadata. Discover curricula **on demand per institution**, beginning with XMUM. Cache source-backed results and report missing information. Adding another Malaysian university should require a source adapter/configuration and a reviewed coverage inventory, not collecting every university in advance.

Separate four gates: (1) source located, (2) access/reuse method allowed, (3) downloaded/extracted and validated, (4) persisted records with provenance. Research completion establishes selected source verification, not gates 3–4 for the application. A crawler returning HTTP200 cannot establish completed ingestion.

## Acquisition runbook for the data engineer

| Step | Exact entry point / file | Method and expected output | Gate/fallback |
|---|---|---|---|
| 1. Freeze manifest | This registry and research baseline | Copy approved rows into a dated acquisition manifest; record scope, expected formats, licence decision and owner | Keep unknown/blocked rows visible; no automatic promotion to verified |
| 2. Check policy | Each exact source host, terms and robots | Record checked URL, response, retrieval time and applicable rule | XMUM robots was unresolved; retry normally. If restrictive/unavailable, use a permitted manual import or mark blocked; never bypass login/CAPTCHA |
| 3. Enumerate XMUM | [Directory](https://xmu.edu.my/undergraduate-programmes), [brochure index](https://www.xmu.edu.my/index.php/admissions/download), [MPU](https://xmu.edu.my/MPU/about-us) | One institution inventory; programme URLs, titles, available public fields and per-programme status | Current research has 25 entries, but runtime discovers current entries; account for each even if extraction fails |
| 4. Extract curriculum candidates | Programme-page URLs and brochure links in A-XMUM-01..25 | Read explicit Main Courses/year/elective headings; optional programme outcomes separately; PDF page2 fallback | Keep year/semester/type null unless shown; preserve bilingual/combined labels and placeholders for review |
| 5. Secure standards | [MQA index](https://www2.mqa.gov.my/qad/v2/types3new.cfm) and relevant B rows | Applicable bachelor's outcome/core-area metadata, document/circular version and page locators | Permission gate for stored full text; link/paraphrase-only mode if rights unresolved; no invented field standard |
| 6. Obtain taxonomy | [ESCO wizard](https://esco.ec.europa.eu/en/use-esco/download); [version-pinned API sample](https://ec.europa.eu/esco/api/search?text=accountant&type=occupation&language=en&limit=1&selectedVersion=v1.2.1) | English classification CSV with relevant relation files; or permitted small API subset | Engineer requests wizard delivery with their own email/consent; do not automate CAPTCHA or invent ZIP URLs. Log actual headers/version/license |
| 7. Add local classification | [eMASCO](https://emasco.mohr.gov.my/), [MyNSR FAQ](https://mynsr.talentcorp.com.my/faqs/) | MASCO code/version notes; selected permitted local role references | No unverified complete national skill export; unresolved crosswalks remain unresolved |
| 8. Acquire workforce pair | [Q1 XLSX 19819](https://www.dosm.gov.my/portal-main/release-document-log?release_document_id=19819), [Q2 XLSX 20742](https://www.dosm.gov.my/portal-main/release-document-log?release_document_id=20742) | Two ~349KB as-published files; normalized checked table rows and source metadata | Match header/period/unit rather than trusting hardcoded coordinates; fail on layout change; preserve dash/zero |
| 9. Optional survey corroboration | [employment_sector.csv](https://storage.dosm.gov.my/labour/employment_sector.csv) and [metadata](https://open.dosm.gov.my/data-catalogue/employment_sector) | `date,sector,sex,proportion`; selected 2024/2025 annual records; CC BY notice | January1 means year; percent is not count; incompatible metric with job offerings |
| 10. Curate AI cards | [ILO PDF](https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf), E-HBS-2026 and selected P1 sources | Narrow supported claims, task/setting/model/date, exact locators, counter-evidence and rights | Exposure/foresight/guidance/observed experiment must be distinct; correction dependencies mandatory |
| 11. SDG/resources | [UN goals JSON](https://unstats.un.org/sdgapi/v1/sdg/Goal/List), [targets JSON](https://unstats.un.org/sdgapi/v1/sdg/Target/List), selected course pages | Official IDs/source links; reviewed skill-to-target rationale; 6–12 relevant resource metadata records | Rights review for redistributed raw text; resource prerequisites/time/cost may be null; no invented pathway |
| 12. Review and release pack | Validated candidates and source manifest | Coverage, conflict and rights report; permitted normalized snapshot; checksums; reproducible input versions | Only then import using separately approved backend functionality; no live claim for fixtures |

Start with metadata and small samples. Do not acquire the 48.65MB TalentCorp Volume1 or multi-gigabyte corpora merely because a link exists. Select only sector pages needed for the demonstration. Public MyMahir portal scraping/aggregation requires consent under its terms; use permitted reports or request an export instead. No provider has been contacted by this research task.

## File contracts for a later implementation

These are **proposed internal formats**, not claims about provider column names, and not implemented schemas.

| Layer | Proposed storage | Required distinctions |
|---|---|---|
| Raw allowed artifact | Immutable original HTML/PDF/XLSX/CSV/JSON in local/object storage, named by source ID + SHA256 | Original bytes and response metadata; never overwrite; rights-restricted text excluded from public Git |
| Manifest | UTF-8 JSON; small CSV discovery registry | Source ID, canonical/final URL, publisher, type, MIME, bytes/hash, edition, terms/robots decision, fetched UTC, publication date precision, observation window, synthetic flag |
| Curriculum candidates | JSONL with source anchors, optional CSV manual import | Official title/raw label, programme, year label, nullable parsed year/semester/type/code, elective group/quota, source locator, evidence level, conflict status |
| Reference data | UTF-8 CSV/JSONL; Parquet only for larger analytical tables | Provider IDs/URIs and pinned version; preserve original labels, relation types, language and source IDs |
| Report evidence | JSONL cards + page/section/table/cell locators | Supported narrow statement; excerpt only as permitted; evidence class/subtype, task, geography, dates, model/tool, uncertainty, correction/supersession |
| Reviewed mappings | CSV/JSONL before later relational import | Left/right taxonomy/version/ID; relation; source evidence or inference flag; reviewer/status; rationale; ambiguity; no numeric confidence invented |
| Snapshot bundle | Manifest plus stable hashes/ordered artifact list | Acquisition time versus “as known on” cutoff; parser/mapping versions; no silently mixed synthetic/real values |

Unknown dates remain null plus a precision/status field; a year-only date must not become an invented January1 publication date. The OpenDOSM provider's January1 convention is separately preserved as annual-period encoding. `Year 1` in a curriculum and a calendar year of observation are different attributes.

## Relationships and existing database fit

The working revised Phase 1 repository currently has eight tables: `institutions`, `programmes`, `programme_revisions`, `courses`, `documents`, `document_anchors`, `jobs`, `sources`. Its additive migration `0002_catalogue_sources` and manual catalogue/source APIs already provide metadata/provenance; source registration does not fetch or independently verify anything. The repository advanced during this research, so the plan was reconciled with its current data-model/architecture docs at commit `6690a4d`. **Reuse the existing source registry and revision boundary; do not create duplicates.** Evidence passages, standards/skills/occupations, signal snapshots and analysis entities remain future concepts. Extend only in the separately approved phase with migrations/tests when needed.

Retain institution → programme → immutable programme revision → all course appearances. Course occurrences in different years/tracks/programmes remain distinguishable. A course may have multiple source anchors and a shared elective pool; neither title-only global deduplication nor compulsory-by-default is safe. Programme revision points to a curriculum snapshot/source set. Shared MPU course → programme/cohort eligibility is an explicit relationship requiring evidence, not an unconditional cross-join.

Future sources → artifacts/versions → evidence items supports every normalized fact. Standards → bachelor competencies and taxonomy skills form reviewed links. Occupations ↔ skills retain taxonomy URIs, version and essential/optional relation. MASCO/ISCO/ESCO crosswalks are many-to-many with unresolved states. Workforce observations link to occupation **at the granularity published**, or sector, with metric/unit/geography/period/method; a broad group must not be copied into every child occupation or skill as measured demand.

AI task evidence links to occupation/task only where justified, plus method/model/evaluation date and correction relationships. Programme/course ↔ benchmark/occupation/skill links are inferred review candidates unless actual course outcomes support them. SDG links require target code, rationale, supporting task/skill evidence and reviewer status. Learning resources have publisher-stated prerequisites/duration/cost with unknowns retained.

An analysis run must reference exact curriculum revision, evidence snapshot hashes, mappings, parser/rule version, scenario assumptions and any model/prompt version. These relationships implement the existing reproducibility contract; no graph/vector database or per-major AI agent is needed.

## Proposed refresh policy, distinct from publisher cadence

| Family | Publisher cadence verified | SHIFT//OS proposed policy |
|---|---|---|
| XMUM | No fixed course-page update schedule found | On demand; cached results; termly catalogue check and before demo; conditional requests where supported |
| MQA/MQF/EAC | Version/circular-driven; no common release schedule verified | Quarterly index check and whenever new circular is noticed; academic applicability review before switching |
| ESCO | Versioned major/minor releases | Quarterly version check; pin during demonstration; inspect deltas before remapping |
| MyNSR/MASCO | No reliable fixed public export schedule verified; portal transition unresolved | Quarterly metadata review; do not assume planned updates occurred |
| DOSM JMI | Quarterly observation series; variable release lag | Check monthly release calendar/archive; ingest new published quarter only; compare revisions separately |
| OpenDOSM employment sector | Annual observations; metadata lists next update 31 Oct2027 | Quarterly metadata check; refresh upon published update; preserve previous vintage |
| MyCOL | Publisher describes annual research, observed cycle gaps/scopes vary | Quarterly publication-index check; verify comparability per edition |
| AI research | Irregular publication, model change and corrections | Monthly check of small selected source set; correction invalidates affected claims until reviewed |
| UN targets | No fixed target-text revision cadence verified | Quarterly metadata/terms check; keep indicator revisions separate |
| Learning resources | Course-specific/variable | Quarterly and before recommendation/demo; recheck dead links, price, hours and prerequisites |

These are engineering policies, not promises about source publishers. No scheduling feature is requested for this task; manual refresh commands are sufficient for the preliminary package.

## Acquisition safeguards and acceptance criteria

For later allowed HTTP acquisition, propose one request at a time per host, at least two seconds between requests unless publisher policy is stricter, 20-second request timeout, bounded pages/bytes, and at most three attempts with backoff for temporary failures. Respect `Retry-After`; stop/review on 401/403/robots denial; no user-agent tricks, login bypass or anti-bot evasion. Validate redirects stay within approved official domains. These are proposed controls, not claims they are implemented.

Checksum/version identity makes reruns idempotent. Use institution+official programme source identity; code where supplied plus programme/revision/year/choice-group context for course identity. Preserve raw labels and review ambiguous merges. A vanished course is “missing in new source snapshot,” not silently deleted or proven discontinued. Store extraction candidates separately from accepted facts. A changed source creates a new evidence version and re-evaluates only dependent results, retaining prior runs; unchanged content produces no duplicates.

Required later checks: each discovered programme accounted for; every admitted university fact has an origin locator; unsupported semester/type remains null; crosswalks versioned; period/unit/metric valid; two real workforce periods present; no occupation count copied into skill demand; no forecast represented as measured capability; correction dependencies satisfied; recommendations cite admissible evidence or abstain. Machine-generated candidates must pass JSON-schema/Pydantic validation and source-bound checks. Parser/layout changes fail visibly instead of returning a misleading empty catalogue.

Offline tests/demo retain explicitly invented institutions/programmes/courses where detail is synthetic. A real XMUM catalogue may be used with verified titles only; missing real descriptions stay missing. Keep `synthetic_demo` markers at source, item and report levels. Scenario assumptions are separately labelled inference. Public Git includes code, manifest, permitted data and attribution; rights-restricted raw documents stay out. Do not assume metadata-only operation grants permission to reproduce protected source text at scale.

## Rights checklist by artifact

| Source | Acquisition/release decision |
|---|---|
| XMUM | Public read verified; robots/automation/redistribution unresolved. Use permitted manual extraction, fact pointers and explicit limitation pending review; no whole-brochure mirror. |
| MQF/MQA/EAC | MQF restrictive notice verified; individual standards have separate rights checks. Metadata/pointers first; written permission if required for stored full text. |
| ESCO | Follow EC reuse terms, required ESCO acknowledgement, version and adaptation notice. Do not confuse API software licence with content rights. |
| DOSM JMI | Government Open Data Terms1.0 attribution/terms link/ownership statement as applicable; exceptions retained. |
| OpenDOSM / selected ILO and HBS article | Specific CC BY4 notices verified; attribute, state changes, observe third-party exceptions and ILO adaptation conditions. |
| TalentCorp/MyMahir | Report-specific rights unresolved; portal terms restrict automated scraping/aggregation. No inferred open licence from government affiliation. |
| UN / UNESCO / learning providers | UN target reuse status unresolved; UNESCO selected publications state CC BY-SA3 IGO but full-file checks pending; OpenLearn and MIT have non-commercial/other conditions. Link to learning content instead of mirroring. |

Legal/access facts above are observations of publisher notices, not a blanket reuse authorisation. If permission cannot be obtained, retain a data-limited branch with source links and abstention; never substitute fabricated public evidence.
