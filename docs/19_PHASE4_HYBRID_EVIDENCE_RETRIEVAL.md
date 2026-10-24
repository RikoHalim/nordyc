# Phase 4 hybrid evidence retrieval — implementation plan

Planning revision: **24 October 2026**. This document specifies future Phase 4 work; it does not describe an implemented research service, LLM connection, API or migration. Phase 1–3 remain unchanged. Read alongside the [analysis specification](06_ANALYSIS_ENGINE.md), [Phase 3 runbook](17_PHASE3_EVIDENCE_INGESTION.md), [workforce methodology](18_WORKFORCE_TRENDS.md) and [test plan](11_TEST_PLAN.md).

## Existing infrastructure and intended extension

Reuse FastAPI, PostgreSQL, the versioned programme catalogue, evidence repositories, source-specific ingestion adapters and bounded HTTP transport. PostgreSQL is the primary evidence store. The bounded Phase 3 catalogue contains genuine records with incomplete coverage, legacy/multilingual taxonomy and unresolved identity/permission limits; database presence alone does not establish fitness for a particular claim.

Phase 4 adds a small analysis coordinator, internal retrieval and sufficiency policy, an interchangeable approved-search adapter, original-source verification, and one citation-bounded LLM adapter. Use ordinary services and a durable worker, without additional agents, model training, a knowledge graph or a mandatory vector database. Search indexes or deterministic lexical matching can start small; similarity is a candidate match, not an occupation identity or verified curriculum fact.

**Model prerequisite:** the repository currently has no runtime LLM client or configured provider/model integration. The intended design uses one existing, user-approved model through one configurable adapter when implementation is authorized. Record its actual provider/model identifier; do not invent an existing integration or introduce a second model for research, verification or analysis. A disabled/unavailable model must remain visible; deterministic offline fixtures exercise the contract without claiming live LLM analysis.

## Internal-first workflow

```text
Staff select programme and upload available curriculum/brochure/syllabus
  -> existing extraction worker + review of coverage/ambiguous course candidates
  -> freeze programme revision and inventory of every available course appearance
  -> retrieve PostgreSQL occupation/skill, standards, workforce and AI records
  -> check relevance, scope, quality, dates, rights and coverage per question
  -> sufficient: freeze eligible evidence pointers
     gap: bounded approved search -> original source -> verification/rights checks
          -> permitted verified facts imported/versioned -> retrieve and recheck
          -> unresolved/blocked/ambiguous: record INSUFFICIENT EVIDENCE
  -> deterministic workforce calculations over compatible observations
  -> one configured LLM explains only the admitted evidence and explicit unknowns
  -> schema + citation + evidence-policy validation
  -> immutable programme/course findings for human academic review
```

1. An authorized analysis request queues work; no searching, PDF parsing or model call blocks the HTTP handler. Extraction must finish first. Unsupported layouts or uncertain inventory coverage stay visible; do not describe the inventory as a certified complete curriculum. All extracted course appearances receive a result, including unverified candidates and those with no admissible evidence.
2. Internal retrieval selects explicit versions and the genuine or explicitly synthetic lane. It considers discipline, qualification level, country, taxonomy edition, language and task/occupation granularity. Retrieve occupational skills/tasks, applicable MQA or professional benchmarks, dated workforce observations and separate AI capability/exposure/practice evidence. A benchmark is never evidence of university teaching.
3. A deterministic sufficiency check records which questions each reference can support and which remain unanswered. Required evidence depends on the claim: an occupation link needs a supported identity/mapping; a recent demand statement needs compatible dated observations; a syllabus-content statement needs verified document content. Count of hits, an allowlisted domain or a model confidence score cannot satisfy these checks.
4. Important missing, outdated, conflicting or insufficient evidence automatically schedules fallback **when the operator has enabled and configured an approved provider and the source/use policy permits it**. Research targets the specific gap, not every dataset or every possible profession. A sufficient internal result makes no external request. Recheck internal storage after verified imports; never loop indefinitely on a gap.
5. Disabled research, missing credentials, exhausted budgets, forbidden reuse, unavailable originals or unresolved mappings produce explicit gap reasons and `insufficient_evidence` where the requested conclusion is unsupported. Preserve supported dimensions and all courses. External availability must not decide whether an otherwise valid programme run can return a useful partial report.
6. Freeze the final evidence manifest before model analysis. Record the initial internal snapshot, acquisition attempts and accepted additions. A later refresh creates a new run; late worker writes cannot alter a completed run. Replaying a completed run uses its frozen inputs, without new research.

