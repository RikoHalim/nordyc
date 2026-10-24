import { render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import type {
  CareerResult,
  CareerRun,
  Model,
  PlanResult,
  PlanRun,
} from "../src/api/types";
import { ApiClient } from "../src/api/client";
import { Workspace, type WorkspaceContext } from "../src/app/workspace";
import {
  byCreatedAt,
  safeCareerResult,
  safePlanResult,
} from "../src/lib/results";
import IntelligencePage from "../src/pages/Intelligence";
import scenarios from "../../examples/api/scenarios.synthetic.json";

const { resultsMock } = vi.hoisted(() => ({ resultsMock: vi.fn() }));
vi.mock("../src/lib/results", async (original) => ({
  ...(await original<typeof import("../src/lib/results")>()),
  useAnalysisResults: resultsMock,
}));

const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const now = "2026-10-25T01:00:00Z";
const hash = "a".repeat(64);
function careerResult(): CareerResult {
  return {
    schema_version: "phase5-career-1",
    method_version: "phase5-requirement-coverage-1",
    programme_id: id(1),
    programme_revision_id: id(2),
    as_of: now,
    is_synthetic: true,
    status: "insufficient_evidence",
    course_ids: [id(3)],
    ranking_basis: "Insufficient comparable evidence.",
    occupations: [],
    competencies: [],
    recommendations: [],
    evidence: [],
    limitations: ["Fictional test data only."],
  };
}
function careerRun(result = careerResult()): CareerRun {
  return {
    id: id(4),
    created_at: now,
    updated_at: now,
    is_synthetic: true,
    institution_id: id(5),
    programme_id: id(1),
    programme_revision_id: id(2),
    job_id: id(6),
    mode: "offline",
    status: "PARTIAL",
    started_at: now,
    completed_at: now,
    error: null,
    request_json: {},
    manifest_json: {},
    result_json: result,
    model_usage_json: { status: "deterministic" },
    fingerprint: hash,
    method_version: result.method_version,
    schema_version: result.schema_version,
    model_name: null,
    needs_evidence_revalidation: false,
  };
}
function planResult(career = careerResult()): PlanResult {
  return {
    schema_version: "phase6-action-plan-1",
    method_version: "phase6-pathways-1",
    programme_id: id(1),
    programme_revision_id: id(2),
    career_run_id: id(4),
    career_fingerprint: hash,
    as_of: now,
    is_synthetic: true,
    status: "insufficient_evidence",
    overview: {
      institution_id: id(5),
      institution_name: "Fictional Test University",
      programme_id: id(1),
      programme_name: "Synthetic Computing",
      programme_revision_id: id(2),
      revision_label: "Fictional revision",
      course_ids: [id(3)],
    },
    career,
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
      explanation: "Same admitted evidence; no forced change.",
    },
    sdg_alignments: [],
    review: {
      status: "proposed",
      academic_approval: false,
      implementation_authorised: false,
    },
    evidence: [],
    permission_policy: {},
    inputs: { mode: "offline" },
  };
}
function planRun(result = planResult()): PlanRun {
  const base = careerRun();
  return {
    ...base,
    id: id(7),
    career_run_id: id(4),
    career_fingerprint: hash,
    result_json: result,
    method_version: result.method_version,
    schema_version: result.schema_version,
  };
}
function workspace(
  api = new ApiClient("SYNTHETIC-TEST-ONLY"),
  permissions: Model<"AccessContext">["permissions"] = ["read"],
): WorkspaceContext {
  return {
    api,
    access: {
      access_mode: "scoped",
      authenticated: true,
      operator_alias: "Fictional operator grant",
      identity_kind: "operator_grant",
      permissions,
      institution_ids: [id(5)],
      global_admin: false,
      execution: {} as Model<"ExecutionConfiguration">,
      limitations: [],
    },
    programme: {
      id: id(1),
      name: "Synthetic Computing",
      institution_id: id(5),
    } as WorkspaceContext["programme"],
    institution: {
      id: id(5),
      name: "Fictional Test University",
    } as WorkspaceContext["institution"],
    revisionId: id(2),
    revisions: [],
    setRevision: vi.fn(),
  };
}
function state(extra = {}) {
  const career = careerRun();
  const plan = planRun();
  return {
    careerRun: career,
    careerResult: career.result_json as CareerResult,
    planRun: plan,
    planResult: plan.result_json as PlanResult,
    careerChoices: [career],
    planChoices: [plan],
    careerPage: { items: [career], total: 1 },
    planPage: { items: [plan], total: 1 },
    careerOffset: 0,
    planOffset: 0,
    careerId: career.id,
    planId: plan.id,
    loading: false,
    planLoading: false,
    error: null,
    planError: null,
    select: vi.fn(),
    page: vi.fn(),
    reload: vi.fn(),
    ...extra,
  };
}
function show(section: string, context = workspace()) {
  return render(
    <MemoryRouter>
      <Workspace.Provider value={context}>
        <IntelligencePage section={section} />
      </Workspace.Provider>
    </MemoryRouter>,
  );
}
beforeEach(() => {
  resultsMock.mockReturnValue(state());
});

