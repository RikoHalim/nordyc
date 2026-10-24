# Future Workforce Radar methodology

Implemented within Phase 3. This service calculates changes in persisted workforce observations and retrieves task evidence independently. It does not analyse courses, recommend academic changes or predict future employment. No new table, migration, external request, AI model or startup job is required.

## API and reproducibility

`GET /api/v1/evidence/workforce-trends?before_id=<UUID>&after_id=<UUID>&percent_threshold=5&absolute_threshold=0` compares exactly two stored observation records. The caller selects the source vintages explicitly. Missing records return the existing 404 error envelope; malformed IDs or invalid thresholds return 422. The calculation writes no result or observation records.

The response contains `classification` (`RISING`, `DECLINING`, `STABLE`, `INSUFFICIENT_DATA`), absolute and percentage changes, baseline status, compatibility/rejection reasons, population and measurement scope, period type, horizon, policy, independent AI attribute and a SHA256 fingerprint. Both original observations include their complete version, source and evidence reference, including original locator, checksum, publication-date precision and retrieval timestamp. The fingerprint covers the serialized result and method version, excluding the fingerprint itself; it changes when inputs, linked evidence or thresholds change. No current clock or mutable registry lookup affects a calculation.

`GET /api/v1/evidence/occupations/{id}/ai-transformation` retrieves the independent AI attribute even when occupational demand observations are unavailable. Existing `/ai-impact` and `/workforce-observations` lists remain independently queryable. Neither new endpoint triggers ingestion.

## Compatibility and population boundaries

Comparisons require the same series, publisher, occupational identity or exact published label, classification system/code, sector, geography, indicator, unit and synthetic status. Population dimensions also match exactly: `population`, `sex`, `age_group`, `citizenship`, `employment_status`, `industry`, `classification_version`, `methodology`, `sampling_frame`, `seasonal_adjustment`, `source_granularity`, and any source-specific `metadata_json.dimensions` object. A missing dimension on one side does not match a supplied value on the other. Unknown dimensions remain unknown; matching within a published series is not independent validation of its methodology.

Manual observation imports should provide stable `metadata_json.series_id` and `population_level` (`occupation`, `occupation_group`, `all_occupations`, `sector`, or an explicit unsupported value), with source population/methodology dimensions where applicable. Linked occupations use exact taxonomy/external identifiers across snapshots. No MASCO/ISCO/ESCO crosswalk or fuzzy name match is invented.

Existing immutable imports remain usable without rewriting history. The known `dosm_jmi` adapter identifies DOSM JMI Summary Table 2 as one series and marks its published rows as broad occupation groups or an all-occupations total. Exact table-title and published-label agreement are required. The `employment_sector` adapter identifies annual sector/sex employment shares as sector context. These adapter contracts describe source granularity; they never expand a group observation into its constituent occupations.

Source and observation synthetic flags must agree. Sources must be `dated_workforce_signal` or explicitly `synthetic_demo`. Rejected references are inadmissible. Structured parsed references may remain `needs_review`; the response preserves that review status and does not promote it to verified interpretation.

## Periods and calculations

Full calendar months, quarters and years are recognized from their exact dates. Different calendar lengths caused by month lengths or leap years remain compatible for the same period type. If a supplied `metadata_json.period_type` disagrees with those dates, comparison is refused. A custom interval is supported only with `period_type="fixed_days"` and identical day counts. Overlapping, reversed and repeated periods are refused. Gaps are retained rather than silently filled or annualized.

An observation ending after its stored retrieval timestamp or an exact known publication day is rejected. The check uses stored source dates rather than the current clock, keeping replay deterministic. Malformed population/series metadata abstains visibly instead of producing a classification or server error.

For compatible finite, nonnegative, published values:

