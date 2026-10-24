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
| 6 — Pathways/scenarios/SDG/report | Ordered Academic Reskilling Pathways within Action Plans, verified resources, based duration estimates, moderate/accelerated scenarios and evidence replay | Implemented on feature/phase6-academic-pathways: exact parent lineage, reviewed resources/effort, two hypothetical scenarios, official target contributions and protected immutable Action Plans. Measured acceptance is in the Phase 6 runbook; production/academic validation remains pending |
| 7 — Integration | Offline clean-setup demo, evaluation, scoped access/source safeguards | Implemented bounded integration and evaluation; measured results in Phase 7 runbook/STATUS; production/academic/organiser gates remain |
| 8 — React workspace/controlled preview | Programme library and upload, course/career intelligence, evidence, pathways/scenarios/SDG and Action Plan review | Implemented against protected endpoints with synthetic/unknown states explicit; local acceptance and separate Replit/public-release gates recorded in STATUS |

Preliminary requirements are a proposal covering intended full delivery and a rough live proof of the key capability, with accessible GitHub. Production readiness is not required. Prioritise a defensible vertical slice and honest coverage. Catalogue target: all discoverable XMUM undergraduate programmes; deep validation: a small diverse subset first. Do not promise content-level evidence for every course.

## Current priority — Phase 8 acceptance and remaining evidence gates

The authorised Phase 4 implementation extends the bounded Phase 3 infrastructure. Its [runbook](21_PHASE4_COURSE_RELEVANCE.md) records retained internal retrieval, validation, jobs/persistence/APIs and current Replit-managed Claude configuration. [Phase 4.2](25_PHASE42_LIVE_BACKEND_VERIFICATION.md) is complete for bounded backend integration. [Phase 4.3](26_PHASE43_BRAVE_SEARCH_VERIFICATION.md) is PARTIAL: live Brave search works, but source registration/acquisition and admission still need completion. Existing source/currentness/rights/identity limitations remain explicit.

1. Preserve the completed Phase 1–8 workflows with offline/PostgreSQL, frontend, browser and migration checks; report the actual current results in STATUS. Local acceptance does not complete the separate Replit runtime/worker/database gate.
2. Preserve the accepted Replit-managed `claude-opus-5` proof without another paid model request. Gemini stays disabled. Resolve the Phase 4.3 source gate through exact candidate registration/rights review and an admissible original or documented manual-original import; do not disable robots or infer evidence from snippets. Any additional paid Brave request needs new approval.
3. Review missing current taxonomy, standards applicability, curriculum detail, Malaysian occupation bridges and source permissions. Preserve insufficient-evidence outcomes rather than force matches or academic conclusions.
4. Obtain written Domain 1 clarification in parallel. Future feature planning does not grant a waiver or authorization to implement a personal platform.
5. Phase 5–8 were separately authorised and implemented; review [career alignment](27_PHASE5_FUTURE_CAREER_ALIGNMENT.md), [Action Plans](28_PHASE6_ACADEMIC_PATHWAYS_ACTION_PLANS.md), [integration/security](29_PHASE7_INTEGRATION_EVALUATION_SECURITY.md) and [the React workspace](30_PHASE8_FRONTEND_REPLIT_MVP.md). Stop after the authorised Phase 8 verification/publication. No merge or public release follows automatically; source, operational and organiser gates remain explicit.

An insufficient-evidence result is a correct outcome for an unsupported claim. Passing offline fixtures does not prove live research or new model execution. The historical Phase 4.2 live Claude proof is separate from the controlled synthetic/mocked Phase 5–8 checks; original-source admission and real academic validation remain incomplete. The React frontend is implemented, while deployment acceptance requires its own observed receipt. See the [test matrix](11_TEST_PLAN.md#phase-4-hybrid-retrieval-tests-planned).

## Implemented Phase 5–6 scope

Phase 5 extends existing Academic Decision Studio logic with programme-level Future Career Alignment and occupational competency-gap analysis, followed by the minimum sufficient primary intervention, alternatives/no change and human review. Phase 6 extends existing scenario/report/Academic Action Plans with ordered academic pathways, duration estimates with explicit basis, verified resources, meaningful SDG links and selective reassessment. Those backend phases introduced no standalone student platform, tracking or new model; the frontend was separately added in Phase 8. Proposed objectives remain future plans; titles and attendance cannot prove skills. Optional alignment scores must explain evidence/weights/method and abstain when coverage is unknown.

## Final-round expectations and unresolved scope

The original final product requires six features: skills intake, dated trends, future-role matching, personalised pathways, explained SDG mapping and multiple future scenarios. No blanket institutional waiver is confirmed. Only institutional framing and CV-upload exemption are reported accepted. Obtain written confirmation for programme profiles vs personal skills, occupation alignment vs person-role matching and academic plans vs personalised pathways. See docs 09; preserve the gap in STATUS.

Do not automatically add CV/personal functionality. A synthetic learner adapter is an option only if later confirmed necessary and explicitly requested. Track any final-round rubric separately from preliminary engineering acceptance.

## Post-hackathon

After the tested MVP and confirmed requirements: on-demand discovery for another institution, wider discipline validation, production authorisation/admin imports, stronger source lifecycle monitoring, backups/deployment and academic reviewer evaluation. Extend existing boundaries as needed. Nationwide crawling, recruitment/payment/event scheduling and unsupported predictive metrics remain outside the roadmap.

## Team boundaries and stop rules

Research owns organiser clarification/pitch; data owns sources/rights; backend owns migrations/APIs/jobs; AI owns grounding/evaluation; frontend/integration owns the controlled workspace and its API, accessibility and browser checks. Agree shared schemas first. No chatbot, national crawler or automatic course authoring. No phase, commit or push starts automatically from this roadmap.

## Phase 7 implementation and Phase 8 boundary

The separately authorised [Phase 7 integration/evaluation/security work](29_PHASE7_INTEGRATION_EVALUATION_SECURITY.md) is implemented on feature/phase7-system-integration, based on published Phase 6 receipt 9149d55bf597d3eef2a10193cceba0d56694e040. It supplies the protected API foundation for the separately authorised Phase 8 frontend. Normalized examples support tests and visual development; their review hashes cannot be submitted as real approvals. Review measured STATUS results and separate academic/security/operations/compliance readiness. Production identity, verified Replit DB/storage/supervision, expert data validation, Brave original-source admission and written organiser clarification remain gates.

## Authorised Phase 8 implementation

The NORDYC React/TypeScript workspace is implemented on feature/phase8-react-dashboard, based on the published Phase 7 receipt. The revised design is reconstructed honestly from its seven screenshots; the older generic React explorer and generated dependencies were not imported wholesale. All required academic views consume protected APIs, with clearly labelled backend-backed synthetic/mocked demonstration and actual upload/review jobs. Controlled local and Replit development-preview acceptance is COMPLETE, with actual database/worker/browser observations recorded in STATUS. The temporary Replit stack was stopped after verification and the original workspace restored; this is a reproducible preview capability, not a currently running public deployment. See [the Phase 8 runbook](30_PHASE8_FRONTEND_REPLIT_MVP.md) and current STATUS for the latest acceptance and publication receipt. Public release still requires separate authorisation plus identity/storage/database/worker/restore/source gates. Do not merge, deploy publicly or introduce an individual/CV workflow automatically.