## Evidence eligibility and freshness

Each retrieved item must expose evidence class, source/version/reference ID, relevance basis, claim scope, publication date and precision, observation/study period where applicable, retrieval time, language, review basis, limitations and rights/use decision. Missing values remain unknown. A new retrieval timestamp does not make an old finding current.

| Evidence family | Eligibility and freshness decision |
|---|---|
| Occupations and skills | Preserve original IDs, labels, taxonomy/edition and relation type. Check supersession and mapping review. Legacy ESCO may support a labelled historical benchmark, not a claim to current complete English coverage. Do not silently translate Arabic labels or guess MASCO/ISCO/ESCO bridges. |
| Academic standards | Verify publisher, discipline, qualification/accreditation level, edition, effective dates and amendments. A narrow MQA summary cannot establish full programme compliance or taught content. Unknown applicability is a gap. |
| Workforce | Use original indicator, geography, population/classification, periods, values and units. Version the expected release cadence and recency policy for a claim about current conditions. Historical observations remain valid historical evidence after newer releases arrive. |
| AI impacts | Keep publication date separate from study period, model/tool version and task setting. Preserve corrections, conflicting results and observed capability/practice versus exposure and forecasts. An old experiment cannot prove a current general capability. |
| University documents | Separate uploaded origin/asserted metadata from verified official title, description or syllabus content. Publication/effective-cohort date is not upload time. Full syllabus verification requires document/page support and the review basis; upload alone is insufficient. |

Configure freshness by family and publisher cadence/edition rather than one universal expiry. Record the policy version and analysis `as_of` time; unknown dates cannot support a time-sensitive claim. An ordinary current run freezes its final retrieval cutoff after bounded research completes. Evidence published or first acquired after an explicitly selected historical as-known cutoff is excluded; do not move that cutoff to admit later discoveries. Relevant older evidence may remain as labelled context. Conflicts are preserved and may reduce sufficiency; search ranking cannot settle them.

Existing Phase 3 `review_status` must be preserved. Source-attributed structured rows can still have `needs_review`: a validated deterministic adapter may support the exact published value with that caveat, as in the existing radar. They are not academically verified findings. Automatic PDF pages, ambiguous model interpretations, rejected references and unsupported identity bridges are inadmissible as verified claims. A source-checked excerpt establishes what the source reports, not that the study is universally true or that an academic reviewer approved it.

## Controlled external research

The search provider only discovers candidates. Prefer original government/statistical and standards bodies, universities, peer-reviewed research, professional/accreditation bodies and credible primary research publications. Publisher/discipline allowlists and use rules are operator-managed. A newly discovered domain needs policy approval before original-source acquisition; a public search result does not expand the fetch allowlist. Do not silently substitute a different search provider or an unrestricted browser agent when the approved adapter fails.

Keep configuration modular: enabled flag, approved provider/credential reference, source allowlists, permitted formats, per-source use/retention rules, family freshness policy, cache lifetime, search/document/model budgets and worker deadline. These are planned settings, not existing environment variables. Credentials remain server-side. Provider queries must use approved structured parameters, never a user-supplied endpoint or arbitrary request headers.

Use explicit finite ceilings for queries per gap, gaps/documents per programme, bytes/pages, retries and total elapsed time. Proposed MVP starting limits are **two queries per gap, ten queries and ten original documents per programme, and a 180-second research budget**, whichever is reached first; log truncation and abstain on remaining gaps. Operators can narrow these limits for a provider's terms. Reuse the existing acquisition defaults of 20-second request timeout, at least two seconds between requests per host, at most three attempts and 5 MB responses unless a specific reviewed policy requires a different bound. A total deadline overrides retries; honour rate limits and Retry-After without sleeping past it.

Validate HTTPS origins, public DNS/IP pinning, redirects, media types, archive expansion and document limits using the existing transport. Respect robots and publisher/API terms, login, CAPTCHA, paywalls and licensing; fail visibly with manual instructions. Do not weaken protections to fetch a new source. Search API terms govern query/result use separately from original publisher rights. Research must not run on backend startup or through an unrestricted public ingestion trigger.

