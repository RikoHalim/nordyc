import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "../src/api/client";
import type {
  CareerResult,
  CareerRun,
  Model,
  PlanResult,
  PlanRun,
} from "../src/api/types";
import { prepareReview } from "../src/lib/prepare-review";
import scenarios from "../../examples/api/scenarios.synthetic.json";

const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const now = "2026-10-25T00:00:00Z";
const fingerprint = "a".repeat(64);
const programmeId = id(1),
  revisionId = id(2),
  analysisId = id(4),
  careerId = id(5),
  planId = id(6);
function fixtures(withRecommendations = true) {
  const recommendation: Model<"AcademicRecommendation"> = {
    key: "review-missing-evidence",
    programme_revision_id: revisionId,
    category: "request_review",
    action: "Review the fictional assessment evidence.",
    rationale: "The synthetic evidence does not establish content coverage.",
    minimum_sufficient_intervention: "Request the missing assessment passage.",
    alternatives: [
      {
        category: "request_review",
        action: "Request evidence.",
        rationale: "Resolve uncertainty.",
      },
    ],
    no_change_option: {
      category: "no_change",
      action: "Retain existing content pending review.",
      rationale: "No drastic change is justified.",
    },
    competency_objective: "Clarify bounded evidence.",
    evidence_sufficiency: "insufficient_evidence",
    priority: "review_first",
    priority_basis: "Missing evidence needs review.",
    review_status: "needs_evidence",
    academic_review_required: true,
    automatic_curriculum_change: false,
  };
  const result: CareerResult = {
    schema_version: "phase5-career-1",
    method_version: "phase5-requirement-coverage-1",
    programme_id: programmeId,
    programme_revision_id: revisionId,
    as_of: now,
    is_synthetic: true,
    status: "insufficient_evidence",
    ranking_basis: "No ranking is justified by these fictional inputs.",
    occupations: [],
    competencies: [],
    recommendations: withRecommendations ? [recommendation] : [],
    evidence: [],
    course_ids: [id(3)],
  };
  const career: CareerRun = {
    id: careerId,
    institution_id: id(9),
    programme_id: programmeId,
    programme_revision_id: revisionId,
    created_at: now,
    updated_at: now,
    started_at: now,
    completed_at: now,
    job_id: id(8),
    is_synthetic: true,
    mode: "offline",
    status: "PARTIAL",
    error: null,
    request_json: { mode: "offline", revision_id: revisionId },
    manifest_json: {},
    result_json: result,
    model_usage_json: { status: "deterministic", request_count: 0 },
    fingerprint,
    method_version: result.method_version,
    schema_version: result.schema_version,
    model_name: null,
    needs_evidence_revalidation: false,
  };
  const analysis: Model<"AnalysisRead"> = {
    id: analysisId,
    institution_id: id(9),
    programme_id: programmeId,
    programme_revision_id: revisionId,
    created_at: now,
    updated_at: now,
    started_at: now,
    completed_at: now,
    job_id: id(7),
    is_synthetic: true,
    mode: "offline",
    status: "PARTIAL",
    error: null,
    request_json: { mode: "offline", research: false, revision_id: revisionId },
    manifest_json: {},
    summary_json: {},
    research_json: {},
    fingerprint,
    model_name: null,
    prompt_version: null,
    schema_version: "phase4-course-1",
    needs_evidence_revalidation: false,
  };
  const planResult: PlanResult = {
    schema_version: "phase6-action-plan-1",
    method_version: "phase6-pathways-1",
    programme_id: programmeId,
    programme_revision_id: revisionId,
    career_run_id: careerId,
    career_fingerprint: fingerprint,
    as_of: now,
    is_synthetic: true,
    status: "insufficient_evidence",
    overview: {
      institution_id: id(9),
      institution_name: "Fictional Test University",
      programme_id: programmeId,
      programme_name: "Synthetic Computing",
      programme_revision_id: revisionId,
      revision_label: "Synthetic revision",
      course_ids: [id(3)],
    },
    career: result,
    recommendations: [],
    pathways: [],
    resources: [],
    scenarios: scenarios.response.items as Model<"FutureScenario">[],
    comparison: {
      scenario_keys: [
        "gradual_workforce_transformation",
        "accelerated_ai_adoption",
      ],
      dimensions: [],
      changed_recommendation_ids: [],
      unchanged_recommendation_ids: [],
      no_regret_recommendation_ids: [],
      explanation: "No forced curriculum changes.",
    },
    sdg_alignments: [],
    evidence: [],
    permission_policy: {},
    inputs: { mode: "offline", phase4_analysis_id: analysisId },
  };
  const plan: PlanRun = {
    ...career,
    id: planId,
    career_run_id: careerId,
    career_fingerprint: fingerprint,
    result_json: planResult,
    request_json: { mode: "offline", phase4_analysis_id: analysisId },
    schema_version: planResult.schema_version,
    method_version: planResult.method_version,
  };
  return { analysis, career, plan };
}
function setup(withRecommendations = true) {
  const rows = fixtures(withRecommendations);
  const api = new ApiClient("SYNTHETIC-OFFLINE-TEST-ONLY");
  const all = vi
    .spyOn(api, "all")
    .mockImplementation(
      async (path) =>
        (path.endsWith("/analyses")
          ? [rows.analysis]
          : path.endsWith("/career-analyses")
            ? [rows.career]
            : [rows.plan]) as never,
    );
  const get = vi
    .spyOn(api, "get")
    .mockImplementation(
      async (path) =>
        (path.includes("/career-analyses/")
          ? rows.career
          : path.includes("/action-plans/")
            ? rows.plan
            : rows.analysis) as never,
    );
  const request = vi
    .spyOn(api, "request")
    .mockImplementation(
      async (path) =>
        (path.endsWith("/analyses")
          ? rows.analysis
          : path.endsWith("/career-analyses")
            ? rows.career
            : rows.plan) as never,
    );
  const controller = new AbortController();
  const options = {
    key: "review-test",
    signal: controller.signal,
    onProgress: vi.fn(),
  };
  return { ...rows, api, all, get, request, controller, options };
}
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("bounded protected offline preparation", () => {
  it("reuses fresh exact-revision PARTIAL results and exact Phase 4 plan lineage without writes", async () => {
    const state = setup();
    await expect(
      prepareReview(state.api, programmeId, revisionId, state.options),
    ).resolves.toEqual({
      analysisId,
      careerId,
      planId,
      recommendationCount: 1,
    });
    expect(state.request).not.toHaveBeenCalled();
    expect(state.get.mock.calls.map(([path]) => path)).toEqual([
      `/api/v1/analyses/${analysisId}`,
      `/api/v1/career-analyses/${careerId}`,
      `/api/v1/action-plans/${planId}`,
    ]);
  });
  it("queues only the three documented offline stages with stable keys, no mappings, research, or approvals", async () => {
    const state = setup();
    state.all.mockResolvedValue([]);
    await prepareReview(state.api, programmeId, revisionId, state.options);
    expect(
      state.request.mock.calls.map(([path, , options]) => ({
        path,
        method: options?.method,
        body: options?.body,
      })),
    ).toEqual([
      {
        path: `/api/v1/programmes/${programmeId}/analyses`,
        method: "POST",
        body: {
          revision_id: revisionId,
          mode: "offline",
          research: false,
          idempotency_key: "review-test-courses",
        },
      },
      {
        path: `/api/v1/programmes/${programmeId}/career-analyses`,
        method: "POST",
        body: {
          revision_id: revisionId,
          mode: "offline",
          idempotency_key: "review-test-career",
        },
      },
      {
        path: `/api/v1/career-analyses/${careerId}/action-plans`,
        method: "POST",
        body: {
          mode: "offline",
          phase4_analysis_id: analysisId,
          idempotency_key: "review-test-plan",
        },
      },
    ]);
    expect(
      state.request.mock.calls.every(
        ([, , options]) => options?.signal instanceof AbortSignal,
      ),
    ).toBe(true);
  });
  it("waits for an existing pending job and does not duplicate its submission", async () => {
    vi.useFakeTimers();
    const state = setup(false);
    state.get.mockResolvedValueOnce({
      ...state.analysis,
      status: "RUNNING",
      completed_at: null,
    });
    const result = prepareReview(
      state.api,
      programmeId,
      revisionId,
      state.options,
    );
    await vi.advanceTimersByTimeAsync(1000);
    await expect(result).resolves.toMatchObject({
      analysisId,
      careerId,
      planId: null,
      recommendationCount: 0,
    });
    expect(state.request).not.toHaveBeenCalled();
    expect(
      state.get.mock.calls.filter(([path]) => path.includes("/analyses/")),
    ).toHaveLength(2);
  });
  it("rejects a queued response that contradicts the explicitly offline submission", async () => {
    const state = setup();
    state.all.mockResolvedValue([]);
    state.request.mockResolvedValueOnce({ ...state.analysis, mode: "live" });
    await expect(
      prepareReview(state.api, programmeId, revisionId, state.options),
    ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
    expect(state.request).toHaveBeenCalledTimes(1);
  });
  it("reuses a queued assessment awaiting its evidence packet and only returns the validated terminal result", async () => {
    vi.useFakeTimers();
    const state = setup(false);
    const queued = {
      ...state.career,
      status: "QUEUED" as const,
      completed_at: null,
      needs_evidence_revalidation: true,
      result_json: {},
      fingerprint: null,
    };
    state.all.mockImplementation(
      async (path) =>
        (path.endsWith("/analyses") ? [state.analysis] : [queued]) as never,
    );
    state.get
      .mockResolvedValueOnce(state.analysis)
      .mockResolvedValueOnce(queued)
      .mockResolvedValueOnce(state.career);
    const result = prepareReview(
      state.api,
      programmeId,
      revisionId,
      state.options,
    );
    await vi.advanceTimersByTimeAsync(1000);
    await expect(result).resolves.toMatchObject({
      analysisId,
      careerId,
      planId: null,
    });
    expect(state.request).not.toHaveBeenCalled();
    expect(state.get).toHaveBeenCalledTimes(3);
  });
  it("allows polling a newly queued assessment but rejects terminal evidence revalidation", async () => {
    vi.useFakeTimers();
    const state = setup(false);
    state.all.mockResolvedValueOnce([state.analysis]).mockResolvedValueOnce([]);
    state.request.mockResolvedValueOnce({
      ...state.career,
      status: "QUEUED",
      completed_at: null,
      needs_evidence_revalidation: true,
      result_json: {},
      fingerprint: null,
    });
    state.get.mockResolvedValueOnce(state.analysis).mockResolvedValueOnce({
      ...state.career,
      needs_evidence_revalidation: true,
    });
    const result = prepareReview(
      state.api,
      programmeId,
      revisionId,
      state.options,
    );
    const rejection = expect(result).rejects.toMatchObject({
      code: "EVIDENCE_WITHHELD",
    });
    await vi.advanceTimersByTimeAsync(1000);
    await rejection;
    expect(state.request).toHaveBeenCalledTimes(1);
    expect(state.request.mock.calls[0][0]).toBe(
      `/api/v1/programmes/${programmeId}/career-analyses`,
    );
  });
  it("reports a worker failure without submitting a replacement or repair", async () => {
    vi.useFakeTimers();
    const state = setup();
    state.get
      .mockResolvedValueOnce({ ...state.analysis, status: "RUNNING" })
      .mockResolvedValueOnce({ ...state.analysis, status: "FAILED" });
    const result = prepareReview(
      state.api,
      programmeId,
      revisionId,
      state.options,
    );
    const rejection = expect(result).rejects.toMatchObject({
      code: "REQUEST_FAILED",
    });
    await vi.advanceTimersByTimeAsync(1000);
    await rejection;
    expect(state.get).toHaveBeenCalledTimes(2);
    expect(state.request).not.toHaveBeenCalled();
  });
  it("cancels preparation on a hidden tab and clears the worker poll", async () => {
    vi.useFakeTimers();
    const state = setup();
    state.get.mockResolvedValue({ ...state.analysis, status: "RUNNING" });
    const result = prepareReview(
      state.api,
      programmeId,
      revisionId,
      state.options,
    );
    const rejection = expect(result).rejects.toMatchObject({
      name: "AbortError",
    });
    await vi.advanceTimersByTimeAsync(0);
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    document.dispatchEvent(new Event("visibilitychange"));
    await rejection;
    await vi.advanceTimersByTimeAsync(2000);
    expect(state.get).toHaveBeenCalledTimes(1);
    expect(state.request).not.toHaveBeenCalled();
  });
  it("returns honest no-plan state when a valid assessment has no recommendations", async () => {
    const state = setup(false);
    await expect(
      prepareReview(state.api, programmeId, revisionId, state.options),
    ).resolves.toEqual({
      analysisId,
      careerId,
      planId: null,
      recommendationCount: 0,
    });
    expect(
      state.all.mock.calls.some(([path]) => path.includes("/action-plans")),
    ).toBe(false);
    expect(state.request).not.toHaveBeenCalled();
  });
  it("honours an explicit assessment instead of silently substituting latest history", async () => {
    const state = setup(false);
    await prepareReview(state.api, programmeId, revisionId, {
      ...state.options,
      careerId,
    });
    expect(state.all.mock.calls.map(([path]) => path)).toEqual([
      `/api/v1/programmes/${programmeId}/analyses`,
    ]);
    expect(state.get).toHaveBeenCalledWith(
      `/api/v1/career-analyses/${careerId}`,
      "CareerRead",
      expect.any(AbortSignal),
    );
  });
  it.each([
    ["wrong programme", { programme_id: id(99) }, "INVALID_RESPONSE"],
    ["wrong revision", { programme_revision_id: id(99) }, "INVALID_RESPONSE"],
    [
      "stale evidence",
      { needs_evidence_revalidation: true },
      "EVIDENCE_WITHHELD",
    ],
    ["failed job", { status: "FAILED" }, "REQUEST_FAILED"],
    ["undocumented execution mode", { mode: "premium" }, "INVALID_RESPONSE"],
    [
      "invalid model metadata",
      { model_name: { provider: "invented" } },
      "INVALID_RESPONSE",
    ],
  ])(
    "rejects %s in the fresh selected assessment without retrying or substituting",
    async (_, changed, code) => {
      const state = setup();
      state.get
        .mockResolvedValueOnce(state.analysis)
        .mockResolvedValueOnce({ ...state.career, ...changed } as never);
      await expect(
        prepareReview(state.api, programmeId, revisionId, {
          ...state.options,
          careerId,
        }),
      ).rejects.toMatchObject({ code });
      expect(state.request).not.toHaveBeenCalled();
    },
  );
  it("does not reuse a plan bound to another Phase 4 run", async () => {
    const state = setup();
    state.all.mockImplementation(
      async (path) =>
        (path.endsWith("/analyses")
          ? [state.analysis]
          : path.endsWith("/career-analyses")
            ? [state.career]
            : [
                { ...state.plan, request_json: { phase4_analysis_id: id(90) } },
              ]) as never,
    );
    await prepareReview(state.api, programmeId, revisionId, state.options);
    expect(state.request).toHaveBeenCalledTimes(1);
    expect(state.request.mock.calls[0][0]).toBe(
      `/api/v1/career-analyses/${careerId}/action-plans`,
    );
  });
  it("rejects a returned plan with a different career fingerprint", async () => {
    const state = setup();
    state.get
      .mockResolvedValueOnce(state.analysis)
      .mockResolvedValueOnce(state.career)
      .mockResolvedValueOnce({
        ...state.plan,
        career_fingerprint: "b".repeat(64),
      });
    await expect(
      prepareReview(state.api, programmeId, revisionId, state.options),
    ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
    expect(state.request).not.toHaveBeenCalled();
  });
  it("aborts an awaiting worker when the owning view is cancelled", async () => {
    vi.useFakeTimers();
    const state = setup();
    state.get.mockResolvedValue({
      ...state.analysis,
      status: "RUNNING",
      completed_at: null,
    });
    const result = prepareReview(
      state.api,
      programmeId,
      revisionId,
      state.options,
    );
    const rejection = expect(result).rejects.toMatchObject({
      name: "AbortError",
    });
    await vi.advanceTimersByTimeAsync(0);
    state.controller.abort();
    await rejection;
    await vi.advanceTimersByTimeAsync(2000);
    expect(state.get).toHaveBeenCalledTimes(1);
    expect(state.request).not.toHaveBeenCalled();
  });
  it("ends a stopped-worker wait after 90 seconds without a repair or retry request", async () => {
    vi.useFakeTimers();
    const state = setup();
    state.get.mockResolvedValue({
      ...state.analysis,
      status: "QUEUED",
      completed_at: null,
    });
    const result = prepareReview(
      state.api,
      programmeId,
      revisionId,
      state.options,
    );
    const rejection = expect(result).rejects.toMatchObject({ code: "TIMEOUT" });
    await vi.advanceTimersByTimeAsync(90_000);
    await rejection;
    expect(state.request).not.toHaveBeenCalled();
    expect(state.get.mock.calls.length).toBeLessThanOrEqual(90);
  });
});