- Absolute change = after − before, in the original unit. For percentage-share indicators this is a percentage-point difference.
- Percentage change = 100 × (after − before) ÷ before. Decimal arithmetic uses a local precision of 50 significant digits; no floating-point or display rounding is used for threshold decisions.
- A zero baseline produces a null percentage change. Zero to positive is `INSUFFICIENT_DATA` under the percentage-threshold policy; zero to zero is `STABLE`. A missing or suppressed value remains missing/inadmissible and is never replaced with zero.

The default relative threshold is **5%**, with an absolute threshold of **0 original units**. Both thresholds must be met inclusively for a nonzero change to be `RISING` or `DECLINING`; otherwise the result is `STABLE`. Equality is stable even when both thresholds are zero. These are transparent engineering screening defaults, not statistical-significance or publisher thresholds. Thresholds are included in every response. They are configurable per request, with finite nonnegative values; relative thresholds are bounded to 1000 and absolute thresholds to 10^18.

Supported occupational indicators distinguish `online_job_offerings`, `job_postings`, `job_offerings` (advertising), `vacancies` (unfilled positions), and `employment_count` (employment). The classification describes the direction of that specific indicator, not interchangeable measures of demand. Employment shares, sector-only populations, unknown indicators, missing series or unresolved population granularity return `INSUFFICIENT_DATA` for occupational demand. Compatible sector shares can still return their arithmetic changes as context.

Two monthly/quarterly observations spanning at most 366 days are labelled `short_term`. Other compatible pairs are `two_period_comparison`. **Every two-point result has `sustained_trend_supported=false`**, including annual or widely separated endpoints. No sustained-trend detector is claimed. Seasonality, changing platform coverage and measurement uncertainty remain explicit limitations.

## Independent AI transformation attribute

`AI-TRANSFORMING` is separate from observed demand direction. A result may be `RISING` or `DECLINING` while its independent AI attribute is `AI-TRANSFORMING`. Missing admissible evidence returns `INSUFFICIENT_EVIDENCE` with a null flag; it does not assert that AI has no effect.

Activation requires reviewed occupation identity and evidence, a dated `dated_ai_capability` source (or consistent synthetic lane), a documented task and capability, and `impact_type` equal to `observed_capability` or `observed_practice`. An exact linked occupation ID is admissible. Cross-snapshot identities or exact labels additionally require the operator assertion `metadata_json.occupation_match_reviewed=true`, with an exact matching `occupation_taxonomy` + `occupation_external_id`, matching `classification_system` + `classification_code`, or exact `occupation_label`. Conflicting supplied taxonomy/classification identifiers are refused even if labels match. Review remains an operator assertion, not independent academic approval.

Exposure and future-prediction cards can appear as linked evidence with explicit exclusion reasons, but cannot activate transformation. Missing tasks/capabilities/dates, unreviewed references, inconsistent synthetic lineage and retracted/superseded/correction-pending cards are excluded. Source dates, study periods, setting and limitations remain visible. Documented task capability does not establish widespread adoption, displacement or Malaysian effects. Broad workforce groups never receive an individual occupation's AI attribute.

## Measured real-data example

The stored DOSM JMI `Professionals` broad-group observations are 315,768 for Q1 2026 and 285,907 for Q2 2026, both `job_offerings`. Their difference is **−29,861**, approximately **−9.45662638%**. At the default threshold the result is `DECLINING`, scoped to the published occupation group and labelled `short_term`; it supports no individual-occupation, skill-demand, sustained-trend or AI-causation conclusion. The source vintages are 25 June 2026 and 18 August 2026. Exact evidence and version hashes are returned by the endpoint and documented in [the ingestion report](PHASE3_INGESTION_REPORT.md).

## Later-phase use

Phase 4 may retrieve these source-bound directional indicators and AI task evidence independently as conservative review context. A direction or AI attribute cannot establish university teaching content, course obsolescence or a replacement decision. Phase 6 scenarios must state their assumptions separately; historical observed changes must not be relabelled forecasts. This implementation stops at Phase 3 intelligence infrastructure.
