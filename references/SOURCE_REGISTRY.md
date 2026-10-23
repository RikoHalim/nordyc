# Candidate source registry — verify availability, coverage and rights during Phase 2–3

These are starting-point URLs, not API contracts or downloaded dataset files. Check site terms, dates, license and availability at implementation time.

| Source | URL | Intended use | Restrictions/limits |
|---|---|---|---|
| XMUM Undergraduate Programmes | https://www.xmu.edu.my/undergraduate-programmes | Official undergraduate degree directory | Course details depend on programme page; coverage varies |
| XMUM Downloads | https://www.xmu.edu.my/index.php/admissions/download | Public programme brochures when present | PDF data varies, not verified syllabi |
| MQA Programme Standards directory | https://www2.mqa.gov.my/qad/v2/types3new.cfm | Discipline-specific academic benchmark standards | Verify current/version, not actual course delivery |
| TalentCorp MyNSR | https://mynsr.talentcorp.com.my/ | Malaysian occupation–skill descriptions | **Not** complete national occupation coverage (pilot coverage); check reuse |
| TalentCorp MyCOL | https://www.talentcorp.com.my/mycol | Malaysia shortage occupations and context | Published snapshots/reports; no invented quarterly skill frequencies |
| DOSM Job Market Insights | https://www.dosm.gov.my/ | Occupation-level dated Malaysian job signals | Find release-specific Excel/PDF, preserve units and periods |
| ESCO Downloads | https://esco.ec.europa.eu/en/use-esco/download | Cross-disciplinary occupations/skills | Not Malaysian demand; check version and attribution |
| TalentCorp Impact Study | https://www.talentcorp.com.my/impact-study/ | AI/digital/green transitions in selected sectors | Not every sector/major |
| ILO GenAI Jobs Index | https://www.ilo.org/publications/generative-ai-and-jobs-refined-global-index-occupational-exposure | AI exposure estimates | Exposure != displacement probability |
| UN Sustainable Development Goals | https://sdgs.un.org/goals | SDG official objectives/targets | Explain specific mapping, not decoration |

## Data ingestion checklist

Each source row imported into DB needs source publisher, document name, URL, publication date if known, observation window if any, retrieved_at, country/discipline coverage, method, locator/excerpt, license/reuse review, and any caveats. URL alone is insufficient for a source-backed finding.
