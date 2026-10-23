# Cross-disciplinary source strategy

Prioritise **five reusable source families**, but treat many as publications/registries rather than drop-in JSON APIs.

| Family | Reference | Use | Data caveat |
|---|---|---|---|
| University programmes/courses | XMUM official directory and programme/brochure pages | Verified institutional course names and years | Detailed syllabus usually absent |
| Academic benchmarks | Malaysian Qualifications Agency (MQA) programme standards | Expected field competencies | Not evidence of what XMUM actually teaches |
| Occupation/skill taxonomy | TalentCorp MyNSR; ESCO | Role-skill and competency vocabularies across disciplines | MyNSR coverage limited, ESCO not Malaysia demand |
| Dated Malaysian workforce | DOSM Job Market Insights; TalentCorp MyCOL | Occupation-level demand, shortage context, change over time | Don't map aggregate job counts directly to individual skill demand |
| Dated AI-task impact | TalentCorp AI/Digital/Green study, ILO and field-specific studies | Which task types AI impacts, with caveats | Exposure measures not predictive certainty; needs field-specific review |

Useful source starting URLs with verification/reuse notes are in `references/SOURCE_REGISTRY.md`.

## Evidence provenance requirements

For every imported item record publisher, title, original URL, retrieval method, access/reuse status, publication date if shown, observed/measurement period, retrieval timestamp, exact quote/locator and limitations. Never guess publication dates or license rights.

## Scale strategy

- Initial **XMUM full catalogue**; **three or more diverse disciplines** for depth validation; no promise every course gets a full relevance verdict.
- Shared skill/AI facts reused where supported; require discipline and occupation-specific links.
- New Malaysian institutions later discovered **on demand** and cached with lineage; never scrape all Malaysia up front.
- Two dated source snapshots for the demo; use **real and licensed** data where feasible, otherwise synthetic snapshots clearly labelled as simulations. Never mix actual and synthetic values silently.

## Mapping pitfalls

- Programme course titles are not competencies; standards are benchmarks not evidence of delivery.
- A major can lead to many occupations; mapping programme -> jobs is uncertain and should be reviewed.
- MQA documents differ by field/year/version and may change: preserve effective dates.
- Brochures may omit electives, internships, prerequisites; mark gaps rather than 'not offered'.