describe("fresh structured result gates", () => {
  it("shows status only for a queued assessment before its evidence packet is ready", () => {
    resultsMock.mockReturnValue(
      state({
        careerRun: {
          ...careerRun(),
          status: "QUEUED",
          needs_evidence_revalidation: true,
          result_json: { private: "QUEUED-PRIVATE-CANARY" },
        },
        careerResult: undefined,
        planRun: undefined,
        planResult: undefined,
      }),
    );
    show("recommendations");
    expect(screen.getByRole("status")).toHaveTextContent(
      /Career assessment QUEUED/i,
    );
    expect(screen.queryByText(/QUEUED-PRIVATE-CANARY/)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/This assessment is stale/),
    ).not.toBeInTheDocument();
  });
  it("parses actual OpenAPI result schemas only after source and completion guards", () => {
    expect(safeCareerResult(careerRun())?.status).toBe("insufficient_evidence");
    expect(
      safePlanResult(planRun(), careerRun())?.overview.programme_name,
    ).toBe("Synthetic Computing");
    expect(
      safeCareerResult({
        ...careerRun(),
        needs_evidence_revalidation: true,
        result_json: { private: "WITHHELD-CANARY" },
      }),
    ).toBeNull();
    expect(
      safeCareerResult({ ...careerRun(), status: "RUNNING", result_json: {} }),
    ).toBeNull();
    expect(
      safeCareerResult({ ...careerRun(), status: "FAILED", result_json: {} }),
    ).toBeNull();
  });
  it("rejects malformed completed results, wrong revisions and wrong parent identity", () => {
    expect(() =>
      safeCareerResult({ ...careerRun(), result_json: {} }),
    ).toThrow();
    expect(() => safeCareerResult(careerRun(), id(9), id(2))).toThrow();
    expect(() => safeCareerResult(careerRun(), id(1), id(9))).toThrow();
    expect(() =>
      safePlanResult({ ...planRun(), career_run_id: id(9) }, careerRun()),
    ).toThrow();
    expect(() =>
      safePlanResult(
        { ...planRun(), career_fingerprint: "b".repeat(64) },
        careerRun(),
      ),
    ).toThrow();
  });
  it("orders by creation time rather than lexicographical UUID", () => {
    expect(
      byCreatedAt([
        { id: "zzz", created_at: "2026-01-01T00:00:00Z" },
        { id: "aaa", created_at: now },
      ])[0].id,
    ).toBe("aaa");
  });
});

