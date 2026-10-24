# MVP checklist and judge walkthrough

The target is an institution-facing proof for Malaysian university career centres and academic reviewers. XMUM is the preconfigured pilot; other Malaysian institutions remain supported by later on-demand extension. **Phase 4 implementation is the current priority. Future Career Alignment (Phase 5), Academic Reskilling Pathways and scenarios/action reporting (Phase 6) are planned, not currently available features.** Use [STATUS](../STATUS.md) for measured delivery, source coverage and blockers.

## MVP feature checklist

| Capability | Delivery boundary | Demo claim allowed |
|---|---|---|
| Select institution/programme; upload available brochure/curriculum/syllabus | Existing catalogue/upload/extraction foundation, subject to reviewed candidates and layout limits | Show actual imported records, origin links and unknown fields; detailed syllabus/CV/budget not mandatory |
| Programme-wide analysis of every available course | Phase 4, current implementation priority | Show measured results only when available, including every appearance and explicit insufficient-evidence/provider-unavailable cases |
| Cross-disciplinary occupation/skill, dated workforce/AI and academic evidence | Phase 3 bounded evidence foundation implemented | Show actual queried records and source dates/limits; do not claim complete/current national coverage |
| Evidence-backed academic recommendation and comparison | Phase 5 planned | Minimum sufficient supported primary action, alternatives/no change and pending human review; present only as a labelled plan until implemented |
| Future Career Alignment | Phase 5 planned, within existing career/skill alignment | Source-linked programme-to-occupation requirements versus supported curriculum intent/unknowns; optional reproducible score, never personal employment probability |
| Academic Reskilling Pathways | Phase 6 planned, within decisions/action plans | Ordered objectives/activities/prerequisites, assessed practical limits, verified resources and duration bases; no invented taught outcomes or full course content |
| Scenario comparison and selective reassessment | Phase 6 planned | Moderate/accelerated assumptions separate from observations; traceable changed/unchanged results, no fake job forecasts |
| Meaningful SDG links and consolidated Academic Action Plans | Phase 6 planned | Explained official goal/target links, sources/unknowns, interventions/pathways/scenarios and pending approval |
| Minimal UI and clean offline demonstration | Later integration/UI gate | Actual endpoints or prominently labelled synthetic preview; no production readiness claim |

The catalogue target is all publicly discoverable XMUM undergraduate programmes. Validate the engine deeply on a small diverse subset first. University uploads are primary; public discovery is secondary. Do not add recruitment, ERP/student tracking, event booking or additional agents to complete this checklist. Budget/planning period are optional at later feasibility comparison.

## Live proof now versus intended completed MVP

For the current proof, show only working backend capabilities and measured Phase 4 results, using API inspection if the UI is not available. A planned interface, mocked provider or synthetic scenario must be labelled before it is shown. Missing keys or source permissions remain explicit blockers; offline tests do not prove a live LLM/research call.

The following is the **intended end-to-end walkthrough after the relevant phases pass acceptance**, not a statement that these screens or capabilities exist today:

1. Select XMUM and a programme, then upload an available university brochure/curriculum or syllabus. Inspect extraction, original links and uncertain year/elective candidates. Show catalogue gaps without demanding a detailed syllabus.
2. Open a few genuinely available programmes from diverse disciplines. Analyse the full selected inventory, including courses with insufficient evidence; do not demonstrate only favourable course results.
3. Explain a title-only result: “Review whether this competency is covered,” rather than “This competency is absent.” A benchmark does not prove what XMUM teaches.
4. Show genuine dated occupation/skill, academic and AI references, and a compatible workforce comparison. State broad-group/short-term limits, legacy editions and unmatched classifications.
5. In Future Career Alignment, inspect relevant source-backed occupations and requirements against documented curriculum intent/unknowns. A potential gap is a review hypothesis until supported; omit a score if evidence is insufficient.
6. Compare the supported primary academic action with smaller interventions and `no_change`, including why each is adequate, conditional or unsupported. Human reviewer status stays pending.
7. Inspect an ordered Academic Reskilling Pathway: target competency, proposed objectives/activities, prerequisites, duration basis, verified original resource and assessment limits. A seminar attendance certificate is not technical competency.
8. Compare moderate/accelerated AI adoption assumptions, then replay a genuine changed evidence snapshot or an explicitly synthetic fixture. Explain affected and unaffected outcomes; a no-change result is valid.
9. Inspect the consolidated draft Academic Action Plan, source dates/rights, meaningful SDG rationale, unknowns and next evidence needed. A draft is not an approved curriculum change.
10. End with remaining data/organiser questions, rather than claiming all university teaching or individual graduate skills were audited.

## 30-second value proposition

“NORDYC helps university reviewers connect available curriculum evidence with traceable occupational, workforce and AI developments. It makes unknowns visible, identifies questions worth investigating and will compare proportionate academic interventions and learning pathways before people decide what to change.”

## Questions judges may ask

- **Why not just a generic chatbot?** Versioned sources, claim-specific evidence gates, deterministic signal calculations, auditable curriculum coverage and human review. Describe only implemented validation as delivered.
- **How do you know a course is outdated?** A title cannot establish that; review prompts and syllabus confirmation are explicit. AI exposure is not obsolescence.
- **Does alignment predict employment?** No. A future optional score would describe declared curricular-evidence alignment, with method/coverage limits and abstention.
- **Do pathways prove students gained skills?** No. Objectives are proposed; attendance/completion does not prove technical competence. Appropriate assessed practical evidence can support only its tested scope.
- **Is this every Malaysian university?** XMUM pilot, diverse bounded validation and later on-demand institutional extension; no nationwide crawl or complete-content claim.
- **Where are personal matching and personalised pathways?** The institutional substitution remains **UNCONFIRMED** in [the compliance matrix](09_HACKATHON_COMPLIANCE.md). CV-upload exemption is narrower. A lightweight individual contingency is planning only, pending clarification and authorization.

Preliminary priorities remain a defensible working proof, an honest proposal covering intended delivery and an accessible repository. This planning revision does not authorize publishing changes or starting Phases 5/6.
