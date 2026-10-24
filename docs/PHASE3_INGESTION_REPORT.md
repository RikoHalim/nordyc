# Phase 3 completion and workforce intelligence report — 24 October 2026

**Phase 3 infrastructure and bounded evidence gates are functional. Ready to begin a conservative Phase 4 prototype against the frozen subset, not a complete/current all-programme evidence catalogue.** Latest English ESCO, reviewed Malaysian crosswalks, full discipline standards and permission-cleared TalentCorp data remain open enrichment/review gates. They must remain unavailable rather than be inferred. No Phase 4 implementation, academic recommendations, frontend redesign, additional AI model, commit or push was performed.

## Resolved issues and actual acquisition

The initial run had only workforce records and three ILO exposure cards. This completion preserves those immutable inputs and adds genuine taxonomy relationships, academic benchmark summaries, official SDGs, diverse AI research, deterministic radar APIs and a protected upload-first PDF path.

Interactive browser assistance was attempted but the session exposed no enabled browser/apps. Official web-page reads/search and legitimate normal downloads/manual import were used. Browser/web access was not treated as permission for backend scraping; production SSRF/public-DNS/robots/retry limits were unchanged.

- **ESCO:** an explicitly linked official legacy archive supplied a complete Arabic CSV ZIP (4,236,615 bytes, CRC checked, SHA256 `51259f71995ff62f75fa23d3b30ac7707051f062234c45ffc3fe60be7527c665`). A deliberately partial 3,145,728-byte range of the same-edition multilingual TTL archive supplied complete English subject/description blocks. Only source-verified exact-URI joins were retained: **38 occupations, 10 English-described skills, 39 essential/optional relationships**. Four occupation labels are source-English, 34 remain source-Arabic. The edition is **v1.0.3**, not current; the full TTL archive was neither downloaded nor CRC-verified. The modern API/wizard failure is preserved. Official EC reuse acknowledgement/adaptation notice is in the manifest and reference pack.
- **MQA:** four actual official PDFs were downloaded and selected bachelor-level pages checked, including rendered Accounting/Biotech pages. **12 original benchmark summaries** cover Computing, Accounting, Business and Biotechnology, with edition, page, date precision, PDF hash and minimal proportionate supporting quotations. This is scoped attributed prototype research, not an open/full-text redistribution grant, independent academic validation, programme compliance or evidence XMUM teaches these competencies. The original documents are not published in the repository.
- **UN:** official resolution A/RES/70/1 supplied **17 goals and 169 targets** with exact identifiers/text/page references, issued 21 October 2015 and adopted 25 September. The official UN Publications Policy Manual §§5.34–5.35(c) provides the distinct official-document public-domain basis; §5.37's separate statistical database permission is not assumed. All 169 target texts were crosschecked in memory against the API after format/footnote normalization; no disagreement. No occupation/skill-to-SDG link was invented.
- **AI:** **20 cards** now cover ILO exposure, HBS consulting experiments, OECD exposure/advertised-skill associations, METR coding-workflow evidence and the corrected A-Lab materials workflow/correction. Observation/model dates differ from publication dates; METR disagreement and A-Lab correction are retained. Exact pages or HTML sections, limitations, rights/attribution and engineering-review basis remain visible. OECD retains its original `dated_workforce_signal` source class for contextual exposure findings; it is not recast as measured capability.
- **Workforce:** the original **247 observations** remain unchanged: two DOSM JMI quarterly Table2 subsets (11 rows each) and 225 annual sector/sex shares. Original units, missing values and source periods survive. The production acquisition path genuinely downloaded DOSM workbooks and ILO PDF; OpenDOSM used a permitted normal manual CSV fallback after its robots check failed.
- **Curriculum:** the primary workflow now selects a programme and uploads a private original PDF. HTTP only queues; the existing separate worker detects supported labelled year columns or uses supplied regions, creates unreviewed course candidates and retains the original document/hash/page anchors. The real Accounting brochure upload returned 202, worker succeeded with **37 candidates** (12 Year1,14 Year2,6 Year3,5 year-unknown electives), **zero verified taught-content claims**, and repeat upload returned the unchanged revision with one stored PDF. Unsupported/scanned/syllabus layouts still need explicit regions or reviewed JSON; no general syllabus interpretation is claimed. Discovery remains secondary.

