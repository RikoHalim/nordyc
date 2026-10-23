# Roadmap — retain Phase 1, advance one phase at a time

The existing foundation is adapted to revised requirements. STATUS records measured acceptance; this roadmap is not evidence a gate passed. Implement only the authorised phase and stop after reporting results.

## Preliminary MVP sequence

| Phase | Deliverable | Acceptance boundary |
|---|---|---|
| 1 — Foundation adaptation | Retain FastAPI/PostgreSQL, versioned multi-programme catalogue; add source/provenance metadata and create/read APIs | Preserve old records/importer; multi-programme/API/provenance/migration tests; actual results in STATUS |
| 2 — Discovery | All publicly discoverable XMUM undergraduate links/course titles/year/elective metadata; manual fallback | Diverse HTML fixtures, idempotency/versioning, truthful real-source access/verified counts |
| 3 — Evidence | Standards, occupations/skills, dated workforce/AI references and two snapshots | Traceable dates/units/classes; synthetic fallback explicit; reuse source registry |
| 4 — Relevance | Conservative whole-programme assessment including every course | Title-only abstention, diverse disciplines, citations, no invented scores |
| 5 — Actions | Supported primary action, alternatives/no change and human review | Weak evidence -> review; redesign evidence gate; pending approval |
| 6 — Scenarios/SDG/report | Moderate/accelerated assumptions and evidence replay | Traceable changes, unrelated discipline stability, explained SDG links |
| 7 — Integration | Offline clean-setup demo, evaluation, source-access safeguards | End-to-end without private keys; measured coverage/abstention |
| 8 — Minimal UI/demo | Programme explorer, evidence inspector, actions/scenario comparison | Real endpoints; synthetic/unknown states visible; reproducible proof |

Preliminary requirements are a proposal covering intended full delivery and a rough live proof of the key capability, with accessible GitHub. Production readiness is not required. Prioritise a defensible vertical slice and honest coverage. Catalogue target: all discoverable XMUM undergraduate programmes; deep validation: a small diverse subset first. Do not promise content-level evidence for every course.

## Final-round expectations and unresolved scope

The original final product requires six features: skills intake, dated trends, future-role matching, personalised pathways, explained SDG mapping and multiple future scenarios. No blanket institutional waiver is confirmed. Only institutional framing and CV-upload exemption are reported accepted. Obtain written confirmation for programme profiles vs personal skills, occupation alignment vs person-role matching and academic plans vs personalised pathways. See docs 09; preserve the gap in STATUS.

Do not automatically add CV/personal functionality. A synthetic learner adapter is an option only if later confirmed necessary and explicitly requested. Track any final-round rubric separately from preliminary engineering acceptance.

## Post-hackathon

After the tested MVP and confirmed requirements: on-demand discovery for another institution, wider discipline validation, production authorisation/admin imports, stronger source lifecycle monitoring, backups/deployment and academic reviewer evaluation. Extend existing boundaries as needed. Nationwide crawling, recruitment/payment/event scheduling and unsupported predictive metrics remain outside the roadmap.

## Team boundaries and stop rules

Research owns organiser clarification/pitch; data owns sources/rights; backend owns migrations/APIs/jobs; AI owns grounding/evaluation; frontend/integration helps testing before the UI gate. Agree shared schemas first. No chatbot, national crawler or automatic course authoring. No phase, commit or push starts automatically from this roadmap.