Use generic discipline, task, qualification and occupation terms in search queries. Do not send private uploaded text, filenames, student/staff identifiers or credentials to search providers. Restrict analysis/result access to the requesting institution/operator; the existing catalogue token is not full tenant authorization. Before a real external LLM receives private curriculum content, document the approved processing/retention policy and authorization, minimise context, and redact personal data. Without that policy, use permitted public excerpts or return a processing limitation. Do not add mandatory personal-data inputs.

Fetched documents, search snippets and uploaded text are untrusted data. Embedded instructions cannot change tools, allowlists, credentials, prompts, budgets or write privileges. The model has no unrestricted network/database tools; services own retrieval and validation. Audit logs contain IDs, decisions and sanitized errors, not credentials, full private documents or restricted excerpts.

## Verification before admission

For every candidate claim:

1. Resolve and retrieve the original publication through the allowed transport, or use an administrator-supplied permitted original with an explicit operator assertion. Preserve original/canonical URL, publisher, title and actual retrieval time. A search snippet, aggregator, model-generated URL or bibliography entry alone is insufficient.
2. Check format/integrity and capture the original hash where the artifact can lawfully be processed. Preserve publication-date precision, effective edition, observation/study dates and exact page/table/cell/section locator. Record access/rights basis and verifier/method/version/time.
3. Check the specific claim against the original passage/table: labels, units, population, dates, taxonomy, task, scope and limitations. Preserve a minimal allowed evidence excerpt, the supported paraphrase and any correction/retraction. Exact structured values can be checked deterministically. A PDF table must retain usable headers and cell/page context; uncertain extraction stays a candidate.
4. Assign the existing evidence class and AI subtype without conflating them. Check identity/crosswalk evidence explicitly; a name similarity is not a reviewed mapping. Do not turn an occupation count into skill demand, an exposure estimate into observed capability, or an external standard into an XMUM fact.
5. Keep candidate, source-checked and human academic review decisions distinct, with reasons and attribution. Model-produced interpretations remain candidates until source-support checks pass; ambiguous PDF interpretation or consequential content/compliance claims require explicit review. The same model agreeing with itself is not independent verification. Unsupported claims stay `needs_review`/rejected and cannot fill the gap.
6. Validate typed normalized data and citation resolution before admitting a fact to a run. A citation must support the associated claim, not merely point to a real source. For material disagreements, retain both evidence pointers and an uncertainty explanation; do not manufacture a consensus.

Automated source checks can admit narrow supported facts according to their adapter policy; they do not replace human academic decisions. An allowlist establishes an allowed origin, not factual correctness, reuse permission or automatic review approval.

## Storage, provenance and permission-aware cache

Reuse `sources`, `datasets`, `dataset_versions`, `evidence_references` and the separate occupation/skill/task, workforce, AI and standards tables. New reusable sources must have a registry identity and explicit acquisition/use policy; an analysis must not silently mutate the checked-in registry. Unknown sources can remain discovery metadata pending operator registration. Existing version-local composite FKs still apply. Cross-version/taxonomy mappings need explicit reviewed bridge provenance rather than inserting incompatible relationships.

Persist verified findings for reuse only when the source policy allows that use. Preserve source URL/title/publisher, original/derived hashes, dates/precision, exact locators, evidence class/subtype, verification basis and limitations in the version/reference lineage. Keep original bytes and permitted excerpts private or distributable according to their separate rights. Store only bibliographic pointers, gap status and access/manual instructions where content retention is prohibited or unclear; do not cache snippets/full text through search logs or model prompts. Transient processing and reporting of excerpts also require permission, not merely an absent storage operation. If a permitted reproducible evidence pointer cannot be retained, exclude the claim from a persisted substantive finding.

The future analysis manifest links programme revision, admitted record/version/reference IDs, deterministic workforce inputs/method/thresholds, gap decisions, retrieval/verification policy, research attempts, `as_of`, synthetic lane and model/prompt/schema versions. Add only the minimum analysis-run/finding and research-attempt/cache metadata missing from the existing schema, with additive migrations/tests during implementation. Existing curriculum jobs require an institution/revision; do not force unrelated external imports into them. Reuse the separate evidence import jobs for normalized imports and design the analysis worker's durable lifecycle explicitly.

