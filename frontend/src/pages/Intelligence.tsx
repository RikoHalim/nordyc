import { useState, type ReactNode } from "react";
import { Printer, RefreshCw } from "lucide-react";
import { ApiError, validateResponse } from "../api/client";
import type {
  CareerResult,
  CareerRun,
  Evidence,
  Model,
  Page,
  PlanResult,
  PlanRun,
} from "../api/types";
import { dateLabel, humanise, isPending } from "../api/types";
import { useWorkspace } from "../app/workspace";
import { useResource } from "../lib/resource";
import {
  safeCareerResult,
  safePlanResult,
  useAnalysisResults,
} from "../lib/results";
import {
  Badge,
  Card,
  Citations,
  Empty,
  ErrorState,
  Loading,
  Notice,
  PageHeading,
  ReviewForm,
  Status,
  TextList,
} from "../components/ui";

type Results = ReturnType<typeof useAnalysisResults>;
type Recommendation = Model<"AcademicRecommendation">;
type RecommendationRow = Model<"RecommendationRead">;
const titles: Record<string, string> = {
  industry: "Industry outlook",
  careers: "Future career alignment",
  competencies: "Competency coverage",
  recommendations: "Academic recommendations",
  pathways: "Academic pathways",
  scenarios: "Future scenarios",
  sdg: "SDG contribution",
  plan: "Academic action plan",
  reviews: "Review history",
  evidence: "Evidence & sources",
};
const text = (value: unknown) =>
  typeof value === "string" || typeof value === "number"
    ? String(value)
    : "Not recorded";

function ResultLabels({ run }: { run: CareerRun | PlanRun }) {
  const usage = run.model_usage_json as Record<string, unknown>;
  const actual =
    typeof usage.actual_model === "string" ? usage.actual_model : null;
  const validated = [
    "validated_option_comparison",
    "validated_pathway_review",
  ].includes(String(usage.status));
  const tokens =
    usage.usage &&
    typeof usage.usage === "object" &&
    !Array.isArray(usage.usage)
      ? (usage.usage as Record<string, unknown>)
      : {};
  return (
    <div className="inline-meta">
      <Status value={run.status} />
      <Badge tone={run.is_synthetic ? "caution" : "neutral"}>
        {run.is_synthetic
          ? "Fictional academic demonstration"
          : "Stored programme data"}
      </Badge>
      <Badge>
        {run.mode === "offline"
          ? "Offline deterministic analysis"
          : String(actual || run.model_name || "").includes("synthetic-mock")
            ? "Mocked model output"
            : actual && validated
              ? "Recorded model response"
              : "No successful model response recorded"}
      </Badge>
      <span>Created {dateLabel(run.created_at)}</span>
      <details>
        <summary>Execution metadata</summary>
        <p>
          Returned model: {actual || "Not recorded"}. Requests:{" "}
          {text(usage.request_count)}. Input tokens: {text(tokens.input_tokens)}
          . Output tokens: {text(tokens.output_tokens)}. Client duration:{" "}
          {typeof usage.duration_ms === "number"
            ? `${usage.duration_ms} ms`
            : "Not recorded"}
          .
        </p>
        <p>
          Observed cost is unavailable unless separately established by billing
          records. Token metadata does not establish a charge.
        </p>
      </details>
    </div>
  );
}

function RunSelection({ state }: { state: Results }) {
  return (
    <details>
      <summary>Assessment history and versions</summary>
      <Card className="analysis-toolbar">
        <div className="filter-row">
          <label>
            Career assessment
            <select
              value={state.careerId || ""}
              onChange={(event) => state.select("career", event.target.value)}
            >
              <option value="">Latest on this history page</option>
              {state.careerChoices.map((row) => (
                <option key={row.id} value={row.id}>
                  {dateLabel(row.created_at)} · {humanise(row.status)} ·{" "}
                  {row.id.slice(0, 8)}
                </option>
              ))}
              {state.careerId &&
                !state.careerChoices.some(
                  (row) => row.id === state.careerId,
                ) && (
                  <option value={state.careerId}>
                    Selected historical assessment
                  </option>
                )}
            </select>
          </label>
          <label>
            Action plan
            <select
              value={state.planId || ""}
              onChange={(event) => state.select("plan", event.target.value)}
              disabled={!state.careerRun}
            >
              <option value="">Latest for selected assessment</option>
              {state.planChoices.map((row) => (
                <option key={row.id} value={row.id}>
                  {dateLabel(row.created_at)} · {humanise(row.status)} ·{" "}
                  {row.id.slice(0, 8)}
                </option>
              ))}
              {state.planId &&
                !state.planChoices.some((row) => row.id === state.planId) && (
                  <option value={state.planId}>Selected historical plan</option>
                )}
            </select>
          </label>
          <button className="button secondary" onClick={state.reload}>
            <RefreshCw size={15} aria-hidden="true" />
            Refresh records
          </button>
        </div>
        <div className="history-pagination">
          <span>
            Career history: {state.careerPage?.total ?? 0} stored runs across
            revisions. Only the selected revision is shown.
          </span>
          <button
            className="button quiet"
            disabled={!state.careerOffset}
            onClick={() => state.page("career", state.careerOffset - 10)}
          >
            Previous assessments
          </button>
          <button
            className="button quiet"
            disabled={
              !state.careerPage ||
              state.careerOffset + 10 >= state.careerPage.total
            }
            onClick={() => state.page("career", state.careerOffset + 10)}
          >
            Older assessments
          </button>
          {state.planPage && (
            <>
              <button
                className="button quiet"
                disabled={!state.planOffset}
                onClick={() => state.page("plan", state.planOffset - 10)}
              >
                Previous plans
              </button>
              <button
                className="button quiet"
                disabled={state.planOffset + 10 >= state.planPage.total}
                onClick={() => state.page("plan", state.planOffset + 10)}
              >
                Older plans
              </button>
            </>
          )}
        </div>
      </Card>
    </details>
  );
}

