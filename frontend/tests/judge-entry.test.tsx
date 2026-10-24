import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import scenarios from "../../examples/api/scenarios.synthetic.json";
import { ApiClient } from "../src/api/client";
import type {
  AccessContext,
  CareerResult,
  CareerRun,
  Institution,
  Model,
  PlanResult,
  PlanRun,
  Programme,
} from "../src/api/types";
import { SessionContext } from "../src/app/session";
import SampleProgrammeEntry from "../src/components/SampleProgrammeEntry";

const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const now = "2026-10-25T00:00:00Z";
const hash = "a".repeat(64);
const credential = "SYNTHETIC-JUDGE-TEST-CREDENTIAL-NOT-LIVE";
const institution: Institution = {
  id: id(1),
  name: "Fictional Demonstration University",
  country: "MY",
  website_url: "https://synthetic.example.invalid",
  source_id: null,
  source_locator: null,
  is_synthetic: true,
  data_quality: "synthetic",
  created_at: now,
  updated_at: now,
};
const programme: Programme = {
  id: id(2),
  institution_id: institution.id,
  name: "Fictional Prepared Programme",
  programme_code: null,
  academic_year: null,
  active_revision_id: id(3),
  active_revision: {
    id: id(3),
    programme_id: id(2),
    version_label: "Fictional revision",
    effective_date: null,
    is_synthetic: true,
    created_at: now,
    updated_at: now,
  },
  level: "undergraduate",
  discipline_key: "computing",
  canonical_url: "https://synthetic.example.invalid/programme",
  source_id: null,
  source_locator: null,
  is_synthetic: true,
  data_quality: "synthetic",
  created_at: now,
  updated_at: now,
};
const inventory: Model<"CoverageRead"> = {
  programme_id: programme.id,
  programme_revision_id: programme.active_revision_id,
  course_count: 1,
  verified_title_count: 0,
  needs_review_count: 1,
  title_only_count: 1,
  is_synthetic: true,
  graduation_curriculum_complete: false,
};
const careerResult: CareerResult = {
  schema_version: "phase5-career-1",
  method_version: "phase5-requirement-coverage-1",
  programme_id: programme.id,
  programme_revision_id: id(3),
  as_of: now,
  is_synthetic: true,
  status: "insufficient_evidence",
  course_ids: [id(4)],
  ranking_basis: "No comparable evidence establishes a ranking.",
  occupations: [],
  competencies: [],
  recommendations: [],
  evidence: [],
  limitations: ["Explicit synthetic evidence limitations remain visible."],
};
const career: CareerRun = {
  id: id(5),
  institution_id: institution.id,
  programme_id: programme.id,
  programme_revision_id: id(3),
  created_at: now,
  updated_at: now,
  started_at: now,
  completed_at: now,
  job_id: id(6),
  is_synthetic: true,
  mode: "offline",
  status: "PARTIAL",
  error: null,
  request_json: {},
  manifest_json: {},
  result_json: careerResult,
  model_usage_json: { status: "deterministic" },
  fingerprint: hash,
  method_version: careerResult.method_version,
  schema_version: careerResult.schema_version,
  model_name: null,
  needs_evidence_revalidation: false,
};
const planResult: PlanResult = {
  schema_version: "phase6-action-plan-1",
  method_version: "phase6-pathways-1",
  programme_id: programme.id,
  programme_revision_id: id(3),
  career_run_id: career.id,
  career_fingerprint: hash,
  as_of: now,
  is_synthetic: true,
  status: "insufficient_evidence",
  overview: {
    institution_id: institution.id,
    institution_name: institution.name,
    programme_id: programme.id,
    programme_name: programme.name,
    programme_revision_id: id(3),
    revision_label: "Fictional revision",
    course_ids: [id(4)],
  },
  career: careerResult,
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
    explanation: "The same admitted evidence does not force academic changes.",
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
const plan: PlanRun = {
  ...career,
  id: id(7),
  career_run_id: career.id,
  career_fingerprint: hash,
  result_json: planResult,
  method_version: planResult.method_version,
  schema_version: planResult.schema_version,
};
const access: AccessContext = {
  access_mode: "scoped",
  authenticated: true,
  operator_alias: "Fictional read-only judge",
  identity_kind: "operator_grant",
  permissions: ["read"],
  institution_ids: [institution.id],
  global_admin: false,
  execution: {
    external_processing_allowed: false,
    research_enabled: false,
    claude_enabled: false,
  },
  limitations: [],
};
const json = (value: unknown) =>
  new Response(JSON.stringify(value), {
    headers: { "Content-Type": "application/json" },
  });
const page = (items: unknown[]) => ({
  items,
  total: items.length,
  limit: 100,
  offset: 0,
});

beforeEach(() => {
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function show({
  programmes = [programme],
  institutions = [institution],
  coverage = new Map([[programme.id, inventory]]),
  careers = [career],
  plans = [plan],
}: {
  programmes?: Programme[];
  institutions?: Institution[];
  coverage?: Map<string, Model<"CoverageRead">>;
  careers?: CareerRun[];
  plans?: PlanRun[];
} = {}) {
  const fetch = vi.fn(async (input: string, _init?: RequestInit) => {
    const url = new URL(input, window.location.origin);
    if (url.pathname === `/api/v1/programmes/${programme.id}/career-analyses`)
      return json(page(careers));
    if (url.pathname === `/api/v1/career-analyses/${career.id}/action-plans`)
      return json(page(plans));
    throw new Error("Unexpected synthetic sample read");
  });
  vi.stubGlobal("fetch", fetch);
  const api = new ApiClient(credential);
  render(
    <SessionContext.Provider value={{ api, access, disconnect: vi.fn() }}>
      <MemoryRouter>
        <Routes>
          <Route
            path="/"
            element={
              <SampleProgrammeEntry
                programmes={programmes}
                institutions={institutions}
                coverage={coverage}
              />
            }
          />
          <Route
            path="/programmes/:programmeId/overview"
            element={<h1>Stored synthetic programme overview</h1>}
          />
        </Routes>
      </MemoryRouter>
    </SessionContext.Provider>,
  );
  return fetch;
}

describe("judge sample programme entry", () => {
  it("opens a completed backend sample for a read-only judge without mutation or credentials in the URL", async () => {
    const empty = {
      ...programme,
      id: id(8),
      name: "Empty fictional programme",
      active_revision_id: null,
      active_revision: null,
    };
    const fetch = show({ programmes: [empty, programme] });
    expect(screen.getByText("Demo data — fictional example.")).toBeVisible();
    const link = await screen.findByRole("link", {
      name: "Explore Sample Programme",
    });
    const url = new URL(link.getAttribute("href")!, window.location.origin);
    expect(url.pathname).toBe(`/programmes/${programme.id}/overview`);
    expect(Object.fromEntries(url.searchParams)).toEqual({
      revision: id(3),
      career: career.id,
      plan: plan.id,
    });
    expect(link.getAttribute("href")).not.toContain(credential);
    expect(fetch.mock.calls).toHaveLength(2);
    expect(fetch.mock.calls.every(([, init]) => init?.method === "GET")).toBe(
      true,
    );
    expect(
      fetch.mock.calls.every(
        ([path]) => !path.includes(empty.id) && !path.includes(credential),
      ),
    ).toBe(true);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    await userEvent.click(link);
    expect(
      await screen.findByRole("heading", {
        name: "Stored synthetic programme overview",
      }),
    ).toBeVisible();
  });

  it.each([
    [
      "real institution",
      { institutions: [{ ...institution, is_synthetic: false }] },
    ],
    ["real programme", { programmes: [{ ...programme, is_synthetic: false }] }],
    [
      "empty synthetic inventory",
      {
        coverage: new Map([[programme.id, { ...inventory, course_count: 0 }]]),
      },
    ],
    [
      "stale inventory revision",
      {
        coverage: new Map([
          [programme.id, { ...inventory, programme_revision_id: id(9) }],
        ]),
      },
    ],
  ])("does not label a %s as the prepared sample", async (_label, options) => {
    const fetch = show(options);
    expect(
      await screen.findByText(/No prepared sample programme is available/),
    ).toBeVisible();
    expect(
      screen.queryByRole("link", { name: "Explore Sample Programme" }),
    ).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each([
    ["pending", { ...career, status: "RUNNING" as const, completed_at: null }],
    ["withheld", { ...career, needs_evidence_revalidation: true }],
    ["wrong revision", { ...career, programme_revision_id: id(9) }],
    ["non-synthetic", { ...career, is_synthetic: false }],
  ])("does not use a %s career run", async (_label, row) => {
    const fetch = show({ careers: [row] });
    expect(
      await screen.findByText(/No prepared sample programme is available/),
    ).toBeVisible();
    expect(
      screen.queryByRole("link", { name: "Explore Sample Programme" }),
    ).toBeNull();
    expect(fetch.mock.calls).toHaveLength(1);
  });

  it("fails closed when the Action Plan references a different career version", async () => {
    show({ plans: [{ ...plan, career_fingerprint: "b".repeat(64) }] });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "INVALID_RESPONSE",
    );
    expect(
      screen.queryByRole("link", { name: "Explore Sample Programme" }),
    ).toBeNull();
  });

  it("does not open a sample when its plan omits an inventoried course", async () => {
    show({
      plans: [
        {
          ...plan,
          result_json: {
            ...planResult,
            overview: { ...planResult.overview, course_ids: [] },
          },
        },
      ],
    });
    expect(
      await screen.findByText(/No prepared sample programme is available/),
    ).toBeVisible();
    expect(
      screen.queryByRole("link", { name: "Explore Sample Programme" }),
    ).toBeNull();
  });

  it("rejects duplicated course IDs as complete inventory coverage", async () => {
    show({
      careers: [
        {
          ...career,
          result_json: { ...careerResult, course_ids: [id(4), id(4)] },
        },
      ],
    });
    expect(
      await screen.findByText(/No prepared sample programme is available/),
    ).toBeVisible();
    expect(
      screen.queryByRole("link", { name: "Explore Sample Programme" }),
    ).toBeNull();
  });

  it("clears the sample link on focus revalidation when evidence becomes withheld", async () => {
    const rows = [plan];
    show({ plans: rows });
    await screen.findByRole("link", { name: "Explore Sample Programme" });
    rows[0] = { ...plan, needs_evidence_revalidation: true };
    fireEvent.focus(window);
    await waitFor(() => {
      expect(
        screen.queryByRole("link", { name: "Explore Sample Programme" }),
      ).toBeNull();
    });
    expect(
      await screen.findByText(/No prepared sample programme is available/),
    ).toBeVisible();
  });
});
