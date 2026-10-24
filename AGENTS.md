# Codex project-wide instructions — SHIFT//OS

This file applies to all development phases. Read `README.md`, `STATUS.md`, and the relevant docs before touching code.

## Product contract

- Target primary user: **Malaysian university career centres**, in collaboration with academic committees/programme leads. Human reviewers, not AI, make academic decisions.
- Initial pilot: **all publicly discoverable XMUM undergraduate programmes/course lists**. Validate engine on a **small set of diverse disciplines first**. Support another Malaysian institution later via on-demand discovery.
- Primary workflow: select programme -> upload available university curriculum/brochure or syllabus documents -> extract course titles/year/elective information -> align with MQA standards, multi-disciplinary occupation/skill mappings, dated workforce/AI evidence -> assess **each programme and each course** -> flag review priorities -> generate evidence-aware academic interventions -> compare options/no change -> scenario/reassessment -> programme action plan. Public website discovery remains a secondary acquisition option.
- University name and programme selection should be minimal; no mandatory detailed syllabus, CV, budget or planning-period inputs. A brochure/title inventory is sufficient for preliminary review. Budget and planning period can be **optional at later feasibility comparison**.
- Every discovered university/course fact must retain a link to its real origin. Never assign made-up syllabi or learning outcomes to a real university.

## Mandatory evidence policy

1. Distinguish `verified_university_fact`, `published_standard`, `occupation_requirement`, `dated_workforce_signal`, `dated_ai_capability`, `inference`, `synthetic_demo`.
2. Title-only course information is **not** proof of content. Return preliminary review prompts and `needs_syllabus_confirmation` where required; **no definitive obsolete / replacement ruling**.
3. MQA/ESCO/occupation standards are programme/occupation **benchmarks**, not evidence that XMUM teaches those exact skills.
4. Occupation-level job counts do **not** establish skill-level demand. AI exposure is **not** replacement probability and does not make a course obsolete.
5. Every recommendation must include at least one admissible evidence pointer or report `insufficient_evidence`; show disagreements, unknowns, source dates.
6. Machine-generated output must be JSON-schema/Pydantic validated; no untraceable claims. No invented programmes, courses, job listings, sources, citations, partners, placement rates or assessment results.
7. With weak evidence, prioritise **investigate/review**, not drastic academic changes. Flag limitations explicitly.
8. SDG tags need an explained, defensible link, not decoration.

## Engineering contract

- Backend first, clear service/repository/provider separation; no hardcoded credentials, mocked source content masquerading as live data, uncontrolled scraping or undisclosed LLM model.
- Maintain a working **offline synthetic fixtures mode** so tests and demo do not depend on third-party APIs/LLM calls. Label synthetic sources prominently.
- Discovery: respect site terms/robots, timeouts, rate limits, retry/backoff and manual import fallback; never assert automated collection has succeeded without persisted verified records.
- Analysis runs must be **versioned, reproducible, observable and idempotent**. Upserting a source shouldn't duplicate courses; changes in evidence should selectively re-evaluate affected results.
- APIs return documented error shapes. Background jobs should not block requests; select an appropriate worker approach in the relevant phase.
- Write migration + tests for each schema/API change. Run targeted tests, then full relevant suite; report failures honestly.
- Avoid complex multi-agent orchestration, knowledge graphs, custom model training, massive nationwide crawling, real student personal data, event scheduling, payment/recruitment integration, fake accuracy metrics.
- Prefer documented tradeoffs and narrow code over oversized frameworks.

## Hackathon brief constraints

- Preliminary: a **rough working proof of the key capability**, clear proposal covering the brief and accessible GitHub repository. Full production product not required.
- Source brief says final product must include **six features**; see `docs/09_HACKATHON_COMPLIANCE.md` for original expectations vs current institutional reinterpretation.
- Organisers reportedly approved institutional angle and no CV uploads; **no confirmed blanket waiver** of personal matching/pathways/SDG/scenarios. Preserve this gap in `STATUS.md` until written confirmation.

## Work protocol

For each phase: inspect -> state smallest implementation plan -> implement only approved phase -> tests/migrations -> update docs/`STATUS.md` -> show changed files, commands, results, risks and next recommended prompt. **Stop**, do not start the next phase automatically. If required input cannot be obtained, build an explicit data-limited fallback rather than invent it.