function OfflineGeneration({ state }: { state: Results }) {
  const { api, access, programme, revisionId } = useWorkspace();
  const [advanced, setAdvanced] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  if (!access.permissions.includes("write"))
    return (
      <Notice>
        Your grant is read-only. An authorised operator can submit an offline
        assessment.
      </Notice>
    );
  async function generate(kind: "career" | "plan") {
    if (!revisionId || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (kind === "career") {
        let extra: Record<string, unknown> = {};
        if (advanced.trim()) {
          const parsed: unknown = JSON.parse(advanced);
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
            throw new ApiError("VALIDATION_ERROR");
          extra = parsed as Record<string, unknown>;
          if (extra.mode && extra.mode !== "offline")
            throw new ApiError("VALIDATION_ERROR");
          if (extra.revision_id && extra.revision_id !== revisionId)
            throw new ApiError("CONFLICT");
        }
        const body = validateResponse(
          {
            ...extra,
            revision_id: revisionId,
            mode: "offline",
            idempotency_key: `ui-career-${crypto.randomUUID()}`,
          },
          "CareerRequest",
        );
        const queued = await api.post<CareerRun>(
          `/api/v1/programmes/${programme.id}/career-analyses`,
          "CareerRead",
          body,
        );
        state.select("career", queued.id);
      } else if (state.careerRun && state.careerResult) {
        const fresh = await api.get<CareerRun>(
          `/api/v1/career-analyses/${state.careerRun.id}`,
          "CareerRead",
        );
        if (
          !safeCareerResult(fresh, programme.id, revisionId) ||
          fresh.fingerprint !== state.careerRun.fingerprint
        )
          throw new ApiError("CONFLICT");
        const queued = await api.post<PlanRun>(
          `/api/v1/career-analyses/${fresh.id}/action-plans`,
          "PlanRead",
          {
            mode: "offline",
            idempotency_key: `ui-plan-${crypto.randomUUID()}`,
          },
        );
        state.select("plan", queued.id);
      }
      state.reload();
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? failure
          : new ApiError("VALIDATION_ERROR"),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="generation-panel">
      <summary>Prepare an offline assessment or action plan</summary>
      <Notice>
        No paid AI or research request is made by these controls. A background
        worker must process the job. An empty mapping request produces explicit
        evidence limitations, not invented occupation or course content.
      </Notice>
      <label>
        Optional reviewed mapping request (JSON)
        <textarea
          rows={5}
          value={advanced}
          onChange={(event) => setAdvanced(event.target.value)}
          placeholder="Leave empty for an evidence-limited assessment"
          maxLength={250_000}
        />
      </label>
      <p className="muted">
        Only use exact registered occupation, skill and document-anchor IDs with
        reviewed passages. Do not enter private text or credentials here.
      </p>
      <div className="button-row">
        <button
          className="button secondary"
          disabled={busy || !revisionId}
          onClick={() => generate("career")}
        >
          {busy ? "Submitting…" : "Queue offline career assessment"}
        </button>
        <button
          className="button secondary"
          disabled={
            busy ||
            !state.careerResult ||
            !state.careerResult.recommendations?.length ||
            Boolean(state.careerRun?.needs_evidence_revalidation)
          }
          onClick={() => generate("plan")}
        >
          Queue offline action plan
        </button>
      </div>
      {error && <ErrorState error={error} retry={state.reload} />}
    </details>
  );
}

function Occupations({ result, path }: { result: CareerResult; path: string }) {
  if (!result.occupations?.length)
    return (
      <Empty title="No reviewed occupation mappings">
        A programme title cannot establish occupational fit. Supply reviewed
        taxonomy identities and admitted requirements before drawing alignment
        conclusions.
      </Empty>
    );
  return (
    <div className="card-grid">
      {result.occupations.map((role) => (
        <Card
          key={role.occupation_id}
          title={role.occupation_name}
          eyebrow={role.taxonomy}
        >
          <Status value={role.status} />
          {role.measure?.value != null ? (
            <div className="measure">
              <strong>{role.measure.value}%</strong>
              <span>
                {role.measure.numerator}/{role.measure.denominator} essential
                requirements under {role.measure.method_version}.{" "}
                {role.measure.basis}
              </span>
            </div>
          ) : (
            <Notice>
              {role.measure?.abstention_reason ||
                "No comparable alignment percentage is supported."}
            </Notice>
          )}
          <p>
            {role.rank == null
              ? "Unranked: no comparable ranking asserted."
              : `Recorded rank ${role.rank}`}
          </p>
          <p>
            {role.requirements?.filter(
              (row) => row.requirement_type === "essential",
            ).length || 0}{" "}
            essential ·{" "}
            {role.requirements?.filter(
              (row) => row.requirement_type === "optional",
            ).length || 0}{" "}
            optional requirements
          </p>
          <Citations citations={role.citations} evidencePath={path} />
          <details>
            <summary>Requirement details and limits</summary>
            <p>
              {role.description || "No occupation description was admitted."}
            </p>
            <p>{role.mapping_basis}</p>
            <p className="muted">{role.malaysia_applicability}</p>
            {role.requirements?.map((row) => (
              <div key={row.relationship_id} className="detail-row">
                <strong>{row.skill_name}</strong>
                <Status value={row.state} />
                <p>{row.explanation}</p>
              </div>
            ))}
            <TextList items={role.limitations} />
          </details>
        </Card>
      ))}
    </div>
  );
}

function Competencies({
  result,
  path,
}: {
  result: CareerResult;
  path: string;
}) {
  const [filter, setFilter] = useState("all");
  const rows = result.competencies || [];
  const visible = rows.filter(
    (row) =>
      filter === "all" ||
      (["supported", "partial", "documented_gap", "unknown"].includes(filter)
        ? row.state === filter
        : row.support_type === filter),
  );
  return (
    <>
      <label className="filter-field">
        Competency evidence
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        >
          <option value="all">All evidence states</option>
          {[
            "supported",
            "partial",
            "documented_gap",
            "unknown",
            "demonstrated",
            "documented_intent",
            "possible_association",
          ].map((value) => (
            <option key={value} value={value}>
              {humanise(value)}
            </option>
          ))}
        </select>
      </label>
      {visible.length ? (
        <div className="table-scroll">
          <table className="data-table">
            <caption>
              Occupational requirements compared with documented curriculum
              evidence
            </caption>
            <thead>
              <tr>
                <th>Competency / occupation</th>
                <th>Requirement</th>
                <th>Curriculum support</th>
                <th>Finding / evidence</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={`${row.occupation_id}:${row.relationship_id}`}>
                  <td>
                    <strong>{row.skill_name}</strong>
                    <br />
                    <small>
                      {result.occupations?.find(
                        (role) => role.occupation_id === row.occupation_id,
                      )?.occupation_name || "Occupation identity unavailable"}
                    </small>
                  </td>
                  <td>{humanise(row.requirement_type)}</td>
                  <td>
                    <Status value={row.state} />
                    <p>{humanise(row.support_type || "unknown")}</p>
                    {row.courses?.map((course) => (
                      <p key={course.course_id}>
                        Course {course.course_id.slice(0, 8)} ·{" "}
                        {humanise(course.support)} · {course.extent} documented
                        scope
                      </p>
                    ))}
                  </td>
                  <td>
                    <p>{row.explanation}</p>
                    <Citations citations={row.citations} evidencePath={path} />
                    <details>
                      <summary>Missing evidence and limits</summary>
                      <TextList items={row.evidence_needed} />
                      <TextList items={row.limitations} />
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty title="No matching competency findings">
          Unknown coverage is not a confirmed gap. Review the occupation mapping
          and available curriculum evidence.
        </Empty>
      )}
      <Notice>
        Demonstrated source evidence describes a bounded assessed observation;
        it does not certify every graduate. Intent, partial support, possible
        association and unknown remain distinct.
      </Notice>
    </>
  );
}

function RecommendationDetail({
  row,
  path,
  career,
  children,
}: {
  row: Recommendation;
  path: string;
  career?: CareerResult | null;
  children?: ReactNode;
}) {
  return (
    <Card title={row.action} eyebrow={humanise(row.category)}>
      <div className="inline-meta">
        <Status value={row.evidence_sufficiency} />
        <Status value={row.review_status || "proposed"} />
      </div>
      <h3>Suggested next step</h3>
      <p>{row.minimum_sufficient_intervention}</p>
      <Citations citations={row.citations} evidencePath={path} />
      <details>
        <summary>Why this action and which courses it concerns</summary>
        <p>{row.rationale}</p>
        {career && (
          <p>
            Occupation contexts:{" "}
            {career.occupations
              ?.filter((role) =>
                row.occupation_ids?.includes(role.occupation_id),
              )
              .map((role) => role.occupation_name)
              .join(" · ") || "No reviewed occupation binding"}
            . Target competency:{" "}
            {career.competencies?.find(
              (finding) => finding.skill_id === row.skill_id,
            )?.skill_name || "Requires evidence review"}
            .
          </p>
        )}
        <p>
          {row.course_ids?.length
            ? `${row.course_ids.length} documented course reference(s): ${row.course_ids.map((value) => value.slice(0, 8)).join(", ")}. Inspect the linked curriculum evidence.`
            : "A specific course binding is not documented; review the programme-level evidence."}
        </p>
        <h3>Competency objective</h3>
        <p>{row.competency_objective}</p>
        <p>
          <strong>Priority basis:</strong> {row.priority_basis}
        </p>
      </details>
      <details>
        <summary>Alternatives, no change and feasibility</summary>
        {row.alternatives.map((option, index) => (
          <div className="detail-row" key={index}>
            <strong>{option.action}</strong>
            <p>{option.rationale}</p>
            <TextList items={option.conditions} />
          </div>
        ))}
        <div className="detail-row">
          <strong>No change: {row.no_change_option.action}</strong>
          <p>{row.no_change_option.rationale}</p>
          <TextList items={row.no_change_option.conditions} />
        </div>
        <TextList items={row.implementation_considerations} />
        <TextList items={row.limitations} />
      </details>
      {children}
    </Card>
  );
}

function RecommendationReview({
  row,
  state,
}: {
  row: RecommendationRow;
  state: Results;
}) {
  const { api, access, programme, revisionId } = useWorkspace();
  const [expanded, setExpanded] = useState(false);
  const [offset, setOffset] = useState(0);
  const key =
    expanded && !row.needs_evidence_revalidation
      ? `${row.id}:${row.version_sha256}:reviews:${offset}`
      : null;
  const history = useResource(key, async (signal) => ({
    key,
    page: await api.get<Page<Model<"ReviewRead">>>(
      `/api/v1/career-recommendations/${row.id}/reviews?limit=10&offset=${offset}`,
      "Page_ReviewRead_",
      signal,
    ),
  }));
  const page = history.data?.key === key ? history.data.page : undefined;
  return (
    <details onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary>Review decisions and authorised consideration</summary>
      {expanded && (
        <>
          <h3>Recorded review history</h3>
          {history.loading ? (
            <Loading label="Loading recommendation reviews" />
          ) : history.error ? (
            <ErrorState error={history.error} retry={history.reload} />
          ) : page?.items.length ? (
            page.items.map((review) => (
              <div key={review.id} className="detail-row">
                <Status value={review.decision} />
                <p>
                  {review.needs_evidence_revalidation
                    ? "Reason withheld pending source revalidation."
                    : review.reason}
                </p>
                <small>
                  {dateLabel(review.reviewed_at)} · operator alias, not
                  independently verified academic identity
                </small>
              </div>
            ))
          ) : (
            <p>No recorded decisions for this recommendation.</p>
          )}
          <div className="button-row">
            <button
              className="button quiet"
              disabled={!offset}
              onClick={() => setOffset((value) => value - 10)}
            >
              Previous decisions
            </button>
            <button
              className="button quiet"
              disabled={!page || offset + 10 >= page.total}
              onClick={() => setOffset((value) => value + 10)}
            >
              Older decisions
            </button>
          </div>
          <ReviewForm
            permitted={access.permissions.includes("review")}
            disabled={row.needs_evidence_revalidation || !state.careerResult}
            submit={async (decision, reason) => {
              const current = await api.get<CareerRun>(
                `/api/v1/career-analyses/${row.run_id}`,
                "CareerRead",
              );
              if (
                !safeCareerResult(current, programme.id, revisionId) ||
                current.id !== state.careerRun?.id ||
                current.fingerprint !== state.careerRun.fingerprint
              ) {
                state.reload();
                throw new ApiError("CONFLICT");
              }
              const rows = await api.get<Model<"RecommendationPage">>(
                `/api/v1/career-analyses/${row.run_id}/recommendations?limit=100&offset=0`,
                "RecommendationPage",
              );
              const fresh = rows.items.find((item) => item.id === row.id);
              if (
                !fresh ||
                fresh.needs_evidence_revalidation ||
                fresh.version_sha256 !== row.version_sha256
              ) {
                state.reload();
                throw new ApiError("CONFLICT");
              }
              await api.post(
                `/api/v1/career-recommendations/${row.id}/reviews`,
                "ReviewRead",
                {
                  decision,
                  reason,
                  expected_recommendation_version: row.version_sha256,
                },
              );
              state.reload();
              history.reload();
            }}
          />
        </>
      )}
    </details>
  );
}

function Recommendations({ state, path }: { state: Results; path: string }) {
  const { api } = useWorkspace();
  const key =
    state.careerResult && state.careerRun
      ? `${state.careerRun.id}:${state.careerRun.fingerprint}:recommendations`
      : null;
  const records = useResource(key, async (signal) => ({
    key,
    page: await api.get<Model<"RecommendationPage">>(
      `/api/v1/career-analyses/${state.careerRun!.id}/recommendations?limit=100&offset=0`,
      "RecommendationPage",
      signal,
    ),
  }));
  if (records.loading)
    return <Loading label="Loading exact recommendation versions" />;
  if (records.error)
    return <ErrorState error={records.error} retry={records.reload} />;
  if (
    records.data?.key !== key ||
    records.data.page.needs_evidence_revalidation
  )
    return (
      <Notice tone="caution">
        Recommendation sources require revalidation. Source-derived proposals
        are withheld.
      </Notice>
    );
  const rows = records.data.page.items.filter(
    (row) =>
      row.run_id === state.careerRun?.id &&
      row.programme_revision_id === state.careerResult?.programme_revision_id &&
      !row.needs_evidence_revalidation,
  );
  return (
    <div className="detail-list">
      {state.careerResult?.recommendations?.length ? (
        state.careerResult.recommendations.map((item) => {
          const persisted = rows.find(
            (row) => row.recommendation_key === item.key,
          );
          return (
            <RecommendationDetail
              key={item.key}
              row={item}
              path={path}
              career={state.careerResult}
            >
              {persisted ? (
                <RecommendationReview row={persisted} state={state} />
              ) : (
                <Notice>
                  The exact persisted review version is unavailable. No review
                  action is offered.
                </Notice>
              )}
            </RecommendationDetail>
          );
        })
      ) : (
        <Empty title="No supported recommendation inventory">
          Supply reviewed occupational requirements and curriculum passages.
          Weak evidence supports investigation rather than invented course
          changes.
        </Empty>
      )}
    </div>
  );
}

function Pathways({ plan, path }: { plan: PlanResult; path: string }) {
  return (
    <div className="detail-list">
      {plan.pathways?.length ? (
        plan.pathways.map((route) => (
          <Card
            key={route.key}
            title={route.objective}
            eyebrow={humanise(route.pathway_type)}
          >
            <Status value={route.evidence_sufficiency} />
            <p>
              {route.total_hours == null
                ? "Total duration unknown"
                : `${route.total_hours} estimated effort hours`}{" "}
              · {route.known_hours} known hours · {route.unknown_duration_steps}{" "}
              steps without an estimate.
            </p>
            <details>
              <summary>Effort estimate and limitations</summary>
              <p className="muted">{route.duration_basis}</p>
              <TextList items={route.limitations} />
            </details>
            <ol className="pathway-timeline">
              {[...route.steps]
                .sort((a, b) => a.position - b.position)
                .map((step) => (
                  <li key={step.key}>
                    <span className="step-number" aria-hidden="true">
                      {step.position}
                    </span>
                    <div>
                      <p className="eyebrow">
                        {humanise(step.step_type)} · proposal
                      </p>
                      <h3>{step.purpose}</h3>
                      <details>
                        <summary>Activity, dependencies and assessment</summary>
                        <p>{step.activity}</p>
                        <p>{step.objective}</p>
                        <p>
                          <strong>Proposed assessment:</strong>{" "}
                          {step.proposed_assessment}
                        </p>
                        <p>
                          Dependencies:{" "}
                          {step.depends_on?.length
                            ? step.depends_on.join(", ")
                            : "No preceding activity specified"}{" "}
                          ·{" "}
                          {humanise(step.ordering_basis || "procedural_review")}
                        </p>
                        <p>
                          {step.duration?.hours == null
                            ? "Effort unknown; verification required."
                            : `${step.duration.hours} ${step.duration.component} hours (${humanise(step.duration.basis_type || "unknown")}).`}{" "}
                          {step.duration?.basis}
                        </p>
                        <TextList items={step.conditions} />
                        <Citations
                          citations={step.citations}
                          evidencePath={path}
                        />
                        <Citations
                          citations={step.duration?.citations}
                          evidencePath={path}
                        />
                        {step.resource_keys?.map((key) => {
                          const resource = plan.resources?.find(
                            (row) => row.key === key,
                          );
                          return resource ? (
                            <div className="detail-row" key={key}>
                              <strong>{resource.name}</strong>
                              <p>
                                {resource.publisher} ·{" "}
                                {humanise(resource.access_status)} access ·{" "}
                                {resource.cost_status === "unknown"
                                  ? "Cost unknown"
                                  : resource.cost_status === "free"
                                    ? "Reported free at verification"
                                    : `${resource.cost_amount ?? "Amount unknown"} ${resource.cost_currency || ""}`}
                              </p>
                              <p>
                                Verified {dateLabel(resource.verified_at)}.{" "}
                                {resource.licence_limitations}
                              </p>
                              <Citations
                                citations={resource.citations}
                                evidencePath={path}
                              />
                            </div>
                          ) : null;
                        })}
                      </details>
                    </div>
                  </li>
                ))}
            </ol>
            <details>
              <summary>Prerequisites and supporting evidence</summary>
              {route.prerequisites?.length ? (
                route.prerequisites.map((item) => (
                  <div key={item.skill_id}>
                    <Status value={item.status || "source_supported"} />
                    <p>{item.basis}</p>
                    <Citations citations={item.citations} evidencePath={path} />
                  </div>
                ))
              ) : (
                <p>
                  No technical prerequisite is documented; timeline order is
                  procedural review, not inferred skill mastery.
                </p>
              )}
              <Citations citations={route.citations} evidencePath={path} />
            </details>
          </Card>
        ))
      ) : (
        <Empty title="No eligible pathway">
          Consideration approval and sufficient source evidence are required for
          substantive proposals. No-change decisions and unknown competencies do
          not become automatic training.
        </Empty>
      )}
      <Notice>
        These are proposed academic activities, not completed student learning.
        No competence, attendance or implementation progress is asserted.
      </Notice>
    </div>
  );
}

function Scenarios({ plan, path }: { plan: PlanResult; path: string }) {
  return (
    <>
      <Notice>
        Hypothetical comparison over the same admitted evidence. These panels
        are not forecasts or replacement probabilities.
      </Notice>
      <div className="card-grid scenario-grid">
        {plan.scenarios.map((scenario) => (
          <Card
            key={scenario.key}
            title={scenario.name}
            eyebrow="Planning assumption"
          >
            <p>{scenario.description}</p>
            <p className="muted">
              {scenario.planning_horizon || "No planning horizon supplied."}
            </p>
            <details>
              <summary>Priority choices and supporting context</summary>
              <p>{scenario.assumption.rationale}</p>
              {scenario.priorities.map((item) => (
                <div key={item.recommendation_id} className="detail-row">
                  <Status value={item.priority} />
                  <p>{item.rationale}</p>
                  <TextList items={item.conditions} />
                </div>
              ))}
              <h3>Supporting context</h3>
              <Citations
                citations={scenario.supporting_citations}
                evidencePath={path}
              />
              <h3>Contradictory context</h3>
              <Citations
                citations={scenario.contradicting_citations}
                evidencePath={path}
              />
            </details>
            <details>
              <summary>Comparison dimensions and uncertainty</summary>
              <TextList items={scenario.comparison_dimensions} />
              <TextList items={scenario.uncertainties} />
            </details>
          </Card>
        ))}
      </div>
      <Card title="What changes between assumptions">
        <p>{plan.comparison.explanation}</p>
        <p>
          {plan.comparison.changed_recommendation_ids.length} changed priorities
          · {plan.comparison.unchanged_recommendation_ids.length} unchanged ·{" "}
          {plan.comparison.no_regret_recommendation_ids.length} shared review
          options. These counts do not measure efficacy.
        </p>
        <details>
          <summary>Comparison details and limitations</summary>
          <TextList items={plan.comparison.dimensions} />
          <TextList items={plan.comparison.limitations} />
        </details>
      </Card>
    </>
  );
}

function SDGs({ plan, path }: { plan: PlanResult; path: string }) {
  return (
    <>
      <Notice>
        Proposed contributions require a defensible educational mechanism. No
        measured or achieved SDG impact is asserted.
      </Notice>
      <div className="card-grid">
        {plan.sdg_alignments?.length ? (
          plan.sdg_alignments.map((item, index) => (
            <Card
              key={`${item.recommendation_id}:${index}`}
              title={
                item.target_code
                  ? `Target ${item.target_code}: ${item.target_title}`
                  : "No justified target mapping"
              }
              eyebrow={
                item.goal_code
                  ? `Goal ${item.goal_code} · ${item.goal_title}`
                  : "Source-limited contribution"
              }
            >
              <Status value={item.status} />
              <p>{item.rationale}</p>
              {item.mechanism && (
                <p>
                  <strong>Mechanism:</strong> {humanise(item.mechanism)}
                </p>
              )}
              <Citations citations={item.citations} evidencePath={path} />
              <details>
                <summary>Evidence limitations</summary>
                <TextList items={item.limitations} />
              </details>
            </Card>
          ))
        ) : (
          <Empty title="No source-supported SDG mapping">
            Official targets and a reviewed mechanism must be supplied before a
            contribution can be proposed.
          </Empty>
        )}
      </div>
    </>
  );
}

function Industry({ result, path }: { result: CareerResult; path: string }) {
  return (
    <>
      <div className="industry-hero">
        <p className="eyebrow">Evidence before predictions</p>
        <h2>
          Understand the context.
          <br />
          Keep the academic judgement.
        </h2>
        <p>
          Published role requirements, dated workforce observations and scoped
          AI evidence support review. They do not declare a course obsolete.
        </p>
      </div>
      {result.occupations?.length ? (
        result.occupations.map((role) => (
          <Card
            key={role.occupation_id}
            title={role.occupation_name}
            eyebrow="Admitted occupational context"
          >
            <p>{role.malaysia_applicability}</p>
            {role.workforce?.length ? (
              <div className="table-scroll">
                <table className="data-table">
                  <caption>
                    Dated occupation-level comparisons; not skill demand
                  </caption>
                  <thead>
                    <tr>
                      <th>Period / geography</th>
                      <th>Recorded comparison</th>
                      <th>Scope</th>
                    </tr>
                  </thead>
                  <tbody>
                    {role.workforce.map((signal, index) => (
                      <tr key={index}>
                        <td>
                          {text(signal.period_end)} · {text(signal.geography)}
                        </td>
                        <td>
                          {text(signal.classification)}
                          <br />
                          Absolute change: {text(signal.absolute_change)}
                          <br />
                          Percentage change:{" "}
                          {signal.percentage_change == null
                            ? "Not calculable"
                            : `${text(signal.percentage_change)}%`}
                        </td>
                        <td>
                          {signal.historical_context_only
                            ? "Historical context only"
                            : "Refer to publication and comparison method"}
                          <p>
                            Deterministic methodology retained; no skill-level
                            demand inference.
                          </p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Notice>
                No suitable occupation-linked workforce observations are
                admitted.
              </Notice>
            )}
            <h3>AI transformation context</h3>
            <p>
              {typeof role.ai_transformation?.status === "string"
                ? humanise(role.ai_transformation.status)
                : "Insufficient admitted task-level evidence."}
            </p>
            <p className="muted">
              Occupational exposure is not replacement probability. Capabilities
              retain their original model, study and task scope.
            </p>
            <Citations citations={role.citations} evidencePath={path} />
            <Citations
              citations={(role.workforce || [])
                .flatMap((signal) => [
                  signal.before_reference_id,
                  signal.after_reference_id,
                ])
                .filter((value): value is string => typeof value === "string")
                .map((reference_id) => ({ reference_id }))}
              evidencePath={path}
            />
            <Citations
              citations={(Array.isArray(role.ai_transformation?.reference_ids)
                ? role.ai_transformation.reference_ids
                : []
              )
                .filter((value): value is string => typeof value === "string")
                .map((reference_id) => ({ reference_id }))}
              evidencePath={path}
            />
            <details>
              <summary>Evidence limits and study scope</summary>
              <TextList
                items={
                  Array.isArray(role.ai_transformation?.limitations)
                    ? role.ai_transformation.limitations.filter(
                        (value): value is string => typeof value === "string",
                      )
                    : []
                }
              />
              <TextList items={role.limitations} />
            </details>
          </Card>
        ))
      ) : (
        <Empty title="No reviewed occupational evidence">
          Review programme-to-occupation mappings and source permissions.
          Currentness and Malaysian applicability must be established; no
          screenshot statistics are substituted.
        </Empty>
      )}
    </>
  );
}

function EvidenceList({ items, path }: { items: Evidence[]; path: string }) {
  const eligible = items.filter(
    (row) =>
      row.internal_eligible &&
      row.rights.internal_analysis_allowed &&
      row.rights.excerpt_output_allowed &&
      row.review_status !== "rejected",
  );
  return (
    <div className="detail-list">
      {eligible.length ? (
        eligible.map((item) => (
          <Card
            key={item.id}
            title={item.title}
            eyebrow={`${item.publisher} · ${humanise(item.evidence_class)}`}
          >
            <div className="inline-meta">
              <Status value={item.review_status} />
              <Badge>
                {item.is_synthetic
                  ? "Synthetic source"
                  : "Attributed reference source"}
              </Badge>
              {item.historical_context_only && (
                <Badge tone="caution">Historical context only</Badge>
              )}
            </div>
            <p>
              Publication: {item.publication_date || "Unknown"} · Observation:{" "}
              {item.observation_start || "Unknown"}
              {item.observation_end ? ` to ${item.observation_end}` : ""}
            </p>
            <Citations
              citations={[{ reference_id: item.id }]}
              evidencePath={path}
            />
            <details>
              <summary>Source details and limitations</summary>
              <p>
                Version {item.version_id.slice(0, 8)} · Locator {item.locator} ·{" "}
                {humanise(item.scope)}
              </p>
              <TextList items={item.limitations} />
            </details>
          </Card>
        ))
      ) : (
        <Empty title="No admissible source records">
          Source evidence is missing or withheld. Search snippets are not
          admitted evidence.
        </Empty>
      )}
    </div>
  );
}

function PlanReview({ state }: { state: Results }) {
  const { api, access, programme, revisionId } = useWorkspace();
  const original = state.planRun;
  return (
    original && (
      <ReviewForm
        permitted={access.permissions.includes("review")}
        disabled={!state.planResult || original.needs_evidence_revalidation}
        submit={async (decision, reason) => {
          const expected = original.fingerprint;
          const career = await api.get<CareerRun>(
            `/api/v1/career-analyses/${original.career_run_id}`,
            "CareerRead",
          );
          const current = await api.get<PlanRun>(
            `/api/v1/action-plans/${original.id}`,
            "PlanRead",
          );
          if (
            !expected ||
            current.fingerprint !== expected ||
            !safePlanResult(current, career, programme.id, revisionId)
          ) {
            state.reload();
            throw new ApiError("CONFLICT");
          }
          await api.post(
            `/api/v1/action-plans/${original.id}/reviews`,
            "PlanReviewRead",
            { decision, reason, expected_plan_fingerprint: expected },
          );
          state.reload();
        }}
      />
    )
  );
}

function Reviews({ state }: { state: Results }) {
  const { api } = useWorkspace();
  const [offset, setOffset] = useState(0);
  const [recommendationId, setRecommendationId] = useState("");
  const snapshots = state.planResult?.recommendations || [];
  const selected = snapshots.some((row) => row.id === recommendationId)
    ? recommendationId
    : "";
  const path = selected
    ? `/api/v1/career-recommendations/${selected}/reviews`
    : state.planRun
      ? `/api/v1/action-plans/${state.planRun.id}/reviews`
      : null;
  const key =
    state.planResult && path
      ? `${path}:${offset}:${state.planRun?.fingerprint}`
      : null;
  const history = useResource(key, async (signal) => ({
    key,
    page: await api.get<Page<Model<"ReviewRead"> | Model<"PlanReviewRead">>>(
      `${path}?limit=10&offset=${offset}`,
      selected ? "Page_ReviewRead_" : "Page_PlanReviewRead_",
      signal,
    ),
  }));
  const page = history.data?.key === key ? history.data.page : undefined;
  return (
    <>
      <label className="filter-field">
        Review history
        <select
          value={selected}
          onChange={(event) => {
            setRecommendationId(event.target.value);
            setOffset(0);
          }}
        >
          <option value="">Selected action plan</option>
          {snapshots.map((row) => (
            <option key={row.id} value={row.id}>
              {row.recommendation.action}
            </option>
          ))}
        </select>
      </label>
      {history.loading ? (
        <Loading label="Loading version-bound review history" />
      ) : history.error ? (
        <ErrorState error={history.error} retry={history.reload} />
      ) : page?.items.length ? (
        <div className="detail-list">
          {page.items.map((row) => (
            <Card
              key={row.id}
              eyebrow={dateLabel(row.reviewed_at)}
              title={humanise(row.decision)}
            >
              <p>
                {row.needs_evidence_revalidation
                  ? "Reason withheld pending source revalidation."
                  : row.reason}
              </p>
              <small>
                Recorded operator: {row.actor}. This alias is not independently
                verified academic identity.
              </small>
            </Card>
          ))}
        </div>
      ) : (
        <Empty title="No recorded review decisions">
          Generated recommendations are proposals. A human operator must
          explicitly record a decision against an exact current version.
        </Empty>
      )}
      <div className="button-row">
        <button
          className="button secondary"
          disabled={!offset}
          onClick={() => setOffset((value) => value - 10)}
        >
          Previous reviews
        </button>
        <button
          className="button secondary"
          disabled={!page || offset + 10 >= page.total}
          onClick={() => setOffset((value) => value + 10)}
        >
          Older reviews
        </button>
      </div>
      <Card title="Record an action-plan review">
        <PlanReview state={state} />
      </Card>
    </>
  );
}

function ActionPlan({ state, path }: { state: Results; path: string }) {
  const plan = state.planResult!;
  return (
    <article className="action-plan">
      <div className="button-row no-print">
        <button className="button secondary" onClick={() => window.print()}>
          <Printer size={16} aria-hidden="true" />
          Print proposal
        </button>
      </div>
      <section className="report-section">
        <p className="eyebrow">01 · Programme overview</p>
        <Card title={plan.overview.programme_name}>
          <p>
            {plan.overview.institution_name} · {plan.overview.revision_label}
          </p>
          <p>
            {plan.overview.course_ids.length} recorded courses. Evidence
            coverage describes records, not curriculum quality.
          </p>
          <p>
            {plan.career.occupations?.length || 0} reviewed occupational
            contexts · {plan.career.competencies?.length || 0} source-linked
            requirement findings · {plan.evidence?.length || 0} admitted source
            pointers.
          </p>
          <details>
            <summary>Programme evidence limitations</summary>
            <TextList items={plan.overview.limitations} />
          </details>
        </Card>
      </section>
      <section className="report-section">
        <h2>02 · Future career alignment</h2>
        <Occupations result={plan.career} path={path} />
      </section>
      <section className="report-section">
        <h2>03 · Competency coverage and gaps</h2>
        <Competencies result={plan.career} path={path} />
      </section>
      <section className="report-section">
        <h2>04 · Academic recommendations</h2>
        {plan.recommendations.map((item) => (
          <RecommendationDetail
            key={item.id}
            row={item.recommendation}
            path={path}
            career={plan.career}
          >
            <p>
              Consideration status: {humanise(item.consideration_status)}. Exact
              recommendation version retained.
            </p>
          </RecommendationDetail>
        ))}
      </section>
      <section className="report-section">
        <h2>05 · Academic pathways</h2>
        <Pathways plan={plan} path={path} />
      </section>
      <section className="report-section">
        <h2>06 · Future workforce scenarios</h2>
        <Scenarios plan={plan} path={path} />
      </section>
      <section className="report-section">
        <h2>07 · SDG contribution</h2>
        <SDGs plan={plan} path={path} />
      </section>
      <section className="report-section">
        <h2>08 · Academic review and implementation</h2>
        <Notice>
          Generated status: proposed. Academic implementation is not authorised
          by generation. Inspect separate human review history for decisions.
        </Notice>
        <details>
          <summary>Plan limitations</summary>
          <TextList items={plan.limitations} />
        </details>
        <PlanReview state={state} />
      </section>
    </article>
  );
}

export default function IntelligencePage({ section }: { section: string }) {
  const { programme, revisionId } = useWorkspace();
  const state = useAnalysisResults();
  const title = titles[section] || "Academic intelligence";
  const needsPlan =
    ["pathways", "scenarios", "sdg", "plan", "reviews"].includes(section) ||
    (section === "evidence" && Boolean(state.planId));
  const careerPath = state.careerRun
    ? `/api/v1/career-analyses/${state.careerRun.id}/evidence`
    : "";
  const planPath = state.planRun
    ? `/api/v1/action-plans/${state.planRun.id}/evidence`
    : careerPath;
  let content: ReactNode;
  if (!revisionId)
    content = (
      <Empty title="Select a curriculum revision">
        A documented revision is needed before analysis can be shown.
      </Empty>
    );
  else if (state.loading) content = <Loading />;
  else if (state.error)
    content = <ErrorState error={state.error} retry={state.reload} />;
  else if (state.careerRun?.needs_evidence_revalidation)
    content = (
      <Notice tone="caution">
        This assessment is stale or its evidence is restricted. Source-derived
        findings, citations and proposals are withheld. Revalidate sources and
        deliberately submit a new assessment.
      </Notice>
    );
  else if (state.careerRun && isPending(state.careerRun.status))
    content = (
      <>
        <Loading
          label={`Career assessment ${humanise(state.careerRun.status)}`}
        />
        <Notice>
          The backend job is pending. This does not establish that a worker is
          online; a configured worker must process it.
        </Notice>
      </>
    );
  else if (state.careerRun?.status === "FAILED")
    content = (
      <Empty title="Career assessment failed">
        No successful academic result is displayed. Inspect the job with an
        authorised operator before deliberately resubmitting.
      </Empty>
    );
  else if (!state.careerResult)
    content = (
      <Empty title="No completed career assessment for this revision">
        Select an existing historical run, inspect older history pages, or ask
        an authorised operator to prepare an offline assessment. No example
        results are substituted.
      </Empty>
    );
  else if (needsPlan && state.planLoading)
    content = <Loading label="Loading the selected action plan" />;
  else if (needsPlan && state.planError)
    content = <ErrorState error={state.planError} retry={state.reload} />;
  else if (needsPlan && state.planRun?.needs_evidence_revalidation)
    content = (
      <Notice tone="caution">
        Action-plan evidence or parent review has changed. Derived proposals and
        source text are withheld pending revalidation.
      </Notice>
    );
  else if (needsPlan && state.planRun && isPending(state.planRun.status))
    content = (
      <>
        <Loading label={`Action plan ${humanise(state.planRun.status)}`} />
        <Notice>
          Awaiting actual worker completion; no completed pathway is being
          assumed.
        </Notice>
      </>
    );
  else if (needsPlan && state.planRun?.status === "FAILED")
    content = (
      <Empty title="Action-plan job failed">
        No successful plan is available. Review the actual job outcome before
        submitting another version.
      </Empty>
    );
  else if (needsPlan && !state.planResult)
    content = (
      <Empty title="No completed action plan for this assessment">
        Recommendations need explicit consideration review and eligible
        evidence. An authorised operator can submit an offline plan; generation
        never grants academic approval.
      </Empty>
    );
  else {
    const career = state.careerResult;
    const plan = state.planResult;
    const sections: Record<string, ReactNode> = {
      industry: <Industry result={career} path={careerPath} />,
      careers: <Occupations result={career} path={careerPath} />,
      competencies: <Competencies result={career} path={careerPath} />,
      recommendations: <Recommendations state={state} path={careerPath} />,
      evidence: (
        <EvidenceList
          items={plan?.evidence || career.evidence || []}
          path={plan ? planPath : careerPath}
        />
      ),
    };
    if (plan)
      Object.assign(sections, {
        pathways: <Pathways plan={plan} path={planPath} />,
        scenarios: <Scenarios plan={plan} path={planPath} />,
        sdg: <SDGs plan={plan} path={planPath} />,
        plan: <ActionPlan state={state} path={planPath} />,
        reviews: <Reviews state={state} />,
      });
    content = (
      <>
        <section className="notice" aria-label="At a glance">
          <div>
            <strong>At a glance</strong>
            <p>
              {career.course_ids.length} recorded courses ·{" "}
              {career.recommendations?.length || 0} proposed actions
              {plan ? ` · ${plan.pathways?.length || 0} proposed pathways` : ""}
              .
            </p>
            <p>
              These are review proposals, not academic approval. Open details
              and sources to see the reasoning and missing evidence.
            </p>
          </div>
        </section>
        {sections[section] || <Empty title="Section unavailable" />}
      </>
    );
  }
  return (
    <>
      <PageHeading eyebrow={programme.name} title={title}>
        <p>
          Traceable evidence, explicit uncertainty and human academic judgement.
        </p>
      </PageHeading>
      <RunSelection state={state} />
      {state.careerRun && (
        <ResultLabels
          run={needsPlan && state.planRun ? state.planRun : state.careerRun}
        />
      )}
      {content}
      <OfflineGeneration state={state} />
    </>
  );
}
