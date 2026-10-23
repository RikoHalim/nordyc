# Dataset acquisition priority

Verified/reviewed: 24 October 2026. Priorities apply to the narrow artifact or subset described here. They do not authorise bulk crawling or override access/licence conditions. Exact IDs and access states are in [the registry](../data/dataset_registry.csv).

## Obtain these five families first

| Order | Source family and exact initial artifacts | Why now / completion gate |
|---|---|---|
| 1 | `A-XMUM-DIRECTORY`, `A-XMUM-BROCHURES`, `A-XMUM-01` through `25`, `A-XMUM-MPU` | All observed public undergraduate main-course lists; retain missing fields and shared-course uncertainty. Gate: all 25 directory entries accounted for as imported/partial/blocked, with origin links; no fabricated completeness. |
| 2 | `B-MQA-DIRECTORY`, `B-MQF-2024`, `B-MQA-COMPUTING`, `B-MQA-ACCOUNTING`, `B-MQA-BUSINESS`, `B-MQA-MEDIA` | Cross-disciplinary bachelor's benchmarks. Gate: edition/circular/applicability and rights checked; start with reviewed metadata/pointers, not an unlicensed stored full-text corpus. |
| 3 | `C-ESCO`, `C-MASCO` | Stable occupation/skill identifiers plus Malaysian classification context. Gate: pin ESCO v1.2.1 English; obtain actual CSV headers or permitted small API subset; reviewed occupation links, unresolved MASCO crosswalks retained. |
| 4 | `D-JMI-Q1-2026`, `D-JMI-Q2-2026` | Two real dated Malaysian workforce releases. Gate: preserve the two files, verify units/headers/observation periods, snapshot hashes and release-specific provenance. |
| 5 | `E-ILO-2025`, `E-HBS-2026` | Reusable cross-disciplinary exposure and observed task evidence, with uncertainty. Gate: small checked annex/evidence-card subset, model/evaluation date distinct from publication date; no displacement forecasts from exposure. |

Use the direct access links in [DATASET_RESEARCH](DATASET_RESEARCH.md) and the registry. No email registration, paid purchase or data-provider contact was performed during research.

## Exact P0 package — essential for preliminary MVP

- **Curriculum:** all A IDs listed in order 1. The programme sources have P0 priority for discovery/import coverage, not full analysis depth. Current inspected directory count is 25; future runs must rediscover rather than hardcode that count.
- **Standards:** all six B IDs in order 2. Acquire current applicable versions at execution; the verified MQF 2024 text may require later addenda. Narrow metadata/link-based benchmarking remains usable if full-text rights are unresolved.
- **Taxonomy:** `C-ESCO`, `C-MASCO`. MyNSR bulk availability is not an MVP dependency.
- **Dated workforce:** `D-JMI-Q1-2026`, `D-JMI-Q2-2026`, both separate as-published artifacts.
- **AI:** `E-ILO-2025`, `E-HBS-2026`. The latter was published in 2026 but evaluates 2023 GPT-4 context.
- **Hackathon support:** `F-UN-SDG`, `F-OPENLEARN`: target identifiers/links plus a small manually verified resource catalogue. No full course content or automatic official SDG crosswalk is needed.

This is 42 registry rows, mostly the 25 university programme sources, rather than 42 large files. Do not measure progress by download volume. Acquisition is complete only when permitted records are validated and their coverage is reported; that has not happened yet.

## P1 — strengthen analysis after the core is secured

