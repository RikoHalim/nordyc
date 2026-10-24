# Programme-wide relevance engine — evidence first

**Phase 4 bounded backend implemented; live acceptance pending credentials.** The [operational runbook](21_PHASE4_COURSE_RELEVANCE.md) records actual tests/limits. The [hybrid retrieval contract](19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md) defines source, verification, cache, security and worker boundaries. Existing Phase 1–3 services remain in place; no Phase 5/6 runtime feature is added.

## Core question

> Are the publicly documented programme offerings plausibly aligned with current/foreseeable occupational and AI changes, and which course areas deserve academic review?

## Inputs

`uploaded curriculum/brochure snapshot` (or secondary public discovery) + `internally retrieved dated evidence` + `verified permitted external findings for important evidence gaps` + `supported occupation and standard crosswalk` + `optional syllabus`. Freeze admitted references/versions in the run. Scenario assumptions are separate, labelled inputs when scenario analysis is later authorized.

The primary journey is select programme → upload available documents → review extraction → analyse every available course. Do not require detailed syllabi. Title-only evidence stays preliminary regardless of upload/discovery origin.

## Outputs

1. Coverage inventory: every available course appearance, catalogue verification state, extraction limitations and evidence level (`title_only`, `public_description`, `detailed_syllabus`, missing). Uploading a document does not verify its content.
2. Per-course **review flag** and specific evidence-based investigation question; keep uncertainty visible.
3. Programme-level **possible** coverage questions, overlaps and sequences, conditioned on available documentation. Academic action generation/comparison remains Phase 5.
4. Evidence inspector: permitted excerpt, original URL, publisher/title, locator, publication/observation/retrieval dates, version, verification basis, limitations and alternative interpretation.
5. Retrieval coverage: internal references used, research gaps/attempt outcomes, freshness/rights decisions and unresolved evidence by dimension. Display **INSUFFICIENT EVIDENCE** wherever a requested conclusion lacks reliable support.

## Hybrid evidence workflow

1. Staff select a programme and upload available curriculum/brochure/syllabus documents. Existing extraction and review produce the course inventory; detailed syllabi are optional. Keep uncertain candidates and coverage limitations visible.
2. Retrieve PostgreSQL records first: occupational requirements/skills, applicable MQA/professional standards, dated workforce observations and AI occupational/task evidence. Check quality, relevance, publication dates, edition, geography/granularity, rights and completeness for each proposed claim.
3. Important missing, stale or insufficient evidence triggers bounded authoritative external research when an approved search API/tool and use policy are configured. Prioritise original government, academic, professional and credible research publications. Search snippets and AI-written research are candidates, not evidence.
4. Verify specific claims against original pages/tables, preserve dates/excerpts/locators/provenance and uncertainty, and import/cache verified findings for future use only where permitted. Recheck sufficiency. Unavailable/restricted originals, unresolved identity or ambiguous extraction leave explicit gaps; do not substitute synthetic data.
5. Freeze the evidence packet and deterministic workforce results. One explicit pretrained Gemini model analyses that packet through the direct adapter, with structured output and final citation/scope validation. The adapter exists, but no local credential/model is configured and no live Gemini/Brave call is verified. Offline/missing-provider results disclose their actual mode.
6. Return findings for every available course. An unresolved evidence requirement yields `insufficient_evidence`; title-based benchmark questions also retain `needs_syllabus_confirmation`. Model/research failure must be visible and cannot produce invented rationale.

Run slow work in a durable worker behind authorized job submission. Apply configurable source allowlists, rate/byte/query/time budgets, public-IP/redirect protections, terms/robots and permission checks. Keep external research modular, disabled until configured, and automatic on important gaps once enabled. Cache/version permitted findings; completed runs replay frozen evidence without fresh searches. See the [full retrieval contract](19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md) for admission, privacy, cache invalidation and missing-provider behavior.

## Assessment dimensions (qualitative, not fabricated score)

