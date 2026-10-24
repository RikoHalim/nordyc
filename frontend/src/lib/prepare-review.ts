import { ApiClient, ApiError, validateResponse } from "../api/client";
import type { CareerRun, Model, PlanRun } from "../api/types";
import { byCreatedAt, safeCareerResult, safePlanResult } from "./results";

type AnalysisRun = Model<"AnalysisRead">;
type ScopedRun = AnalysisRun | CareerRun | PlanRun;
type Options = {
  key: string;
  signal: AbortSignal;
  onProgress: (text: string) => void;
  careerId?: string;
};
const complete = (run: ScopedRun) =>
  run.status === "SUCCEEDED" || run.status === "PARTIAL";
const pending = (run: ScopedRun) =>
  run.status === "QUEUED" || run.status === "RUNNING";
const id = (value: string) =>
  /^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(value);

/** Explicit offline preparation over existing protected worker endpoints only. */
export async function prepareReview(
  api: ApiClient,
  programmeId: string,
  revisionId: string,
  options: Options,
): Promise<{
  analysisId: string;
  careerId: string;
  planId: string | null;
  recommendationCount: number;
}> {
  if (
    !id(programmeId) ||
    !id(revisionId) ||
    (options.careerId && !id(options.careerId)) ||
    !/^[a-zA-Z0-9_-]{1,80}$/.test(options.key)
  )
    throw new ApiError("VALIDATION_ERROR");
  const controller = new AbortController();
  let timedOut = false;
  let polls = 0;
  const cancel = () => controller.abort();
  const onVisibility = () => {
    if (document.visibilityState === "hidden") cancel();
  };
  options.signal.addEventListener("abort", cancel, { once: true });
  document.addEventListener("visibilitychange", onVisibility);
  const timeout = setTimeout(() => {
    timedOut = true;
    cancel();
  }, 90_000);
  const check = () => {
    if (controller.signal.aborted || options.signal.aborted) {
      if (timedOut) throw new ApiError("TIMEOUT");
      throw new DOMException("Aborted", "AbortError");
    }
  };
  const scope = <T extends ScopedRun>(run: T): T => {
    check();
    if (
      run.programme_id !== programmeId ||
      run.programme_revision_id !== revisionId ||
      !["offline", "live"].includes(run.mode)
    )
      throw new ApiError("INVALID_RESPONSE");
    // Queued jobs have no admitted evidence packet yet. Their flag is not a
    // permission to show results; only status is polled until terminal state.
    if (run.needs_evidence_revalidation && !pending(run))
      throw new ApiError("EVIDENCE_WITHHELD", 409);
    if (run.status === "FAILED") throw new ApiError("REQUEST_FAILED");
    if (!complete(run) && !pending(run)) throw new ApiError("INVALID_RESPONSE");
    return run;
  };
  const get = async <T extends ScopedRun>(path: string, schema: string) => {
    check();
    const run = scope(
      validateResponse<T>(
        await api.get(path, schema, controller.signal),
        schema,
      ),
    );
    if (run.id !== path.split("/").at(-1))
      throw new ApiError("INVALID_RESPONSE");
    return run;
  };
  const history = async <T extends ScopedRun>(path: string, schema: string) => {
    check();
    const rows = await api.all<T>(path, schema, controller.signal);
    check();
    return byCreatedAt(rows).filter((row) => {
      if (row.programme_id !== programmeId)
        throw new ApiError("INVALID_RESPONSE");
      return (
        row.programme_revision_id === revisionId &&
        (pending(row) || (complete(row) && !row.needs_evidence_revalidation))
      );
    });
  };
  const pause = () =>
    new Promise<void>((resolve, reject) => {
      check();
      const aborted = () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = setTimeout(() => {
        controller.signal.removeEventListener("abort", aborted);
        resolve();
      }, 1000);
      controller.signal.addEventListener("abort", aborted, { once: true });
    });
  const finish = async <T extends ScopedRun>(
    initial: T,
    path: string,
    schema: string,
  ): Promise<T> => {
    let run = scope(validateResponse<T>(initial, schema));
    while (pending(run)) {
      if (++polls > 90) throw new ApiError("TIMEOUT");
      await pause();
      const fresh = await get<T>(path, schema);
      if (fresh.id !== run.id) throw new ApiError("INVALID_RESPONSE");
      run = fresh;
    }
    return run;
  };
  const queue = async <T extends ScopedRun>(
    path: string,
    schema: string,
    body: unknown,
  ) => {
    check();
    const queued = scope(
      validateResponse<T>(
        await api.request(path, schema, {
          method: "POST",
          body,
          signal: controller.signal,
        }),
        schema,
      ),
    );
    if (queued.mode !== "offline") throw new ApiError("INVALID_RESPONSE");
    return queued;
  };
  try {
    if (options.signal.aborted || document.visibilityState === "hidden")
      cancel();
    check();
    options.onProgress("Preparing course findings…");
    const analyses = await history<AnalysisRun>(
      `/api/v1/programmes/${programmeId}/analyses`,
      "Page_AnalysisRead_",
    );
    const analysis = analyses[0]
      ? await get<AnalysisRun>(
          `/api/v1/analyses/${analyses[0].id}`,
          "AnalysisRead",
        )
      : await queue<AnalysisRun>(
          `/api/v1/programmes/${programmeId}/analyses`,
          "AnalysisRead",
          {
            revision_id: revisionId,
            mode: "offline",
            research: false,
            idempotency_key: `${options.key}-courses`,
          },
        );
    const finishedAnalysis = await finish(
      analysis,
      `/api/v1/analyses/${analysis.id}`,
      "AnalysisRead",
    );
    options.onProgress("Preparing career and competency findings…");
    let career: CareerRun;
    if (options.careerId) {
      career = await get<CareerRun>(
        `/api/v1/career-analyses/${options.careerId}`,
        "CareerRead",
      );
      if (career.id !== options.careerId)
        throw new ApiError("INVALID_RESPONSE");
    } else {
      const careers = await history<CareerRun>(
        `/api/v1/programmes/${programmeId}/career-analyses`,
        "Page_CareerRead_",
      );
      career = careers[0]
        ? await get<CareerRun>(
            `/api/v1/career-analyses/${careers[0].id}`,
            "CareerRead",
          )
        : await queue<CareerRun>(
            `/api/v1/programmes/${programmeId}/career-analyses`,
            "CareerRead",
            {
              revision_id: revisionId,
              mode: "offline",
              idempotency_key: `${options.key}-career`,
            },
          );
    }
    career = await finish(
      career,
      `/api/v1/career-analyses/${career.id}`,
      "CareerRead",
    );
    const careerResult = safeCareerResult(career, programmeId, revisionId);
    if (!careerResult) throw new ApiError("INVALID_RESPONSE");
    const recommendationCount = careerResult.recommendations?.length || 0;
    if (!recommendationCount) {
      options.onProgress(
        "Findings are ready; more evidence is needed before recommendations and pathways.",
      );
      return {
        analysisId: finishedAnalysis.id,
        careerId: career.id,
        planId: null,
        recommendationCount,
      };
    }
    options.onProgress("Preparing academic pathways and action plan…");
    const plans = await history<PlanRun>(
      `/api/v1/career-analyses/${career.id}/action-plans`,
      "Page_PlanRead_",
    );
    const eligible = plans.find(
      (row) =>
        row.career_run_id === career.id &&
        row.career_fingerprint === career.fingerprint &&
        row.request_json.phase4_analysis_id === finishedAnalysis.id,
    );
    let plan = eligible
      ? await get<PlanRun>(`/api/v1/action-plans/${eligible.id}`, "PlanRead")
      : await queue<PlanRun>(
          `/api/v1/career-analyses/${career.id}/action-plans`,
          "PlanRead",
          {
            mode: "offline",
            phase4_analysis_id: finishedAnalysis.id,
            idempotency_key: `${options.key}-plan`,
          },
        );
    plan = await finish(plan, `/api/v1/action-plans/${plan.id}`, "PlanRead");
    const planResult = safePlanResult(plan, career, programmeId, revisionId);
    if (
      !planResult ||
      plan.request_json.phase4_analysis_id !== finishedAnalysis.id ||
      planResult.inputs.phase4_analysis_id !== finishedAnalysis.id
    )
      throw new ApiError("INVALID_RESPONSE");
    check();
    options.onProgress(
      "Your evidence-aware findings and action plan are ready.",
    );
    return {
      analysisId: finishedAnalysis.id,
      careerId: career.id,
      planId: plan.id,
      recommendationCount,
    };
  } catch (failure) {
    if (timedOut) throw new ApiError("TIMEOUT");
    if (controller.signal.aborted || options.signal.aborted)
      throw new DOMException("Aborted", "AbortError");
    throw failure instanceof ApiError
      ? failure
      : new ApiError("INVALID_RESPONSE");
  } finally {
    clearTimeout(timeout);
    options.signal.removeEventListener("abort", cancel);
    document.removeEventListener("visibilitychange", onVisibility);
  }
}
