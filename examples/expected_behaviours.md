# Expected behaviours for the synthetic pilot

These are **rules/acceptance examples**, not outputs validated by a university or labour-market analyst. Codex should use them as assertions, not train a model to copy these conclusions.

1. **Whole programme:** import all fixture courses; analysis returns a record for each. No course is skipped because its syllabus is incomplete.
2. **Inventory-only course:** course `SE404` has `detailed_syllabus_available=false`; course relevance is `INSUFFICIENT_EVIDENCE`, no invented CLOs, and any recommendation should request information (not automatically retain).
3. **Foundations:** a software testing syllabus that teaches manual test design may remain valuable even though synthetic dated signals discuss AI-assisted test generation. The machine should consider a **targeted update or workshop** rather than conclude elimination.
4. **Programme-level elective:** possible only if evidence shows a relevant competency not sufficiently addressed across multiple courses and other lower-disruption responses appear inadequate. With weak information, recommend further review instead.
5. **Changed signal snapshots:** `SYN-Q1` and `SYN-Q2` differ on AI-assisted test-generation practice. An updated snapshot can raise review priority with an explicit reason. It must not pretend to forecast jobs lost or force changed recommendations if evidence is still insufficient.
6. **Workshop:** a hypothetical practical assessment may support a pilot competence claim when measured. A career talk or seminar's attendance does not.
7. **Human approval:** recommendations start as `PROPOSED`; no model response can approve them.
8. **Integrity:** every claim references real fixture anchors/source passage IDs; model-invented IDs cause validation failure.
9. **No auto-obsolescence:** no course classified unnecessary simply because an AI model can produce an output once done by humans.
10. **Scenario:** assumptions are visible; no invented accuracy, placement rates, future salaries or labour market projections.