- Foundational educational purpose: enduring conceptual content (cannot be fully inferred from a title).
- AI/task transformation: cited capabilities and limitations affecting relevant professional tasks.
- Occupational alignment: appropriate roles/skills in Malaysian context (with crosswalk caveats).
- Curriculum currency: compare documented outcomes/topics/assessments **only if available**.
- Future resilience: transferable judgement skills and adaptability (hypothesis when title-only).

## Evidence gates

Phase 4 must consume the [Phase 3 workforce methodology](18_WORKFORCE_TRENDS.md). Preserve `RISING`, `DECLINING`, `STABLE` and `INSUFFICIENT_DATA` with the exact comparison population/metric, periods, thresholds and source versions. They describe observed indicators, not graduate prospects or individual skill demand. Broad-group changes may supply context only; missing detailed occupation observations remain missing. Two-point short-term changes cannot be presented as sustained trends.

Retrieve AI task evidence independently. `AI-TRANSFORMING` may coexist with any demand direction, and requires supported observed capability/practice rather than exposure or foresight alone. A decline must not be attributed to AI by association. A rising role does not automatically justify a new course; a declining role does not justify removing foundational or professional education. All directions can produce investigate/no-change/insufficient-evidence findings depending on actual curriculum evidence. Preserve corrections, disagreements and engineering-review vs academic-review distinctions.

| University evidence | Allowed result | Prohibited conclusion |
|---|---|---|
| Course title + year only | Title-confirmed, possible task impacts and questions for academic review | Taught outcomes, missing AI module, outdated content, definitive replacement |
| Official description | Compare stated objectives and source-referenced requirements; provisional suggestions | Claim actual exams/assessments not published |
| Detailed official syllabus & assessments | More specific content/assessment mapping and review recommendation | Claim perfect competence / automatic hiring outcomes |
| No course evidence | Incomplete catalogue; request review | Fabricated course |

## Deterministic approach

Internal retrieval, rule-based sufficiency checks, controlled research on gaps, original-source verification and supported matching precede the LLM's **citation-bounded explanations**. Workforce trends continue to use the deterministic Phase 3 calculations; the LLM cannot recompute them or invent skill demand. Matching suggestions remain inferences until their identity/support checks pass.

Use one existing approved model through a configurable provider adapter; do not train a model or add a research-model fleet. Preserve model/provider, prompt/schema/rule versions and the evidence manifest with validated results. Keep an explicitly synthetic offline fixture evaluator. Missing model configuration returns an explicit limitation; it does not claim live model analysis. A changed evidence source may justify a new linked run, never silent mutation of a completed result. A substantive verdict with zero admissible citations must fail closed.

## Recommended statuses

`monitor`, `investigate`, `needs_syllabus_confirmation`, `insufficient_evidence`, `validated_action_candidate`; never universally rank courses from title-only data.

Phase 4 emits screening/review findings; `validated_action_candidate` is reserved for the later action-validation phase. A supported benchmark question can be preliminary while the requested content verdict remains insufficient. Preserve the missing evidence and syllabus-confirmation requirement rather than hiding one behind a single favourable flag.

## Relevance example (NOT an XMUM audit)

Verified: course titled `Software Quality Engineering` exists. Independently sourced: AI-assisted software testing practices are evolving. **Allowed**: "Review whether assessments cover critical evaluation of AI-generated test artifacts"; **not allowed**: "XMUM does not teach AI testing".

## Programme-level inference

Absence of a course named `Responsible AI` is **not evidence** the content is not taught anywhere else. Frame as "verify coverage of responsible AI across relevant courses".

## Handoff to planned career alignment and pathways

Current structured results preserve every course, five dimensions, scoped quotations, review questions, limitations, source/version/locator/date/rights metadata and deterministic programme context. Verified curriculum quotations can support later competency review; they are not already normalized skill coverage. [The enhancement plan](22_CAREER_ALIGNMENT_AND_PATHWAYS_PLAN.md) identifies later typed competency assertions, reviewed occupation/skill mappings, potential-gap and confidence contracts. Title-only coverage stays unknown. Phase 5 will own Future Career Alignment and minimum sufficient actions; Phase 6 will own ordered Academic Reskilling Pathways/Action Plans. Those additions remain documentation only and do not expand Phase 4 into academic recommendations.
