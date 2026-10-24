# Roadmap — retain Phase 1, advance one phase at a time

The existing foundation is adapted to revised requirements. STATUS records measured acceptance; this roadmap is not evidence a gate passed. Implement only the authorised phase and stop after reporting results.

## Preliminary MVP sequence

| Phase | Deliverable | Acceptance boundary |
|---|---|---|
| 1 — Foundation adaptation | Retain FastAPI/PostgreSQL, versioned multi-programme catalogue; add source/provenance metadata and create/read APIs | Preserve old records/importer; multi-programme/API/provenance/migration tests; actual results in STATUS |
| 2 — Discovery | All publicly discoverable XMUM undergraduate links/course titles/year/elective metadata; manual fallback | Diverse HTML fixtures, idempotency/versioning, truthful real-source access/verified counts |
| 3 — Evidence | Standards, occupations/skills, dated workforce/AI references, radar and upload compatibility | Functional bounded prototype: genuine legacy/multilingual taxonomy, narrow benchmarks, official SDGs, research/workforce records; currentness/coverage/permission limits remain explicit |
| 4 — Relevance | Internal-first hybrid retrieval, controlled research fallback and one configured LLM; conservative assessment of every available course | Frozen citations, verified permitted fallback, deterministic trends, diverse disciplines, title-only/insufficiency gates; no invented scores |
| 4.1 — Managed Claude | Replit-managed Claude Opus 5 and model/usage audit metadata; Gemini disabled for MVP | Integrated; same academic/privacy contracts retained |
| 4.2 — Live backend | Actual protected API → worker → Claude → PostgreSQL → protected API | COMPLETE for the bounded two-fictional-course proof; real curriculum accuracy is not established |
| 4.3 — Brave evidence | Internal-first research, original-source verification/admission and citation-safe reuse | PARTIAL: one live Brave HTTP200 search passed; unregistered results and original robots verification block new evidence admission |
| 5 — Actions and Future Career Alignment | Programme occupation/competency alignment, potential gaps, primary minimum sufficient intervention, alternatives/no change and human review | Implemented on `feature/phase5-career-alignment`: reviewed exact-source matrix, conservative gaps/optional measures, actions and protected immutable human review. Measured acceptance in Phase 5 runbook; no individual employment probability |
| 6 — Pathways/scenarios/SDG/report | Ordered Academic Reskilling Pathways within Action Plans, verified resources, based duration estimates, moderate/accelerated scenarios and evidence replay | Traceable ordered steps/objectives/prerequisites/resources/duration/SDGs; assessed practice distinct from attendance; unrelated discipline stability; pending authorization |
| 7 — Integration | Offline clean-setup demo, evaluation, source-access safeguards | End-to-end without private keys; measured coverage/abstention |
| 8 — Minimal UI/demo | Programme explorer, evidence inspector, actions/scenario comparison | Real endpoints; synthetic/unknown states visible; reproducible proof |

Preliminary requirements are a proposal covering intended full delivery and a rough live proof of the key capability, with accessible GitHub. Production readiness is not required. Prioritise a defensible vertical slice and honest coverage. Catalogue target: all discoverable XMUM undergraduate programmes; deep validation: a small diverse subset first. Do not promise content-level evidence for every course.

## Current priority — complete Phase 4 validation

The authorised Phase 4 implementation extends the bounded Phase 3 infrastructure. Its [runbook](21_PHASE4_COURSE_RELEVANCE.md) records retained internal retrieval, validation, jobs/persistence/APIs and current Replit-managed Claude configuration. [Phase 4.2](25_PHASE42_LIVE_BACKEND_VERIFICATION.md) is complete for bounded backend integration. [Phase 4.3](26_PHASE43_BRAVE_SEARCH_VERIFICATION.md) is PARTIAL: live Brave search works, but source registration/acquisition and admission still need completion. Existing source/currentness/rights/identity limitations remain explicit.

1. Finish the full relevant offline/PostgreSQL regression suite, migration checks and genuine persisted-evidence API smoke; report actual results in STATUS.
2. Preserve the accepted Replit-managed `claude-opus-5` proof without another paid model request. Gemini stays disabled. Resolve the Phase 4.3 source gate through exact candidate registration/rights review and an admissible original or documented manual-original import; do not disable robots or infer evidence from snippets. Any additional paid Brave request needs new approval.
3. Review missing current taxonomy, standards applicability, curriculum detail, Malaysian occupation bridges and source permissions. Preserve insufficient-evidence outcomes rather than force matches or academic conclusions.
4. Obtain written Domain 1 clarification in parallel. Future feature planning does not grant a waiver or authorization to implement a personal platform.
5. Phase 5 was separately authorised and implemented; review [its measured record](27_PHASE5_FUTURE_CAREER_ALIGNMENT.md). Stop before Phase 6 implementation, frontend or deployment. Source and organiser gates remain explicit.

An insufficient-evidence result is a correct outcome for an unsupported claim. Passing offline fixtures does not prove live research or model integration. Phase 4 completion must disclose any blocked real-source/provider gate rather than claim broad/current coverage. Action generation, scenario work and frontend remain later phases. See the [planned test matrix](11_TEST_PLAN.md#phase-4-hybrid-retrieval-tests-planned).

## Revised Phase 5–6 priorities — documentation only

Phase 5 extends existing Academic Decision Studio logic with programme-level Future Career Alignment and occupational competency-gap analysis, followed by the minimum sufficient primary intervention, alternatives/no change and human review. Phase 6 extends existing scenario/report/Academic Action Plans with ordered academic pathways, duration estimates with explicit basis, verified resources, meaningful SDG links and selective reassessment. No additional standalone module, student tracking, new model or frontend is introduced. Proposed objectives remain future plans; titles and attendance cannot prove skills. Optional alignment scores must explain evidence/weights/method and abstain when coverage is unknown.

## Final-round expectations and unresolved scope

The original final product requires six features: skills intake, dated trends, future-role matching, personalised pathways, explained SDG mapping and multiple future scenarios. No blanket institutional waiver is confirmed. Only institutional framing and CV-upload exemption are reported accepted. Obtain written confirmation for programme profiles vs personal skills, occupation alignment vs person-role matching and academic plans vs personalised pathways. See docs 09; preserve the gap in STATUS.

Do not automatically add CV/personal functionality. A synthetic learner adapter is an option only if later confirmed necessary and explicitly requested. Track any final-round rubric separately from preliminary engineering acceptance.

## Post-hackathon

After the tested MVP and confirmed requirements: on-demand discovery for another institution, wider discipline validation, production authorisation/admin imports, stronger source lifecycle monitoring, backups/deployment and academic reviewer evaluation. Extend existing boundaries as needed. Nationwide crawling, recruitment/payment/event scheduling and unsupported predictive metrics remain outside the roadmap.

## Team boundaries and stop rules

Research owns organiser clarification/pitch; data owns sources/rights; backend owns migrations/APIs/jobs; AI owns grounding/evaluation; frontend/integration helps testing before the UI gate. Agree shared schemas first. No chatbot, national crawler or automatic course authoring. No phase, commit or push starts automatically from this roadmap.
