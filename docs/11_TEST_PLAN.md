# Test and acceptance plan

## Phase gates

1. **Foundation:** application starts; migrations up/down on a clean test DB; CRUD on institution -> multiple programmes -> multiple courses; nullable year/elective; documented errors; no API key required.
2. **Discovery:** official-like HTML fixtures representing several disciplines; year parsing; link provenance; missing semester remains null; parser failure visible; idempotent re-import; timeouts and rate limits mocked.
3. **Evidence pipeline:** source dates and provenance persisted; multiple dated snapshots; source claims and unit types checked; occupation-level metric not cast as skill statistic; deterministic offline fixture import.
4. **Relevance:** whole-programme returns **all courses** even if insufficient evidence; title-only never yields definitive obsolete/update verdict; no evidence -> unknown; standard != teaching evidence; source references are resolvable.
5. **Actions:** valid primary recommendation and alternatives incl `no_change`; high-evidence gate for redesign; missing data yields review not invented action; attendance alone cannot increase assessed skill coverage.
6. **Scenario/report:** two scenario results; date-stamped evidence replay changes only affected results; SDG reasoning not empty; reports distinguish verified and provisional outcomes.
7. **Hardening:** duplicate prevention, cross-programme isolation, input validation, SQL injection mitigation, request logging free of secrets, offline deterministic run, end-to-end fresh setup reproducibility.
8. **UI:** select XMUM -> see all programmes -> run full-programme analysis -> navigate to course evidence -> compare AI-suggested action vs no change -> run scenario -> report. Show meaningful empty/unknown states.

## Critical negative tests

- Input official course title only -> **no claim of actual taught topics**.
- Unverified publisher/URL -> **cannot cite as verified campus fact**.
- Changing irrelevant labour signal -> **should not alter unrelated major findings**.
- Source removed/invalid -> system flags inadequate evidence instead of hallucinated citation.
- Synthetic snapshot -> UI and API label it as synthetic.
- If LLM returns unknown JSON or fabricated URL -> reject/correct by grounding validator.
- Same document imported twice -> zero duplicate courses/sources (unless legitimate different years/tracks).

## Evaluation: don't claim model accuracy without a labelled benchmark

Compare output on a hand-reviewed set of public/synthetic cases from at least 3 disciplines; report agreement rates, citation accuracy, abstention on missing data, false-confidence examples and limitations. Avoid arbitrary thresholds disguised as independently validated performance.

## Demo reproducibility

No live external API calls required for baseline demo. One command sequence starts DB, applies migrations, seeds **synthetic** fixtures and runs tests, documented in README after implementation. Optional live source can be switched on to demonstrate genuine dated refresh.