Permitted frozen ESCO and UN subsets are provided under `data/reference_packs/` for repeatable offline real-data import. Their full attribution/rights decisions are preserved. Restricted originals and narrow internal research cards stay ignored under `data/local/closure_research`; private uploads stay under `data/private/curriculum_uploads`. Synthetic fixtures remain separate and clearly invented.

## Genuine PostgreSQL contents and API proof

Windows/Python3.12/PostgreSQL16.15, same disposable `shiftos_phase3_validation` database on loopback port 55433; no application/user database was migrated. All normalized category reads returned HTTP200, all 18 version-provenance reads succeeded, and SQL joins verified all 39 ESCO relationships point to real stored occupations/skills with nonempty skill descriptions. Taxonomy and real brochure replays were idempotent. Source job failures remain in history; they were not erased to imply universal acquisition success.

| Table | Actual rows |
|---|---|
| `datasets` | 75 |
| `dataset_versions` | 18 |
| `evidence_references` | 628 |
| `occupations` | 38 |
| `skills` | 10 |
| `occupation_skills` | 39 |
| `occupational_tasks` | 0 |
| `workforce_observations` | 247 |
| `ai_impact_evidence` | 20 |
| `academic_standards` | 12 |
| `sdg_references` | 186 |
| `evidence_ingestion_jobs` | 23 |

There are no fabricated standalone occupational-task taxonomy rows; professional task text is stored in the AI evidence cards where supported. Review means an explicit agent engineering source check, not independent human academic approval. Direct source metadata and dates must accompany later use.

## Workforce radar and actual examples

`GET /api/v1/evidence/workforce-trends?before_id=...&after_id=...` returns `RISING`, `DECLINING`, `STABLE` or `INSUFFICIENT_DATA`, raw absolute/percentage deltas, compatible population/unit/classification/period checks, selected thresholds, complete source observations and a method fingerprint. Default relative threshold5%, absolute0, both inclusive for nonzero directional change. These are configurable screening thresholds, not statistical significance.

Actual DOSM broad-group **job-advertising** Q1→Q2 2026 comparisons:

| Published group | Before | After | Absolute change | Percentage change | Classification | Relative threshold |
|---|---|---|---|---|---|---|
| Professionals | 315768.00000000 | 285907.00000000 | -29861.00000000 | -9.4566% | DECLINING | 5% |
| Elementary Occupations | 4070.00000000 | 4646.00000000 | 576.00000000 | +14.1523% | RISING | 5% |
| Unclassified | 0E-8 | None | None | unknown | INSUFFICIENT_DATA | 5% |
| Technicians and associate professionals | 93987.00000000 | 86512.00000000 | -7475.00000000 | -7.9532% | STABLE | 10% |

The technicians example deliberately demonstrates the documented **10% policy override**; it is DECLINING at the default 5% policy. STABLE does not mean zero change or statistical proof of stability. All results are short-term and have `sustained_trend_supported=false`. These are group-level advertisements, not individual occupation/skill demand, employment, hires or AI-caused declines. Annual sector shares remain context and abstain from occupational-demand classification.

`GET /api/v1/evidence/occupations/{id}/ai-transformation` is independent. Only reviewed observed-capability/practice task evidence with an explicit reviewed occupation identity, source date, task and capability can activate `AI-TRANSFORMING`. Exposure/forecast alone cannot. Exact occupation bridges are still unreviewed for this acquired ESCO subset: checked water-engineering/animation occupations correctly return INSUFFICIENT_EVIDENCE, not a manufactured positive. Synthetic tests cover AI-transforming combined with rising and declining demand; no such genuine combined occupational example is claimed from broad DOSM groups. See docs/18_WORKFORCE_TRENDS.md.

## Acquisition accounting: all registry rows