describe("analytical pages preserve uncertainty", () => {
  it("explains that extraction has not started a career assessment without inventing recommendations", () => {
    const api = new ApiClient("SYNTHETIC-TEST-ONLY");
    const post = vi.spyOn(api, "post");
    resultsMock.mockReturnValue(
      state({
        careerRun: undefined,
        careerResult: undefined,
        planRun: undefined,
        planResult: undefined,
      }),
    );
    show("recommendations", workspace(api));
    expect(
      screen.getByText("Assessment not started for this revision"),
    ).toBeVisible();
    expect(
      screen.getByText(/Uploading a PDF extracts course candidates/),
    ).toBeVisible();
    expect(screen.queryByText(/Assessment finished/)).not.toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("distinguishes a completed evidence-limited assessment from one never run", () => {
    const api = new ApiClient("SYNTHETIC-TEST-ONLY");
    vi.spyOn(api, "get").mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
      needs_evidence_revalidation: false,
    });
    show("recommendations", workspace(api));
    expect(
      screen.getByText("Assessment finished — more evidence needed"),
    ).toBeVisible();
    expect(
      screen.queryByText("Assessment not started for this revision"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/No academic changes are recommended by this result/),
    ).toBeVisible();
    expect(screen.getByText("Fictional test data only.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Record review decision" }),
    ).not.toBeInTheDocument();
  });

  it("keeps a completed non-insufficient empty result neutral", () => {
    const result = { ...careerResult(), status: "supported" as const };
    resultsMock.mockReturnValue(
      state({ careerResult: result, careerRun: careerRun(result) }),
    );
    show("recommendations");
    expect(
      screen.getByText("Assessment finished — no supported proposals recorded"),
    ).toBeVisible();
    expect(
      screen.queryByText("Assessment finished — more evidence needed"),
    ).not.toBeInTheDocument();
  });

  it("explains missing career prerequisites before an action plan exists", () => {
    resultsMock.mockReturnValue(
      state({
        careerRun: undefined,
        careerResult: undefined,
        planRun: undefined,
        planResult: undefined,
      }),
    );
    show("plan");
    expect(screen.getByText("Start with a career assessment")).toBeVisible();
    expect(
      screen.getByText(/An Action Plan needs a completed career assessment/),
    ).toBeVisible();
    expect(
      screen.queryByText(/01 · Programme overview/),
    ).not.toBeInTheDocument();
  });

  it("explains a missing plan after a completed assessment without unsupported proposals", () => {
    resultsMock.mockReturnValue(
      state({ planRun: undefined, planResult: undefined }),
    );
    show("plan");
    expect(screen.getByText("Action plan not started")).toBeVisible();
    expect(
      screen.getByText(
        /No supported recommendation is recorded for this assessment yet/,
      ),
    ).toBeVisible();
    expect(
      screen.queryByText(/01 · Programme overview/),
    ).not.toBeInTheDocument();
  });

  it("shows insufficient occupation evidence instead of screenshot statistics", () => {
    show("industry");
    expect(screen.getByText("No reviewed occupational evidence")).toBeVisible();
    expect(
      screen.getByText(/No screenshot statistics are substituted/i),
    ).toBeVisible();
  });
  it("never displays cached restricted findings or proposal prose", () => {
    resultsMock.mockReturnValue(
      state({
        careerRun: { ...careerRun(), needs_evidence_revalidation: true },
        careerResult: {
          ...careerResult(),
          limitations: ["PRIVATE-CURRICULUM-CANARY"],
        },
      }),
    );
    show("plan");
    expect(
      screen.getByText(
        /Source-derived findings, citations and proposals are withheld/i,
      ),
    ).toBeVisible();
    expect(
      screen.queryByText("PRIVATE-CURRICULUM-CANARY"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/01 · Programme overview/),
    ).not.toBeInTheDocument();
  });
  it("displays a real queued state without claiming worker completion", () => {
    resultsMock.mockReturnValue(
      state({
        careerRun: { ...careerRun(), status: "QUEUED" },
        careerResult: null,
      }),
    );
    show("careers");
    expect(
      screen.getByText(/does not establish that a worker is online/i),
    ).toBeVisible();
  });
  it("renders distinct competency and support states and filters unknowns", async () => {
    const findings: Model<"RequirementFinding">[] = [
      {
        occupation_id: id(10),
        relationship_id: id(11),
        skill_id: id(12),
        skill_name: "Fictional assay review",
        requirement_type: "essential",
        state: "unknown",
        support_type: "unknown",
        explanation: "No reviewed passage establishes coverage.",
        academic_review_required: true,
      },
      {
        occupation_id: id(10),
        relationship_id: id(13),
        skill_id: id(14),
        skill_name: "Fictional laboratory planning",
        requirement_type: "optional",
        state: "partial",
        support_type: "documented_intent",
        explanation: "Intended learning only.",
        academic_review_required: true,
      },
      {
        occupation_id: id(10),
        relationship_id: id(15),
        skill_id: id(16),
        skill_name: "Fictional explicitly audited gap",
        requirement_type: "essential",
        state: "documented_gap",
        support_type: "unknown",
        explanation:
          "An explicit complete reviewed negative audit establishes a gap.",
        academic_review_required: true,
      },
    ];
    resultsMock.mockReturnValue(
      state({ careerResult: { ...careerResult(), competencies: findings } }),
    );
    show("competencies");
    expect(screen.getByText("Fictional laboratory planning")).toBeVisible();
    expect(screen.getByText("Fictional explicitly audited gap")).toBeVisible();
    await userEvent.selectOptions(
      screen.getByLabelText("Competency evidence"),
      "unknown",
    );
    expect(screen.getByText("Fictional assay review")).toBeVisible();
    expect(
      screen.queryByText("Fictional laboratory planning"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Fictional explicitly audited gap"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });
  it("keeps two scenarios hypothetical and SDGs unmeasured", () => {
    const view = show("scenarios");
    expect(
      screen.getByText(/not forecasts or replacement probabilities/i),
    ).toBeVisible();
    expect(screen.getByText("What changes between assumptions")).toBeVisible();
    view.unmount();
    show("sdg");
    expect(
      screen.getByText(/No measured or achieved SDG impact/i),
    ).toBeVisible();
    expect(screen.getByText("No source-supported SDG mapping")).toBeVisible();
  });
  it("renders all eight plan sections while review remains separate and permission-bound", () => {
    show("plan");
    for (const label of [
      "02 · Future career alignment",
      "03 · Competency coverage and gaps",
      "04 · Academic recommendations",
      "05 · Academic pathways",
      "06 · Future workforce scenarios",
      "07 · SDG contribution",
      "08 · Academic review and implementation",
    ])
      expect(screen.getByRole("heading", { name: label })).toBeVisible();
    expect(
      screen.getByText(/Your operator grant has no review permission/),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Record review decision" }),
    ).not.toBeInTheDocument();
  });
  it("keeps offline submission write-gated and does not create jobs while rendering", () => {
    const api = new ApiClient("SYNTHETIC-TEST-ONLY");
    const post = vi.spyOn(api, "post");
    show("careers", workspace(api));
    expect(
      screen.queryByRole("button", { name: "Queue offline career assessment" }),
    ).not.toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });
});

it("real result hook selects only the exact revision and created_at newest assessment", async () => {
  const actual =
    await vi.importActual<typeof import("../src/lib/results")>(
      "../src/lib/results",
    );
  const api = new ApiClient("SYNTHETIC-TEST-ONLY");
  const older = {
    ...careerRun(),
    id: id(8),
    created_at: "2026-01-01T00:00:00Z",
  };
  const foreign = {
    ...careerRun(),
    id: id(9),
    programme_revision_id: id(19),
    created_at: "2026-11-01T00:00:00Z",
  };
  vi.spyOn(api, "get").mockImplementation(async (path) => {
    if (path.includes("/programmes/"))
      return {
        items: [older, foreign, careerRun()],
        total: 3,
        limit: 10,
        offset: 0,
      };
    if (path.endsWith(`/career-analyses/${id(4)}`)) return careerRun();
    if (path.includes("/action-plans?"))
      return { items: [], total: 0, limit: 10, offset: 0 };
    throw new Error(`Unexpected controlled route ${path}`);
  });
  const context = workspace(api);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter>
      <Workspace.Provider value={context}>{children}</Workspace.Provider>
    </MemoryRouter>
  );
  const { result } = renderHook(() => actual.useAnalysisResults(), { wrapper });
  await waitFor(() => expect(result.current.careerRun?.id).toBe(id(4)));
  expect(result.current.careerChoices.map((row) => row.id)).toEqual([
    id(4),
    id(8),
  ]);
  expect(api.get).not.toHaveBeenCalledWith(
    expect.stringContaining(id(9)),
    expect.anything(),
    expect.anything(),
  );
});

describe("explicit version-bound writes", () => {
  it("refetches the exact plan and parent before posting the original fingerprint", async () => {
    const api = new ApiClient("SYNTHETIC-TEST-ONLY");
    const get = vi
      .spyOn(api, "get")
      .mockImplementation(async (path) =>
        path.includes("/career-analyses/") ? careerRun() : planRun(),
      );
    const post = vi.spyOn(api, "post").mockResolvedValue({});
    show("plan", workspace(api, ["read", "review"]));
    await userEvent.selectOptions(
      screen.getByLabelText("Review decision"),
      "under_review",
    );
    await userEvent.type(
      screen.getByLabelText("Reason"),
      "Explicit fictional operator review, not academic implementation approval.",
    );
    expect(post).not.toHaveBeenCalled();
    await userEvent.click(
      screen.getByRole("button", { name: "Record review decision" }),
    );
    await screen.findByText("Review recorded by the backend.");
    expect(get).toHaveBeenCalledWith(
      `/api/v1/action-plans/${id(7)}`,
      "PlanRead",
    );
    expect(get).toHaveBeenCalledWith(
      `/api/v1/career-analyses/${id(4)}`,
      "CareerRead",
    );
    expect(post).toHaveBeenCalledWith(
      `/api/v1/action-plans/${id(7)}/reviews`,
      "PlanReviewRead",
      {
        decision: "under_review",
        reason:
          "Explicit fictional operator review, not academic implementation approval.",
        expected_plan_fingerprint: hash,
      },
    );
  });

  it("blocks a changed or withdrawn plan before posting any review", async () => {
    const api = new ApiClient("SYNTHETIC-TEST-ONLY");
    vi.spyOn(api, "get").mockImplementation(async (path) =>
      path.includes("/career-analyses/")
        ? careerRun()
        : { ...planRun(), needs_evidence_revalidation: true },
    );
    const post = vi.spyOn(api, "post").mockResolvedValue({});
    show("plan", workspace(api, ["read", "review"]));
    await userEvent.type(
      screen.getByLabelText("Reason"),
      "Fictional decision against a now-restricted source.",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record review decision" }),
    );
    await screen.findByText(/The record or its evidence has changed/i);
    expect(post).not.toHaveBeenCalled();
    expect(resultsMock.mock.results[0].value.reload).toHaveBeenCalled();
  });

  it("submits only offline mode after an explicit write-authorised action", async () => {
    const api = new ApiClient("SYNTHETIC-TEST-ONLY");
    const post = vi
      .spyOn(api, "post")
      .mockResolvedValue({ ...careerRun(), status: "QUEUED", result_json: {} });
    show("careers", workspace(api, ["read", "write"]));
    expect(post).not.toHaveBeenCalled();
    await userEvent.click(
      screen.getByText("Prepare an offline assessment or action plan"),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Queue offline career assessment" }),
    );
    await waitFor(() => expect(post).toHaveBeenCalledOnce());
    expect(post).toHaveBeenCalledWith(
      `/api/v1/programmes/${id(1)}/career-analyses`,
      "CareerRead",
      expect.objectContaining({
        mode: "offline",
        revision_id: id(2),
        idempotency_key: expect.stringMatching(/^ui-career-/),
      }),
    );
    expect(post.mock.calls[0][2]).not.toHaveProperty("api_key");
  });
});
