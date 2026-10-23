# 06 — Data Sources, Integrity and Licensing

## Preferred evidence families (research starting points, not pre-imported datasets)

- **TalentCorp MyNSR**: Malaysian national skills registry / occupation-skill reference. Official entry point: https://mynsr.talentcorp.com.my/
- **TalentCorp MyCOL and AI/Digital/Green Economy studies**: occupation shortage/change framing; verify exact edition, scope and data access rights before using. Official entry point: https://www.talentcorp.com.my/
- **Department of Statistics Malaysia (DOSM)**: official labour, online job offerings and related statistics; distinguish number of job postings by occupation from *skills* required. Official entry: https://www.dosm.gov.my/
- **ESCO**: international occupation/skill definitions for vocabulary mapping, not a substitute for Malaysia-specific demand evidence: https://esco.ec.europa.eu/en/use-esco/use-esco-services-api
- **Academic guidelines**: MQA relevant programme standards; these can constrain approval but do not automatically determine AI relevance: https://www.mqa.gov.my/
- **AI changes**: documented professional/industry standards, reputable studies and qualified technical reports with author, date and concrete supported claim (e.g. testing practices); do not treat promotional claims as proof of full automation.
- **SDGs**: UN Sustainable Development Goals and target text: https://sdgs.un.org/goals
- **Institution-specific**: official XMUM programme list for course inventory, **not** a substitute for uploaded detailed syllabi.

Some sources require manual downloads or licensing review. Do not promise a free/open API or permission to scrape until verified.

## Minimum `EvidenceSource` record

```json
{
  "id": "<local UUID>",
  "title": "...",
  "publisher": "...",
  "url": "https://...",
  "source_kind": "OCCUPATION_SKILLS",
  "published_at": "YYYY-MM-DD or null",
  "observed_start": "YYYY-MM-DD or null",
  "observed_end": "YYYY-MM-DD or null",
  "retrieved_at": "ISO 8601",
  "jurisdiction": "MY",
  "licensing_note": "...",
  "is_synthetic": false,
  "version": "..."
}
```

Store exact source passages, table identifiers, page/section and a *narrow statement* of what the source supports. Keep publication date distinct from the period being measured; a 2026 report might discuss 2025 observations.

## Provenance quality rules

1. Reject evidence passages without a known source ID and meaningful locator.
2. Preserve observed dates, publisher and jurisdiction; flag missing fields and narrow analysis claims accordingly.
3. A claim about emerging *skills* requires skill-level evidence; an occupation posting count alone isn't sufficient.
4. A source saying 'AI can assist testing' cannot establish 'software testing courses are obsolete'.
5. Mapping to standardised skills must disclose ambiguous terms and crosswalk confidence; academic humans may verify.
6. Source version updates yield a new `signal_snapshot`, not an overwrite.
7. Respect licensing and terms of use; prefer public hand-curated JSON/CSV snapshots for a hackathon rather than crawling websites.
8. Synthetic examples must say `is_synthetic: true` at source, passage and analysis/report levels.

## Snapshot replay demo

Start with `SYN-Q1` and `SYN-Q2` (clearly synthetic) and demonstrate the same curriculum analysed against both; compare whether a recommendation changes *and why*. A changed timestamp alone must **not** change the recommendation.

## Data needed from university

**Required:** programme structure, list of compulsory/elective courses and detailed syllabi for any course requiring substantive verdict. Syllabi should ideally include CLOs, content, assessments, credit/prerequisites when available. **Optional later:** constraints, budgets, lecturer resources, facilities and approval timelines. Never fabricate these.
