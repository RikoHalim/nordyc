import { useSearchParams } from "react-router-dom";
import { ApiError, validateResponse } from "../api/client";
import type {
  CareerResult,
  CareerRun,
  Page,
  PlanResult,
  PlanRun,
} from "../api/types";
import { useWorkspace } from "../app/workspace";
import { useResource } from "./resource";

const terminal = (status: string) =>
  status === "SUCCEEDED" || status === "PARTIAL";
export const byCreatedAt = <T extends { created_at: string }>(rows: T[]) =>
  [...rows].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));

export function safeCareerResult(
  run?: CareerRun,
  programmeId?: string,
  revisionId?: string | null,
): CareerResult | null {
  if (
    !run ||
    run.needs_evidence_revalidation ||
    !terminal(run.status) ||
    !run.fingerprint
  )
    return null;
  if (
    (programmeId && run.programme_id !== programmeId) ||
    (revisionId && run.programme_revision_id !== revisionId)
  )
    throw new ApiError("INVALID_RESPONSE");
  const result = validateResponse<CareerResult>(
    run.result_json,
    "CareerResult",
  );
  if (
    result.programme_id !== run.programme_id ||
    result.programme_revision_id !== run.programme_revision_id ||
    result.is_synthetic !== run.is_synthetic
  )
    throw new ApiError("INVALID_RESPONSE");
  return result;
}

export function safePlanResult(
  run?: PlanRun,
  career?: CareerRun,
  programmeId?: string,
  revisionId?: string | null,
): PlanResult | null {
  if (
    !run ||
    run.needs_evidence_revalidation ||
    !terminal(run.status) ||
    !run.fingerprint
  )
    return null;
  if (
    !career ||
    !safeCareerResult(career, programmeId, revisionId) ||
    run.career_run_id !== career.id ||
    run.career_fingerprint !== career.fingerprint ||
    run.programme_id !== career.programme_id ||
    run.programme_revision_id !== career.programme_revision_id
  )
    throw new ApiError("INVALID_RESPONSE");
  const result = validateResponse<PlanResult>(run.result_json, "PlanResult");
  if (
    result.programme_id !== run.programme_id ||
    result.programme_revision_id !== run.programme_revision_id ||
    result.career_run_id !== run.career_run_id ||
    result.career_fingerprint !== run.career_fingerprint ||
    result.is_synthetic !== run.is_synthetic ||
    result.career.programme_id !== career.programme_id ||
    result.career.programme_revision_id !== career.programme_revision_id ||
    result.career.is_synthetic !== career.is_synthetic
  )
    throw new ApiError("INVALID_RESPONSE");
  return result;
}

function offset(value: string | null) {
  const parsed = Number(value || 0);
  return Number.isInteger(parsed) && parsed >= 0 && parsed <= 100_000
    ? parsed
    : 0;
}

/** Fresh source gates precede parsing; old-context resources never reach a view. */
export function useAnalysisResults() {
  const { api, programme, revisionId } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const careerOffset = offset(params.get("careerOffset"));
  const planOffset = offset(params.get("planOffset"));
  const requestedCareer = params.get("career");
  const requestedPlan = params.get("plan");
  const scope = `${programme.id}:${revisionId}`;
  const historyKey = revisionId
    ? `${scope}:career-history:${careerOffset}`
    : null;
  const history = useResource(historyKey, async (signal) => ({
    key: historyKey,
    page: await api.get<Page<CareerRun>>(
      `/api/v1/programmes/${programme.id}/career-analyses?limit=10&offset=${careerOffset}`,
      "Page_CareerRead_",
      signal,
    ),
  }));
  const careerPage =
    history.data?.key === historyKey ? history.data.page : undefined;
  const careerChoices = byCreatedAt(
    (careerPage?.items || []).filter(
      (row) =>
        row.programme_id === programme.id &&
        row.programme_revision_id === revisionId,
    ),
  );
  const careerId = requestedCareer || careerChoices[0]?.id;
  const careerKey =
    revisionId && careerId ? `${scope}:career:${careerId}` : null;
  const career = useResource(careerKey, async (signal) => {
    const run = await api.get<CareerRun>(
      `/api/v1/career-analyses/${encodeURIComponent(careerId || "")}`,
      "CareerRead",
      signal,
    );
    if (
      run.programme_id !== programme.id ||
      run.programme_revision_id !== revisionId
    )
      throw new ApiError("NOT_FOUND");
    return {
      key: careerKey,
      run,
      result: safeCareerResult(run, programme.id, revisionId),
    };
  });
  const selectedCareer =
    career.data?.key === careerKey ? career.data : undefined;
  const planHistoryKey = selectedCareer
    ? `${scope}:plans:${selectedCareer.run.id}:${planOffset}`
    : null;
  const planHistory = useResource(planHistoryKey, async (signal) => ({
    key: planHistoryKey,
    page: await api.get<Page<PlanRun>>(
      `/api/v1/career-analyses/${selectedCareer!.run.id}/action-plans?limit=10&offset=${planOffset}`,
      "Page_PlanRead_",
      signal,
    ),
  }));
  const planPage =
    planHistory.data?.key === planHistoryKey
      ? planHistory.data.page
      : undefined;
  const planChoices = byCreatedAt(
    (planPage?.items || []).filter(
      (row) =>
        row.career_run_id === selectedCareer?.run.id &&
        row.programme_id === programme.id &&
        row.programme_revision_id === revisionId,
    ),
  );
  const planId = requestedPlan || planChoices[0]?.id;
  const planKey =
    selectedCareer && planId
      ? `${scope}:${selectedCareer.run.id}:plan:${planId}`
      : null;
  const plan = useResource(planKey, async (signal) => {
    const run = await api.get<PlanRun>(
      `/api/v1/action-plans/${encodeURIComponent(planId || "")}`,
      "PlanRead",
      signal,
    );
    if (
      run.career_run_id !== selectedCareer!.run.id ||
      run.programme_id !== programme.id ||
      run.programme_revision_id !== revisionId
    )
      throw new ApiError("NOT_FOUND");
    return {
      key: planKey,
      run,
      result: safePlanResult(
        run,
        selectedCareer!.run,
        programme.id,
        revisionId,
      ),
    };
  });
  const selectedPlan = plan.data?.key === planKey ? plan.data : undefined;
  function select(kind: "career" | "plan", id: string) {
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      if (id) next.set(kind, id);
      else next.delete(kind);
      if (kind === "career") {
        next.delete("plan");
        next.delete("planOffset");
      }
      return next;
    });
  }
  function page(kind: "career" | "plan", value: number) {
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set(`${kind}Offset`, String(Math.max(0, value)));
      next.delete(kind);
      if (kind === "career") {
        next.delete("plan");
        next.delete("planOffset");
      }
      return next;
    });
  }
  function reload() {
    history.reload();
    career.reload();
    planHistory.reload();
    plan.reload();
  }
  return {
    careerRun: selectedCareer?.run,
    careerResult: selectedCareer?.result,
    planRun: selectedPlan?.run,
    planResult: selectedPlan?.result,
    careerChoices,
    planChoices,
    careerPage,
    planPage,
    careerOffset,
    planOffset,
    careerId,
    planId,
    select,
    page,
    reload,
    loading: history.loading || career.loading,
    planLoading: planHistory.loading || plan.loading,
    error: history.error || career.error,
    planError: planHistory.error || plan.error,
  };
}
