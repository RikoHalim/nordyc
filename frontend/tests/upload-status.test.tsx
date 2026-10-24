import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  MemoryRouter,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import courseFixture from "../../examples/api/courses.synthetic.json";
import { ApiClient } from "../src/api/client";
import { Workspace, type WorkspaceContext } from "../src/app/workspace";
import type { Course, Model } from "../src/api/types";
import UploadPage, { validatePdfOrigin } from "../src/pages/Upload";

const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const now = "2026-10-25T00:00:00Z";
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const revision: Model<"ProgrammeRevisionRead"> = {
  id: id(3),
  programme_id: id(2),
  version_label: "Fictional upload revision",
  effective_date: null,
  is_synthetic: true,
  created_at: now,
  updated_at: now,
};
const context: WorkspaceContext = {
  api: new ApiClient("SYNTHETIC-UPLOAD-STATUS-TEST-NOT-LIVE"),
  access: {
    access_mode: "scoped",
    authenticated: true,
    operator_alias: "Fictional upload operator",
    identity_kind: "operator_grant",
    permissions: ["read", "write"],
    institution_ids: [id(1)],
    global_admin: false,
    execution: {
      external_processing_allowed: false,
      research_enabled: false,
      claude_enabled: false,
    },
    limitations: [],
  },
  institution: {
    id: id(1),
    name: "Fictional Upload University",
    country: "MY",
    website_url: "https://curriculum.example.invalid",
    source_id: null,
    source_locator: null,
    is_synthetic: true,
    data_quality: "synthetic",
    created_at: now,
    updated_at: now,
  },
  programme: {
    id: id(2),
    institution_id: id(1),
    name: "Fictional Upload Computing",
    programme_code: null,
    academic_year: null,
    active_revision_id: revision.id,
    active_revision: revision,
    level: "undergraduate",
    discipline_key: "computing",
    canonical_url: "https://curriculum.example.invalid/programme",
    source_id: null,
    source_locator: null,
    is_synthetic: true,
    data_quality: "synthetic",
    created_at: now,
    updated_at: now,
  },
  revisionId: revision.id,
  revisions: [revision],
  setRevision: vi.fn(),
};

