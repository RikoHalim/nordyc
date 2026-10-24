# Roadmap — retain Phase 1, advance one phase at a time

The existing foundation is adapted to revised requirements. STATUS records measured acceptance; this roadmap is not evidence a gate passed. Implement only the authorised phase and stop after reporting results.

## Preliminary MVP sequence

| Phase | Deliverable | Acceptance boundary |
|---|---|---|
| 1 — Foundation adaptation | Retain FastAPI/PostgreSQL, versioned multi-programme catalogue; add source/provenance metadata and create/read APIs | Preserve old records/importer; multi-programme/API/provenance/migration tests; actual results in STATUS |
| 2 — Discovery | All publicly discoverable XMUM undergraduate links/course titles/year/elective metadata; manual fallback | Diverse HTML fixtures, idempotency/versioning, truthful real-source access/verified counts |
| 3 — Evidence | Standards, occupations/skills, dated workforce/AI references, radar and upload compatibility | Functional bounded prototype: genuine legacy/multilingual taxonomy, narrow benchmarks, official SDGs, research/workforce records; currentness/coverage/permission limits remain explicit |
| 4 — Relevance | Internal-first hybrid retrieval, controlled research fallback and one configured LLM; conservative assessment of every available course | Frozen citations, verified permitted fallback, deterministic trends, diverse disciplines, title-only/insufficiency gates; no invented scores |
| 5 — Actions | Supported primary action, alternatives/no change and human review | Weak evidence -> review; redesign evidence gate; pending approval |
| 6 — Scenarios/SDG/report | Moderate/accelerated assumptions and evidence replay | Traceable changes, unrelated discipline stability, explained SDG links |
| 7 — Integration | Offline clean-setup demo, evaluation, source-access safeguards | End-to-end without private keys; measured coverage/abstention |
| 8 — Minimal UI/demo | Programme explorer, evidence inspector, actions/scenario comparison | Real endpoints; synthetic/unknown states visible; reproducible proof |

Preliminary requirements are a proposal covering intended full delivery and a rough live proof of the key capability, with accessible GitHub. Production readiness is not required. Prioritise a defensible vertical slice and honest coverage. Catalogue target: all discoverable XMUM undergraduate programmes; deep validation: a small diverse subset first. Do not promise content-level evidence for every course.

## Phase 4 implementation order — planned, not started

Planning revised **24 October 2026**. Phase 3 remains functional for a bounded MVP; its currentness, rights, language and reviewed-mapping limitations are inputs to the sufficiency gate. Use [the analysis specification](06_ANALYSIS_ENGINE.md) and [hybrid retrieval contract](19_PHASE4_HYBRID_EVIDENCE_RETRIEVAL.md). No Phase 4 code is authorized by this planning revision.

1. Define run/course coverage, evidence packet and gap contracts; select the one approved existing LLM and approved search provider. The repository currently has no runtime model connection. Define configuration, use/privacy rules, permissions and minimal additive persistence/job changes before live egress.
2. Implement PostgreSQL retrieval of occupations/skills, applicable standards, workforce and AI records. Check scope, review basis, publication/observation dates, freshness and completeness. Return all available courses, including explicit insufficient-evidence cases; retain deterministic workforce calculations.
3. Add a configurable, bounded external research adapter for important gaps. Verify claims in original authoritative sources; preserve URLs, dates, permitted excerpts and provenance; import/cache only as permitted. Apply allowlists, existing transport safeguards, rate/time/query budgets and restricted-source/manual outcomes. Recheck internal evidence after imports.
4. Connect the single configured LLM to admitted evidence only. Validate structured output, final citations, claim scope, title-versus-syllabus limits and abstention. Keep offline synthetic fixtures and explicit unavailable-provider outcomes.
5. Validate at least three diverse disciplines, internal-only/no-network success, a genuine permitted fallback smoke test, cache/replay/versioning, negative security/rights cases and Phase 1–3 regressions. Apply/test additive migrations only during implementation. Report actual results and source/model blockers, update STATUS and stop before Phase 5.

An insufficient-evidence result is a correct outcome for an unsupported claim. Passing offline fixtures does not prove live research or model integration. Phase 4 completion must disclose any blocked real-source/provider gate rather than claim broad/current coverage. Action generation, scenario work and frontend remain later phases. See the [planned test matrix](11_TEST_PLAN.md#phase-4-hybrid-retrieval-tests-planned).

## Final-round expectations and unresolved scope

The original final product requires six features: skills intake, dated trends, future-role matching, personalised pathways, explained SDG mapping and multiple future scenarios. No blanket institutional waiver is confirmed. Only institutional framing and CV-upload exemption are reported accepted. Obtain written confirmation for programme profiles vs personal skills, occupation alignment vs person-role matching and academic plans vs personalised pathways. See docs 09; preserve the gap in STATUS.

Do not automatically add CV/personal functionality. A synthetic learner adapter is an option only if later confirmed necessary and explicitly requested. Track any final-round rubric separately from preliminary engineering acceptance.

## Post-hackathon

After the tested MVP and confirmed requirements: on-demand discovery for another institution, wider discipline validation, production authorisation/admin imports, stronger source lifecycle monitoring, backups/deployment and academic reviewer evaluation. Extend existing boundaries as needed. Nationwide crawling, recruitment/payment/event scheduling and unsupported predictive metrics remain outside the roadmap.

## Team boundaries and stop rules

Research owns organiser clarification/pitch; data owns sources/rights; backend owns migrations/APIs/jobs; AI owns grounding/evaluation; frontend/integration helps testing before the UI gate. Agree shared schemas first. No chatbot, national crawler or automatic course authoring. No phase, commit or push starts automatically from this roadmap.
