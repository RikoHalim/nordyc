# 09 — Decisions and Open Questions

## Locked decisions

- Malaysia only for current MVP; country is a backend constant/config, not onboarding selector.
- Target: institutional / career-centre academic decision support; no student-facing CV intake in current prototype.
- Primary input: **complete programme curriculum** and supporting syllabus docs; include all courses in analysis, not one selected course.
- Do not require manually entered competency percentages or AI relevance scores.
- Do not require budget, timeline, lecturer availability during initial setup; these can be optional intervention constraints later.
- LLM makes a **proposed recommendation** from validated evidence; alternatives and human academic approval are mandatory.
- One Workshops & Industry Engagement category with four formats; standalone workshops and optional curriculum pilots both supported.
- Two AI uncertainty scenarios + evidence update replay; avoid made-up future employment statistics.
- Backend first, frontend after tested API.

## Open questions — do not silently invent answers

1. **Hackathon eligibility:** user said organisers approved university framing and said CV upload isn't necessary. Original Domain 1 feature list included individual matching and personalised reskilling. Ask organisers whether **all** individual-level requirements are exempt or whether a small representative pathway example is expected. Avoid building unrequested student-profiling features until clarified.
2. **Detailed official syllabi:** public course names are not enough. Which actual complete detailed syllabus files can the team legally use? If none, use clearly synthetic samples and classify real records as insufficient evidence.
3. **Data licensing/availability:** official Malaysian source bulk/API access and licence must be verified. Use transparent curated snapshots until confirmed.
4. **Academic approvals:** which department/faculty signs off on course changes in the target institution? Keep human-review generic in MVP.
5. **Gemini/API**: choose an API provider/key separately; a consumer subscription does not necessarily include API usage. Build provider abstraction; Phase 01 must not require an API key.
6. **Deadline / team readiness:** schedule depends on actual hackathon dates and developer availability; no exact durations promised.
7. **Relevance thresholds:** need transparent validation examples reviewed by domain experts; avoid pretending an objective percentage of relevance is available.

## Out-of-scope creep warning

If a suggestion adds unrelated dashboards, job marketplace, student CV parsing, automatic full course writing, event booking, regional expansion, investment/market features, human-skills tests or AI agents, explicitly mark it **DEFERRED** unless necessary to satisfy confirmed event requirements.