The original 73 research rows are retained, with two explicitly registered alternative artifacts (legacyESCO and officialUNresolution). MANUAL_REQUIRED/ SKIPPED rows not attempted in this bounded run are not claimed to be tested remote failures. Counts below are normalized records; ILO's76 page candidates and the curriculum's37 unreviewed titles are explicitly distinguished.

| Dataset | Access Method | Status | Records Imported | Source Date | Errors / scope |
|---|---|---|---|---|---|
| `A-XMUM-DIRECTORY` | Phase 2 responsibility | SKIPPED | 0 | Unknown | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-BROCHURES` | Phase 2 responsibility | SKIPPED | 0 | 2026-10 (Communication brochure); listing 2026-10-01 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-01` | Protected raw PDF API → existing worker | UPLOAD_COMPAT_VERIFIED | 37 | Unknown (HTML); brochure listing updated 2025-12-22 | 37 unreviewed uploaded title candidates, 0 verified; full document metadata/pages/hash retained |
| `A-XMUM-02` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-11-14 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-03` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2026-02-25 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-04` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-08 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-05` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-06 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-06` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-11-28 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-07` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-11-28 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-08` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2026-10-01 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-09` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-13 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-10` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2026-04-17 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-11` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-06 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-12` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-12-04 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-13` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-24 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-14` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-24 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-15` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-12-15 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-16` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-12-17 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-17` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-12-15 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-18` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2026-03-30 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-19` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2026-03-30 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-20` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2026-10-01 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-21` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-06 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-22` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-06 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-23` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-12-22 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-24` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-11-14 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-25` | Phase 2 responsibility | SKIPPED | 0 | Unknown (HTML); brochure listing updated 2025-10-31 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-MPU` | Phase 2 responsibility | SKIPPED | 0 | 2026-06 | Secondary public-discovery workflow; not acquired by this evidence command |
| `A-XMUM-HANDBOOKS` | Phase 2 responsibility | SKIPPED | 0 | Unknown; listing updated 2026-09-07 for 2027 handbook | Secondary public-discovery workflow; not acquired by this evidence command |
| `B-MQA-DIRECTORY` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQF-2024` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2024 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQA-COMPUTING` | Official PDF, reviewed benchmark cards | IMPORTED_SUBSET | 3 | 2023 edition; January 2024 cover update; 2024-07-31 portal artifact update | academic_standard: 3; narrow attributed research summaries, not full standards or taught-content claims |
| `B-MQA-ACCOUNTING` | Official PDF, reviewed benchmark cards | IMPORTED_SUBSET | 3 | 2024 (edition); 2025 update listed | academic_standard: 3; narrow attributed research summaries, not full standards or taught-content claims |
| `B-MQA-BUSINESS` | Official PDF, reviewed benchmark cards | IMPORTED_SUBSET | 3 | 2021-08 | academic_standard: 3; narrow attributed research summaries, not full standards or taught-content claims |
| `B-MQA-MEDIA` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2025 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQA-FINANCE` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQA-LANGUAGE` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown (linked filename says October 2020) | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQA-BIOTECH` | Official PDF, reviewed benchmark cards | IMPORTED_SUBSET | 3 | 2019 (Second Edition; exact day unknown) | academic_standard: 3; narrow attributed research summaries, not full standards or taught-content claims |
| `B-MQA-HOSPITALITY` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown (June 2019 linked filename) | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQA-TCM` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown (2021 circular listed) | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQA-AI` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown (2025 title/circular) | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-MQA-MULTIMEDIA` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown (2021 circular listed) | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-COMPUTING-BOK` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `B-EAC-2024` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2024 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `C-ESCO` | Current API failed | MANUAL_REQUIRED | 0 | 2025-12-10 (footer update); v1.2.1 release notice December 2025 | Current API unsafe DNS / normal HTML unavailable; use official current export wizard manually with own consent; legacy alternative imported separately |
| `C-MYNSR` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `C-MASCO` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `C-ISCO08` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `C-ONET` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2026-08 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `D-JMI-Q1-2026` | Automatic bounded XLSX | IMPORTED_SUBSET | 11 | 2026-06-25 | workforce: 11 |
| `D-JMI-Q2-2026` | Automatic bounded XLSX | IMPORTED_SUBSET | 11 | 2026-08-18 | workforce: 11 |
| `D-EMPLOYMENT-SECTOR` | Manual official CSV; automatic robots failed | IMPORTED_SUBSET | 225 | 2026-10-08 (dataset last updated) | workforce: 225 |
| `D-MYCOL-2024-25` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown; cycle label is not exact publication date | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `D-MYCOL-2022-23` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown; cycle label is not exact publication date | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `D-MYCOL-2020-21` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown; cycle label is not exact publication date | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `E-TALENTCORP-IMPACT` | Official metadata/terms review only | CONSENT_REQUIRED | 0 | 2024-11-18 (launch); PDF version date Unverified | Group notice §3.3(a)(iii), PDF page 10 requires written consent for aggregation; zero task cards imported |
| `E-MYMAHIR-PORTAL` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2024-11-17 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `E-ILO-2025` | Automatic PDF + narrow reviewed cards | IMPORTED_SUBSET | 11 | 2025-05-20 | pdf_candidate: 76, ai_evidence: 11 |
| `E-OECD-2024` | Official HTML web read; PDF robots denied | IMPORTED_SUBSET | 2 | 2024-04-10 | ai_evidence: 2 |
| `E-HBS-2026` | Official HBS PDF; reviewed cards | IMPORTED_SUBSET | 2 | 2026-03-11 | ai_evidence: 2 |
| `E-METR-2025` | Official primary post web read; local HTTP failed | IMPORTED_SUBSET | 1 | 2025-07-10 | ai_evidence: 1 |
| `E-METR-2026` | Official primary post web read; local HTTP failed | IMPORTED_SUBSET | 1 | 2026-02-24 | ai_evidence: 1 |
| `E-ALAB` | Corrected publisher HTML; reviewed cards | IMPORTED_SUBSET | 2 | 2023-11-29 | ai_evidence: 2 |
| `E-ALAB-CORRECTION` | Published correction via coauthor institutional PDF web read | IMPORTED_SUBSET | 1 | 2026-01-19 | ai_evidence: 1 |
| `E-UNESCO-JOURNALISM` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2023-06-12 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `F-UN-SDG` | API readable, reuse unresolved | MANUAL_REQUIRED | 0 | 2015 | API database rights not assumed; official resolution alternative imported separately |
| `F-UNESCO-ESD` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2017 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `F-OPENLEARN` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown at catalogue level | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `F-OPENLEARN-ACCOUNTING` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2020-04-08 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `F-OPENLEARN-STATS` | Not attempted / manual review | MANUAL_REQUIRED | 0 | 2025-10-15 | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `F-MIT-OCW` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown at catalogue level | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `F-HRD-ELATIH` | Not attempted / manual review | MANUAL_REQUIRED | 0 | Unknown | Not acquired in this bounded run; exact source/rights/edition and import scope require review |
| `A-LEGACY-UNVERIFIED` | Phase 2 responsibility | SKIPPED | 0 | Unknown | Secondary public-discovery workflow; not acquired by this evidence command |
| `F-UN-SDG-RES70-1` | Official resolution PDF; reviewed bundle | IMPORTED_SUBSET | 186 | 2015-10-21 | sdg: 186 |
| `C-ESCO-V103` | Official legacy CSV + partial TTL; reviewed bundle | IMPORTED_SUBSET | 87 | Unknown | skill: 10, occupation: 38, occupation_skill: 39; legacy/multilingual, 34 Arabic labels; not current English ESCO |

## Immutable input identities

Version SHA256 hashes the actual imported bytes (reviewed JSON manifests for manual cards). Original PDF/archive/HTML hashes remain separately in extraction metadata. A partially acquired file never receives a complete-file integrity claim. Publication precision, study dates, observation periods and UTC retrieval are distinct.

| Dataset | Version | Input SHA256 | Counts |
|---|---|---|---|
| `D-JMI-Q1-2026` | `be84354f-0650-4144-97fa-852f141f31bf` | `cbff5d0a62df0a92a6f018d93ba83a5e9b1727e6ec21ecd6b2f33f6ab5ddbb7f` | {'workforce': 11} |
| `D-JMI-Q2-2026` | `7ab66c36-804b-4d72-963c-6c344f392ea9` | `965f2f20bcb33425eb43eac7f9edfcff186e7fa92048b8b26f8ee8bbe5d25764` | {'workforce': 11} |
| `E-ILO-2025` | `5e06086c-14e6-4316-a5e8-3de4c8c3898e` | `9077761c72aabaa3c7ee70999ec5aa46a6afcf943b5fb01baa971f601d363ee9` | {'pdf_candidate': 76} |
| `D-EMPLOYMENT-SECTOR` | `d4745b1b-3504-42c8-a7b7-f1a08ecaae87` | `cad10213d654dcc99e6c28ba104d638f8f00b99d203b8bbbc33cc5ce9c6faeb2` | {'workforce': 225} |
| `E-ILO-2025` | `c63a2f1a-2221-4f80-885a-aab500b87a14` | `45074fabd269f99ef601477c0862cdf3b722250f6fa90a4ac1b8804219b560d6` | {'ai_evidence': 3} |
| `F-UN-SDG-RES70-1` | `af014c51-b59f-49a3-a53d-c3807ef0ce24` | `cda2bf0b4843a94cf09f92513abfd14acf244f7856d25c34315fa5ef823503ed` | {'sdg': 186} |
| `B-MQA-ACCOUNTING` | `61adaf60-9ae4-4438-a638-6b5deb08c722` | `1ea48550553cde299da1212b7884e0afd6bc6a593cb54bd6f5f5c563ca05ee9d` | {'academic_standard': 3} |
| `B-MQA-BIOTECH` | `c9907611-37b6-45e9-82a9-f693c51cf514` | `35d6dc7e721f99958283c119a4eb349d1bccbe4fb13e64fcd05e8c4c55b534c4` | {'academic_standard': 3} |
| `B-MQA-BUSINESS` | `fa8ac2f1-68f7-4a34-aa43-edc511d4acd2` | `9cf40d1853f748aa184a59281961d3daa5ee8e6a80b1f98b16a53dc9536543d7` | {'academic_standard': 3} |
| `B-MQA-COMPUTING` | `99329517-ec2f-4c78-b1e5-a8ea04c1c0bf` | `4788ade4fa95313a9c52eaa3de60eaa797df9d1616124e31b7df46497a487830` | {'academic_standard': 3} |
| `E-ALAB-CORRECTION` | `7fd39e44-d296-4190-87a1-6a8af38b325a` | `2fd6f5b5bde25b8528842e4b6f3ee183c8e13c3097dced5beede01df0955366d` | {'ai_evidence': 1} |
| `E-ALAB` | `f5e97fa9-c438-4093-bb2d-7d8e98102efb` | `31a1f7638f2a367bd16ae7de23c5a004901074c4f81a52eb7daffd398e86d052` | {'ai_evidence': 2} |
| `E-HBS-2026` | `45c0c862-3bd3-408e-9e1a-16a849b8b0ea` | `3f7615e36d51f8c7e8ea9fb799ad07aa566900c00abe7105ba46e704aab47566` | {'ai_evidence': 2} |
| `E-ILO-2025` | `29f3c3ef-4073-4f90-a86d-5a7f8ad5c1bc` | `d204f3befcaedd20eae28fc3fff6dd3ffbc57e460b058e83fcd7e3d03d2e3feb` | {'ai_evidence': 8} |
| `E-METR-2025` | `a9212543-70c4-48b6-9fa4-71a993683840` | `5ea739e9c87d18db62006ed93a220eef8b0d06c7867b73bd89f93ffc5647041f` | {'ai_evidence': 1} |
| `E-METR-2026` | `fa488fcf-28fe-4876-85d6-e97a8f81bd75` | `98e09a182a37207468f8e3c2cab7555865e7111320cb1da551c292cce33495fd` | {'ai_evidence': 1} |
| `E-OECD-2024` | `c83d8f76-5918-4f9f-96a7-dcdc753e5662` | `a5477a23625f8d3ecffcabfb96fcc9ef8cd49cc50194538a360ef1a2466d9f02` | {'ai_evidence': 2} |
| `C-ESCO-V103` | `98056d41-dcae-43aa-9aed-37cac89ee1e6` | `d60fce025f86c17eaf95c34ad154947206298065398d12988b4d0c33d679ec96` | {'skill': 10, 'occupation': 38, 'occupation_skill': 39} |

## Validation and compatibility

The existing schema is reused. No new migration beyond 0004 is needed for radar or upload jobs; all 13 Phase 3 tables and Phase 1–2 history remain compatible. API schema changes have tests. Original uploads, extracted catalogues and page anchors commit together; forced coverage/result failures prove rollback. Source-class validation permits only narrow capability-free exposure context from workforce sources and refuses relabelling it as observed capability or forecasts. Genuine permitted packs have automated persistence/provenance/replay tests, separate from synthetic engineering tests.

| Final command / check | Measured result |
|---|---|
| PostgreSQL-enabled full pytest, `.pytest-phase3-completion-release` | **487 passed, zero failed/skipped**, one existing upstream deprecation warning; 42.42s |
| PostgreSQL integration tests included | **8 passed**: migrations/history/guards plus pipeline replay/radar API |
| Ruff lint and format | PASS; 133 Python files formatted |
| Dependency integrity (`pip check`) | PASS |
| PostgreSQL migration SQL (`alembic upgrade head --sql`) | PASS; all four revisions compile |
| Whitespace (`git diff --check`) | PASS |

Checks caught and corrected result-validation atomicity, future/malformed comparison metadata, contextual exposure/source-class admission and fixed-cardinality test fixtures. The final complete suite was rerun after the corrections. No failed test was accepted and no remote CI pass is claimed.

## Remaining restrictions and recommended next step

| Requested acceptance gate | Measured assessment |
|---|---|
| Genuine cross-disciplinary occupation–skill mappings | Met for the frozen legacy multilingual subset; current English completeness remains open |
| Traceable academic benchmarks | Met for 12 narrow bachelor summaries in four disciplines; full/current applicability needs academic review |
| Official SDG reference data where permitted | Met: 17 goals and 169 targets from the official resolution, with a separate document rights basis |
| Reviewed AI task evidence across a useful range | Met as source-checked engineering cards with dates/limitations; independent academic validation and exact taxonomy bridges remain open |
| PDF compatibility or explicit limitations | Met: real Accounting upload/worker/replay verified; unsupported layouts/scans documented |
| Genuine historical workforce comparisons | Met at published broad-group advertising/sector-context granularity |
| Four demand classifications and edge cases | Met in tests and real-data examples; the stable example explicitly uses a 10% policy override |
| AI transformation separate from demand | Met; no exposure-only activation or fabricated genuine combined occupation result |
| Queryable real records with evidence | Met through PostgreSQL joins and typed API/provenance queries |
| Existing/new automated checks | Met: 487 tests, including eight PostgreSQL integration tests; lint/format/dependencies/migration checks pass |

This readiness assessment authorizes no academic decision and certifies no complete/current taxonomy or curriculum. A later Phase 4 proof must retain abstention and all source limits rather than treat the imported subset as comprehensive.

1. Current English ESCO needs the official export/wizard with the operator's own consent/email; no identity was submitted. The legacy multilingual subset is not a replacement claim for a current complete English taxonomy. Review currentness and mappings before academic use.
2. TalentCorp/MyMahir Group notice §3.3(a)(iii), PDF page 10 requires written consent for aggregation/copying; §3.3(b) restricts networked reuse. Only bibliographic metadata/terms were reviewed, no evidence cards or full48MB report imported. Obtain publisher permission or an explicitly licensed export; no provider was contacted.
3. MQA summaries cover four disciplines and scoped research use only. Full standards/commercial redistribution, current amendments, Engineering/EAC and other discipline applicability need separate review. Stanford's accounting summary also remains a permission/manual-original candidate, not imported evidence.
4. Malaysian detailed occupational time series and reviewed MASCO/ISCO/ESCO bridges remain unavailable. The radar must continue to abstain at unsupported granularity. No individual-role demand was manufactured.
5. Uploaded PDF support is bounded; other layouts/scans and detailed syllabi can require manual handling. Private upload authentication is the existing catalogue token guard, not full production identity/tenant isolation.
6. Human academic review, broad current coverage, deployed access controls and production operations remain later gates. The next authorized development should be a small conservative Phase4 proof using frozen source versions, all uploaded course appearances, explicit insufficiency and independent demand/AI evidence; do not assume those later features exist now.

## Changed files

- .env.example
- .gitignore
- AGENTS.md
- README.md
- STATUS.md
- alembic/versions/0004_reference_evidence.py
- data/dataset_registry.csv
- data/evidence_acquisition.json
- data/reference_packs/README.md
- data/reference_packs/esco-v1.0.3.selected-source-blocks.ttl
- data/reference_packs/esco-v1.0.3.subset.reviewed.json
- data/reference_packs/un-sdg-resolution.reviewed.json
- docs/01_PRODUCT_REQUIREMENTS.md
- docs/02_ARCHITECTURE.md
- docs/03_DATA_MODEL.md
- docs/06_ANALYSIS_ENGINE.md
- docs/08_SCENARIOS_SDG_AND_REPORTING.md
- docs/10_API_CONTRACT.md
- docs/12_MVP_ROADMAP.md
- docs/16_PHASE2_CURRICULUM_INGESTION.md
- docs/17_PHASE3_EVIDENCE_INGESTION.md
- docs/18_WORKFORCE_TRENDS.md
- docs/DATASET_RESEARCH.md
- docs/DATA_ACQUISITION_PLAN.md
- docs/DATA_GAPS.md
- docs/PHASE3_INGESTION_REPORT.md
- fixtures/evidence/dataset_registry.synthetic.csv
- fixtures/evidence/policy.synthetic.json
- fixtures/evidence/records.synthetic.json
- prompts/04_RELEVANCE_ENGINE.md
- prompts/06_SCENARIOS_REPORTS.md
- pyproject.toml
- requirements.lock
- src/shiftos/api/body_limit.py
- src/shiftos/api/routers/catalogue.py
- src/shiftos/api/routers/evidence.py
- src/shiftos/api/routers/workforce_radar.py
- src/shiftos/cli.py
- src/shiftos/core/config.py
- src/shiftos/main.py
- src/shiftos/models/__init__.py
- src/shiftos/models/evidence.py
- src/shiftos/repositories/evidence.py
- src/shiftos/schemas/evidence.py
- src/shiftos/schemas/workforce_radar.py
- src/shiftos/services/evidence/__init__.py
- src/shiftos/services/evidence/acquisition.py
- src/shiftos/services/evidence/parsers.py
- src/shiftos/services/evidence/pipeline.py
- src/shiftos/services/evidence/registry.py
- src/shiftos/services/evidence/trends.py
- src/shiftos/services/ingestion/catalogue.py
- src/shiftos/services/ingestion/fetcher.py
- src/shiftos/services/ingestion/pdf.py
- src/shiftos/services/ingestion/uploads.py
- src/shiftos/services/ingestion/worker.py
- tests/test_curriculum_pdf.py
- tests/test_curriculum_upload.py
- tests/test_evidence_api.py
- tests/test_evidence_migrations.py
- tests/test_evidence_parsers.py
- tests/test_evidence_pipeline.py
- tests/test_evidence_review_regressions.py
- tests/test_evidence_source_classes.py
- tests/test_migrations.py
- tests/test_reference_packs.py
- tests/test_workforce_radar.py

The pre-existing untracked .idea directory was left untouched. No automatic commit or push was performed.