function uploadJob(
  overrides: Partial<Model<"JobRead">> = {},
): Model<"JobRead"> {
  return {
    id: id(4),
    institution_id: id(1),
    programme_revision_id: null,
    kind: "CURRICULUM_PDF_UPLOAD",
    status: "SUCCEEDED",
    is_synthetic: true,
    created_at: now,
    started_at: now,
    completed_at: now,
    error: null,
    result: {
      entries: [
        { programme_id: context.programme.id, revision_id: revision.id },
      ],
    },
    ...overrides,
  };
}
function coursePage(items: Course[]) {
  return {
    items,
    total: items.length,
    limit: 100,
    offset: 0,
    programme_revision_id: revision.id,
  };
}
function UploadLocation() {
  return <p data-testid="upload-location">{useLocation().search}</p>;
}
function renderUpload(job?: Model<"JobRead">, workspace = context, query = "") {
  return render(
    <MemoryRouter
      initialEntries={[
        `/programmes/${context.programme.id}/upload${job ? `?job=${job.id}` : ""}${query}`,
      ]}
    >
      <Routes>
        <Route
          path="/programmes/:programmeId"
          element={
            <Workspace.Provider value={workspace}>
              <Outlet />
            </Workspace.Provider>
          }
        >
          <Route
            path="upload"
            element={
              <>
                <UploadPage />
                <UploadLocation />
              </>
            }
          />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("curriculum upload status and review readiness", () => {
  it("follows the extracted revision and clears previous assessment selections", async () => {
    const job = uploadJob();
    const course = {
      ...courseFixture.response.items[0],
      id: id(5),
      programme_revision_id: revision.id,
    } as Course;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        Promise.resolve(
          json(input.includes("/catalogue/jobs/") ? job : coursePage([course])),
        ),
      ),
    );
    renderUpload(
      job,
      context,
      `&revision=${id(99)}&analysis=${id(98)}&career=${id(97)}&plan=${id(96)}`,
    );
    await waitFor(() =>
      expect(screen.getByTestId("upload-location")).toHaveTextContent(
        `revision=${revision.id}`,
      ),
    );
    const query = screen.getByTestId("upload-location").textContent || "";
    expect(query).not.toContain("analysis=");
    expect(query).not.toContain("career=");
    expect(query).not.toContain("plan=");
    expect(
      await screen.findByRole("button", { name: "Generate results" }),
    ).toBeEnabled();
  });
  it("accepts only matching authorised HTTPS origins, including equivalent www hosts", () => {
    expect(
      validatePdfOrigin(
        "https://www.curriculum.example.invalid/programme",
        "https://curriculum.example.invalid",
        "https://curriculum.example.invalid:443/original.pdf",
      ),
    ).toBeNull();
    for (const sourceUrl of [
      "https://other.example.invalid/original.pdf",
      "http://curriculum.example.invalid/original.pdf",
      "https://curriculum.example.invalid:444/original.pdf",
      "https://operator@curriculum.example.invalid/original.pdf",
      "not-a-url",
    ])
      expect(
        validatePdfOrigin(
          context.programme.canonical_url,
          context.institution.website_url,
          sourceUrl,
        ),
      ).toMatch(/authorised HTTPS host/);
  });

  it("blocks a real university origin in a fictional institution without changing either record", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const workspace: WorkspaceContext = {
      ...context,
      programme: {
        ...context.programme,
        canonical_url: "https://www.xmu.edu.my/synthetic-origin-mismatch",
      },
    };
    renderUpload(undefined, workspace);
    expect(
      screen.getByText(
        /select the correct authorised institution and programme/,
      ),
    ).toBeVisible();
    fireEvent.drop(screen.getByRole("region", { name: "PDF file drop zone" }), {
      dataTransfer: {
        files: [
          new File(["%PDF-1.7\nfictional input"], "fictional.pdf", {
            type: "application/pdf",
          }),
        ],
      },
    });
    const submit = screen.getByRole("button", {
      name: "Upload and queue extraction",
    });
    expect(submit).toBeDisabled();
    fireEvent.submit(submit.closest("form")!);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "they are not changed automatically",
    );
    expect(workspace.programme.canonical_url).toBe(
      "https://www.xmu.edu.my/synthetic-origin-mismatch",
    );
    expect(workspace.institution.website_url).toBe(
      context.institution.website_url,
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("explicitly identifies an empty selection without submitting anything", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    renderUpload();
    expect(screen.getByText(/No PDF selected/)).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Upload and queue extraction" }),
    ).toBeDisabled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("keeps prolonged queued work distinct from a known worker outage", async () => {
    const job = uploadJob({
      status: "QUEUED",
      started_at: null,
      completed_at: null,
      created_at: new Date(Date.now() - 120_000).toISOString(),
      result: {},
    });
    const fetch = vi.fn(() => Promise.resolve(json(job)));
    vi.stubGlobal("fetch", fetch);
    renderUpload(job);
    expect(
      await screen.findByText(
        /No completion has been reported after more than a minute/,
      ),
    ).toHaveTextContent("Worker availability is unknown");
    expect(
      screen.getByText(/Queue status does not prove worker availability/),
    ).toBeVisible();
    expect(
      screen.queryByText(/Revision ready for review/),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/worker (is stopped|is offline)/i),
    ).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("waits for the committed course read before presenting a revision for review", async () => {
    const job = uploadJob();
    let resolveCourses!: (response: Response) => void;
    const courses = new Promise<Response>((resolve) => {
      resolveCourses = resolve;
    });
    const fetch = vi.fn((input: string) =>
      input.includes("/catalogue/jobs/") ? Promise.resolve(json(job)) : courses,
    );
    vi.stubGlobal("fetch", fetch);
    renderUpload(job);
    await screen.findByText(/The worker has finished/);
    expect(
      screen.queryByText("Revision ready for review"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Inspect this extracted revision" }),
    ).not.toBeInTheDocument();
    const course: Course = {
      ...courseFixture.response.items[0],
      id: id(5),
      programme_revision_id: revision.id,
      extraction_status: "NEEDS_REVIEW",
    } as Course;
    await act(async () => resolveCourses(json(coursePage([course]))));
    expect(await screen.findByText("Revision ready for review")).toBeVisible();
    expect(
      screen.getByText("1 course records loaded from this revision."),
    ).toBeVisible();
    expect(
      screen.getByText(/Manual review required for 1 of 1 course records/),
    ).toBeVisible();
    expect(
      screen.getByText(/Extraction flags are not academic verification/),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Inspect this extracted revision" }),
    ).toHaveAttribute(
      "href",
      `/programmes/${context.programme.id}/courses?revision=${revision.id}`,
    );
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("identifies historical imports without implying the active curriculum changed", async () => {
    const job = uploadJob({
      kind: "CURRICULUM_IMPORT",
      result: {
        entries: [
          {
            programme_id: context.programme.id,
            revision_id: revision.id,
            active: false,
          },
        ],
      },
    });
    const course = {
      ...courseFixture.response.items[0],
      id: id(5),
      programme_revision_id: revision.id,
    } as Course;
    const fetch = vi.fn((input: string) =>
      Promise.resolve(
        json(input.includes("/catalogue/jobs/") ? job : coursePage([course])),
      ),
    );
    vi.stubGlobal("fetch", fetch);
    renderUpload(job);
    expect(
      await screen.findByText(/saved as a historical revision/),
    ).toHaveTextContent("The active curriculum was not replaced");
    expect(await screen.findByText("Revision ready for review")).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Inspect this extracted revision" }),
    ).toHaveAttribute(
      "href",
      `/programmes/${context.programme.id}/courses?revision=${revision.id}`,
    );
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("offers source-grounded manual review after unsupported PDF extraction", async () => {
    const job = uploadJob({
      status: "FAILED",
      error:
        "pdf_regions_required: Catalogue acquisition failed; use reviewed structured JSON",
    });
    const fetch = vi.fn(() => Promise.resolve(json(job)));
    vi.stubGlobal("fetch", fetch);
    renderUpload(job);
    expect(
      await screen.findByText(/Manual PDF review is required/),
    ).toHaveTextContent("this does not mean the PDF has no courses");
    expect(
      screen.queryByText("Revision ready for review"),
    ).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Use reviewed input" }),
    );
    expect(
      screen.getByRole("heading", {
        name: "Import a reviewed course inventory",
      }),
    ).toBeVisible();
    expect(
      screen.getByText(/This creates an immutable revision/),
    ).toBeVisible();
    expect(
      screen.getByRole("checkbox", { name: /I reviewed these course titles/ }),
    ).not.toBeChecked();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("does not infer an imported inventory from a successful job without its programme revision", async () => {
    const job = uploadJob({ result: {} });
    const fetch = vi.fn(() => Promise.resolve(json(job)));
    vi.stubGlobal("fetch", fetch);
    renderUpload(job);
    expect(
      await screen.findByText(/did not report a revision for this programme/),
    ).toHaveTextContent("No imported course inventory is assumed");
    expect(
      screen.queryByText("Revision ready for review"),
    ).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("does not mark an empty committed revision ready", async () => {
    const job = uploadJob();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        Promise.resolve(
          json(input.includes("/catalogue/jobs/") ? job : coursePage([])),
        ),
      ),
    );
    renderUpload(job);
    expect(
      await screen.findByRole("heading", {
        name: "No course records in this revision",
      }),
    ).toBeVisible();
    expect(
      screen.queryByText("Revision ready for review"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Inspect this extracted revision" }),
    ).not.toBeInTheDocument();
  });

  it("withholds readiness and shows a safe error when the committed course read fails", async () => {
    const job = uploadJob();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        Promise.resolve(
          input.includes("/catalogue/jobs/")
            ? json(job)
            : json(
                { internal_database_details: "PRIVATE-DATABASE-DETAILS" },
                503,
              ),
        ),
      ),
    );
    renderUpload(job);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The backend database is unavailable",
    );
    expect(
      screen.queryByText(/PRIVATE-DATABASE-DETAILS/),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Revision ready for review"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Inspect this extracted revision" }),
    ).not.toBeInTheDocument();
  });
});