| IDs | Narrow acquisition | Material benefit / dependency |
|---|---|---|
| `B-MQA-FINANCE`, `B-MQA-LANGUAGE`, `B-MQA-BIOTECH`, `B-MQA-HOSPITALITY`, `B-MQA-TCM`, `B-MQA-AI`, `B-MQA-MULTIMEDIA` | Relevant bachelor sections and circulars, one discipline at a time | Extend depth beyond initial demonstration; currently full-file details remain partly unverified |
| `B-COMPUTING-BOK` | One bachelor BOK workbook | Easier structured academic benchmark if fields/rights validated; computing-only |
| `B-EAC-2024` | BEM/EAC standard, with actual jurisdiction checked | Required before a deep engineering compliance comparison; direct EAC 403 needs permitted alternative |
| `C-MYNSR`, `C-ISCO08` | Selected local role references and necessary international classification definitions | Better Malaysian vocabulary/task bridge; licensed export and crosswalk remain open |
| `D-EMPLOYMENT-SECTOR` | Small CSV, 2024 and 2025 slices with metadata | Survey employment context, not occupation/skill demand; useful fallback and corroboration |
| `D-MYCOL-2024-25`, `D-MYCOL-2022-23` | Selected occupation entries and scope/method pages | Shortage detail; do not compare totals across different sector coverage |
| `E-TALENTCORP-IMPACT` | Two or three relevant official sector chapters/reports | Malaysian transition context; inspect rights and treat projections as foresight |
| `E-OECD-2024` | Selected business/skills findings and methods | More nuanced non-Malaysian skill evidence; proprietary microdata not required |
| `E-METR-2025`, `E-METR-2026` | Paired study/follow-up cards | Software counter-evidence and correction of stale generalisations |
| `E-ALAB`, `E-ALAB-CORRECTION` | Corrected experiment and formal amendment together | Chemistry/materials depth and validation uncertainty; never acquire/use only the stale result |
| `E-UNESCO-JOURNALISM` | Handbook metadata and permitted selected guidance | Media-specific professional competencies; full linked report still to verify |
| `F-UNESCO-ESD` | Selected learning objectives | Evidence for explained sustainability mappings; not an official role crosswalk |
| `F-OPENLEARN-ACCOUNTING`, `F-OPENLEARN-STATS`, `F-MIT-OCW`, `F-HRD-ELATIH` | Verify individual metadata/links fitting actual proposed intervention | Resource diversity, stated duration/cost and missing prerequisites; no whole-catalogue mirror |

## P2 — defer or omit

| IDs | Why deferred |
|---|---|
| `A-XMUM-HANDBOOKS` | Large policy documents; marginal value for first course-list extraction |
| `A-LEGACY-UNVERIFIED` | Inaccessible candidate; use verified current directory; never an admissible source |
| `C-ONET` | Rich tasks, but overlaps ESCO and adds US/SOC crosswalk maintenance; fetch only if a specific task gap justifies it |
| `D-MYCOL-2020-21` | Historical context; not required for dated demo when DOSM pair is available |
| `E-MYMAHIR-PORTAL` | Scraping/aggregation restricted; pursue a licensed export only if public reports prove insufficient |

No priority is assigned to hypothetical APIs or unverified job-board datasets. Nationwide curriculum crawling, entire job-ad corpora, full SDG statistical histories and generic “AI disruption” leaderboards are outside this acquisition package.

## Realistic demonstration boundary

Import all publicly exposed catalogue lists; validate the review workflow first on **Accounting, Communication and Software Engineering**. Add **Chemical Engineering** only after its benchmark/access issues are resolved, or show a science programme as an explicit data-limited case. Marine Environmental Chemistry/Marine Biotechnology are useful subsequent science validation targets and must not inherit computing benchmarks.

For the first three: use 2–3 plausible reviewed occupation mappings per programme, a small traceable skill subset, the same two DOSM release snapshots, and a few task evidence cards. These are acquisition targets, not claims that mappings or analyses are already verified. Every course stays in programme inventory, including ones that require abstention.

Real public evidence can demonstrate directory/list availability, normative comparisons, dated occupation-group context, source inspection and provisional review prompts. Scenario adoption assumptions, optional fictional learner records, budget/staffing constraints and intervention outcome demonstrations must be explicitly `inference` or `synthetic_demo`. Do not relabel real XMUM course content as synthetic detail or fabricate syllabi under real course names.