Cache discovery metadata separately from admitted facts. Keys include normalized nonprivate query, discipline/geography/language, taxonomy/edition, provider and policy version; evidence reuse additionally checks source/content/version, permissions, review state and the run's freshness needs. Apply configured bounded TTLs to discovery and negative/blocked results. A failed query is never evidence that a skill, course topic or occupation does not exist.

Admitted facts remain immutable historical versions. New bytes, parser or transformation context create a new version under the Phase 3 rules; a new retrieval alone does not duplicate rows. Refresh and deduplication are idempotent and concurrency-safe. Policy withdrawal, correction/retraction or changed rights must invalidate future cache admission and flag affected prior findings; preserve lawful audit metadata and apply retention/deletion obligations rather than overwrite history silently. Do not automatically rerun unrelated programmes. Repeated model calls may vary even with frozen inputs: retain the validated output and input/version manifest for audit, without promising identical regenerated prose.

## Analysis contract and abstention

The single configured LLM receives a bounded evidence packet containing admitted IDs/excerpts, curriculum evidence level, deterministic indicators and unresolved gaps. It provides qualitative reasoning and review questions; it does not invent statistics, fetch its own sources or calculate workforce trends. Continue using the [Phase 3 deterministic method](18_WORKFORCE_TRENDS.md), including `INSUFFICIENT_DATA`, population limits, threshold policy and independent AI admission.

Pydantic/JSON-schema and application checks validate every returned course ID, source pointer, claim type and eligibility, including the final serialized findings after any repair or assembly. Fabricated references, unknown fields, unsupported quotations or unsupported definite conclusions fail closed. Permit only a bounded repair attempt with the same evidence and same model; otherwise return an explicit processing/insufficiency result, not unvalidated prose. A failed model call cannot be reported as a successful evidence-backed analysis.

Each course result includes its inventory/evidence level, review flag, supported rationale or targeted review question, source/version/reference locators and dates, relevant deterministic indicators, research outcome, missing-evidence reasons, disagreements and `is_final_curriculum_verdict=false`. Display **INSUFFICIENT EVIDENCE** for `insufficient_evidence`; retain `needs_syllabus_confirmation` independently where title-based benchmarking cannot establish content. Zero supporting references permits only an explicit insufficiency/missing-data explanation, never a substantive verdict. A partly supported report must expose unsupported dimensions and overall coverage.

Claims about documented topics/objectives require source-verified passages at the matching official-description or syllabus evidence level; detailed syllabus/assessment claims require those actual passages. Title-only courses support preliminary benchmark questions, without content assertions. A detailed syllabus is optional, and even a verified syllabus describes documented intent rather than measured student competence. Declining occupation demand, high AI exposure or their combination cannot establish course obsolescence or replacement. Absence of a named AI course does not establish absent AI teaching. Academic decisions remain with university reviewers. Academic interventions, option comparison, scenarios and frontend changes remain outside Phase 4.

## Implementation sequence and completion gates

1. Agree typed run/coverage/evidence-packet contracts and the single approved model/search provider configuration. Establish source/use/privacy policies and additive persistence/job changes, without rewriting Phase 1–3.
2. Implement internal retrieval and deterministic claim-specific eligibility/freshness checks across at least three diverse disciplines. Return all courses with honest gaps before enabling fallback.
3. Add bounded automatic research on important gaps, original-source verification, permission-aware imports/cache and durable attempt reporting. Verify idempotency and frozen-run replay with mocked providers first.
4. Connect the one configured LLM; enforce grounding/schema validation and title-versus-syllabus rules. Maintain deterministic synthetic offline fixtures and explicit model-unavailable behavior.
5. Run targeted then full relevant tests, PostgreSQL migration/history checks and an opt-in permitted real-source smoke test proving discovery → original verification → import/query → cited finding. Report blocked sources and coverage honestly. Update STATUS and stop before Phase 5.

Acceptance requires both internal-only/no-network success and a controlled fallback path, plus successful abstention for unavailable/restricted/ambiguous evidence. Genuine smoke results must identify the actual provider/model, datasets, versions, queries/import counts and citations; mocked fixtures do not establish live research success. Missing external credentials/permissions may leave the live gate blocked while offline tests pass. The [testing matrix](11_TEST_PLAN.md#phase-4-hybrid-retrieval-tests-planned) defines the required negative cases. This planning revision itself implements none of these components.
