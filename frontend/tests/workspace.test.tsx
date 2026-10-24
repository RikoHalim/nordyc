import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import courseFixture from "../../examples/api/courses.synthetic.json";
import { ApiClient } from "../src/api/client";
import type {
  AccessContext,
  Course,
  Evidence,
  Institution,
  Model,
  Programme,
} from "../src/api/types";
import { SessionContext } from "../src/app/session";
import { Workspace, type WorkspaceContext } from "../src/app/workspace";
import {
  EvidenceProvider,
  safeUrl,
  useEvidence,
} from "../src/components/EvidenceDrawer";
import Library from "../src/pages/Library";
import Courses from "../src/pages/Courses";
import UploadPage, { validatePdf } from "../src/pages/Upload";

const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const now = "2026-10-25T00:00:00Z";
const credential = "SYNTHETIC-WORKSPACE-TEST-CREDENTIAL-NOT-LIVE";
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const page = <T,>(items: T[]) => ({
  items,
  total: items.length,
  limit: 100,
  offset: 0,
});
const institution: Institution = {
  id: id(1),
  name: "Fictional Test University",
  country: "MY",
  website_url: "https://curriculum.example.invalid",
  source_id: null,
  source_locator: null,
  is_synthetic: true,
  data_quality: "synthetic",
  created_at: now,
  updated_at: now,
};
const revision: Model<"ProgrammeRevisionRead"> = {
  id: id(3),
  programme_id: id(2),
  version_label: "Fictional revision",
  effective_date: null,
  is_synthetic: true,
  created_at: now,
  updated_at: now,
};
const programme: Programme = {
  id: id(2),
  institution_id: institution.id,
  name: "Fictional Computing",
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
};
function access(
  permissions: AccessContext["permissions"] = ["read"],
): AccessContext {
  return {
    access_mode: "scoped",
    authenticated: true,
    operator_alias: "Fictional operator grant",
    identity_kind: "operator_grant",
    permissions,
    institution_ids: [institution.id],
    global_admin: permissions.includes("admin"),
    execution: {
      external_processing_allowed: false,
      research_enabled: false,
      claude_enabled: false,
    },
    limitations: [],
  };
}
function workspace(
  api: ApiClient,
  permissions: AccessContext["permissions"] = ["read"],
): WorkspaceContext {
  return {
    api,
    access: access(permissions),
    programme,
    institution,
    revisionId: revision.id,
    revisions: [revision],
    setRevision: vi.fn(),
  };
}
function renderWorkspace(
  children: ReactNode,
  api: ApiClient,
  permissions: AccessContext["permissions"] = ["read"],
  entry = `/programmes/${programme.id}/courses`,
) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Workspace.Provider value={workspace(api, permissions)}>
        {children}
      </Workspace.Provider>
    </MemoryRouter>,
  );
}
function course(n: number, year: number | null): Course {
  return {
    ...courseFixture.response.items[0],
    id: id(n),
    programme_revision_id: revision.id,
    course_name:
      year === null
        ? "Fictional Unknown-Year Course"
        : "Fictional Recorded-Year Course",
    year,
    semester: null,
    course_type: "UNKNOWN",
    detailed_syllabus_available: false,
    evidence_level: "title_only",
  } as Course;
}
function evidence(n: number): Evidence {
  return {
    id: `synthetic-evidence-${n}`,
    kind: "skill",
    record_id: id(1000 + n),
    version_id: id(4),
    evidence_reference_id: id(2000 + n),
    source_id: id(5),
    evidence_class: "synthetic_demo",
    scope: "occupation_benchmark",
    publisher: "Fictional Benchmark Publisher",
    title: `Fictional source ${n}`,
    locator: `synthetic:row:${n}`,
    review_status: "reviewed",
    is_synthetic: true,
    source_url: "https://source.example.invalid/fictional",
    rights: {
      internal_analysis_allowed: true,
      external_model_allowed: false,
      excerpt_output_allowed: true,
      basis: "Explicitly synthetic fixture",
    },
    internal_eligible: true,
    model_eligible: false,
    historical_context_only: false,
    identity_reviewed: false,
    date_precision: "unknown",
    excerpt: `PRIVATE-PERMITTED-FICTIONAL-EXCERPT-${n}`,
    limitations: ["Fictional test source, not a university teaching claim."],
  };
}
function EvidenceOpener({
  path,
  referenceId,
}: {
  path: string;
  referenceId: string;
}) {
  const { openEvidence } = useEvidence();
  return (
    <button onClick={() => openEvidence(path, referenceId)}>
      Inspect source evidence
    </button>
  );
}

const textDescriptor = Object.getOwnPropertyDescriptor(Blob.prototype, "text");
const modalDescriptor = Object.getOwnPropertyDescriptor(
  HTMLDialogElement.prototype,
  "showModal",
);
const closeDescriptor = Object.getOwnPropertyDescriptor(
  HTMLDialogElement.prototype,
  "close",
);
beforeAll(() => {
  if (!modalDescriptor)
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
      configurable: true,
      value() {},
    });
  if (!closeDescriptor)
    Object.defineProperty(HTMLDialogElement.prototype, "close", {
      configurable: true,
      value() {},
    });
  // jsdom lacks Blob.text in some versions; FileReader supplies the same browser API semantics.
  if (!Blob.prototype.text)
    Object.defineProperty(Blob.prototype, "text", {
      configurable: true,
      value(this: Blob) {
        return new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = () => reject(reader.error);
          reader.readAsText(this);
        });
      },
    });
});
afterAll(() => {
  if (!textDescriptor)
    delete (Blob.prototype as unknown as { text?: unknown }).text;
  if (!modalDescriptor)
    delete (HTMLDialogElement.prototype as unknown as { showModal?: unknown })
      .showModal;
  if (!closeDescriptor)
    delete (HTMLDialogElement.prototype as unknown as { close?: unknown })
      .close;
});
beforeEach(() => {
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  vi.spyOn(HTMLDialogElement.prototype, "showModal").mockImplementation(
    function (this: HTMLDialogElement) {
      this.open = true;
    },
  );
  vi.spyOn(HTMLDialogElement.prototype, "close").mockImplementation(function (
    this: HTMLDialogElement,
  ) {
    if (this.open) {
      this.open = false;
      this.dispatchEvent(new Event("close"));
    }
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("curriculum library and creation", () => {
  function library(
    permissions: AccessContext["permissions"],
    createResponse?: () => Response,
  ) {
    const business = {
      ...programme,
      id: id(6),
      name: "Fictional Accounting",
      discipline_key: "accounting",
    };
    const fetch = vi.fn((input: string, init?: RequestInit) => {
      if (init?.method === "POST")
        return Promise.resolve(createResponse?.() || json(programme, 201));
      const url = new URL(input, window.location.origin);
      if (url.pathname === "/api/v1/programmes")
        return Promise.resolve(json(page([programme, business])));
      if (url.pathname === "/api/v1/institutions")
        return Promise.resolve(json(page([institution])));
      return Promise.resolve(
        json({
          programme_id: url.pathname.includes(business.id)
            ? business.id
            : programme.id,
          programme_revision_id: revision.id,
          course_count: 2,
          verified_title_count: 0,
          needs_review_count: 2,
          title_only_count: 2,
          is_synthetic: true,
          graduation_curriculum_complete: false,
          metadata: {},
        }),
      );
    });
    vi.stubGlobal("fetch", fetch);
    const api = new ApiClient(credential);
    render(
      <SessionContext.Provider
        value={{ api, access: access(permissions), disconnect: vi.fn() }}
      >
        <MemoryRouter>
          <Routes>
            <Route path="/" element={<Library />} />
            <Route
              path="/programmes/:programmeId/upload"
              element={<h1>Authorised created workspace upload</h1>}
            />
          </Routes>
        </MemoryRouter>
      </SessionContext.Provider>,
    );
    return fetch;
  }

  it("searches actual programme records and keeps new curriculum disabled for read-only grants", async () => {
    const fetch = library(["read"]);
    await screen.findByRole("heading", { name: programme.name });
    expect(
      screen.getByRole("button", { name: /New curriculum/ }),
    ).toBeDisabled();
    expect(
      screen.queryByText("Create an authorised institution record"),
    ).not.toBeInTheDocument();
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Find a curriculum" }),
      "Accounting",
    );
    expect(
      screen.getByRole("heading", { name: "Fictional Accounting" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: programme.name }),
    ).not.toBeInTheDocument();
    expect(fetch.mock.calls.every(([, init]) => init?.method !== "POST")).toBe(
      true,
    );
  });

  it("submits a real authorised creation payload and navigates only after backend acceptance", async () => {
    const fetch = library(["read", "write"]);
    await userEvent.click(
      await screen.findByRole("button", { name: /New curriculum/ }),
    );
    await userEvent.type(
      screen.getByLabelText("Programme name"),
      "New Fictional Curriculum",
    );
    await userEvent.type(
      screen.getByLabelText(/Official programme URL/),
      programme.canonical_url!,
    );
    expect(
      screen.queryByText("Create an authorised institution record"),
    ).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /Create curriculum workspace/ }),
    );
    await screen.findByRole("heading", {
      name: "Authorised created workspace upload",
    });
    const submitted = fetch.mock.calls.find(
      ([, init]) => init?.method === "POST",
    );
    expect(submitted?.[0]).toBe(
      `/api/v1/institutions/${institution.id}/programmes`,
    );
    expect(JSON.parse(String(submitted?.[1]?.body))).toEqual({
      name: "New Fictional Curriculum",
      canonical_url: programme.canonical_url,
      discipline_key: null,
      is_synthetic: true,
    });
  });

  it("keeps a rejected creation in the form without presenting successful navigation", async () => {
    library(["read", "write"], () =>
      json(
        {
          error: {
            code: "CONFLICT",
            message: "Private backend details",
            details: [],
          },
        },
        409,
      ),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: /New curriculum/ }),
    );
    await userEvent.type(
      screen.getByLabelText("Programme name"),
      "Fictional rejected input",
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Create curriculum workspace/ }),
    );
    await screen.findByRole("alert");
    expect(
      screen.queryByRole("heading", {
        name: "Authorised created workspace upload",
      }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Programme name")).toHaveValue(
      "Fictional rejected input",
    );
    expect(
      screen.queryByText("Private backend details"),
    ).not.toBeInTheDocument();
  });
});

describe("recorded course inventory", () => {
  it("groups absent years explicitly without assigning Year 0 or invented outcomes", async () => {
    const records = [course(20, null), course(21, 2)];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        Promise.resolve(
          json(
            input.includes("/courses?")
              ? { ...page(records), programme_revision_id: revision.id }
              : page([]),
          ),
        ),
      ),
    );
    renderWorkspace(<Courses />, new ApiClient(credential));
    await screen.findByRole("heading", {
      name: "Fictional Unknown-Year Course",
    });
    expect(
      screen.queryByRole("button", { name: /Queue offline/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Upload & review/ }),
    ).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /Year not recorded/ }),
    );
    expect(
      screen.getByRole("heading", { name: "Courses without a recorded year" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Fictional Recorded-Year Course" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Year 0")).not.toBeInTheDocument();
    expect(screen.getByText("Needs syllabus confirmation")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("heading", { name: "Fictional Unknown-Year Course" }),
    );
    expect(
      screen.getByText(/Learning outcomes cannot be inferred/),
    ).toBeInTheDocument();
  });

  it("queues only the explicit offline revision and displays pending worker state", async () => {
    let run: Model<"AnalysisRead"> | undefined;
    const fetch = vi.fn((input: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        run = {
          id: id(25),
          institution_id: institution.id,
          programme_id: programme.id,
          programme_revision_id: revision.id,
          job_id: id(26),
          status: "QUEUED",
          mode: "offline",
          created_at: now,
          updated_at: now,
          is_synthetic: true,
          started_at: null,
          completed_at: null,
          error: null,
          request_json: {},
          manifest_json: {},
          summary_json: {},
          research_json: {},
          fingerprint: null,
          model_name: null,
          prompt_version: null,
          schema_version: null,
          needs_evidence_revalidation: true,
        };
        return Promise.resolve(json(run, 202));
      }
      if (input.includes(`/analyses/${id(25)}`))
        return Promise.resolve(json(run));
      if (input.includes("/analyses?"))
        return Promise.resolve(json(page(run ? [run] : [])));
      return Promise.resolve(
        json({
          ...page([course(20, null)]),
          programme_revision_id: revision.id,
        }),
      );
    });
    vi.stubGlobal("fetch", fetch);
    renderWorkspace(<Courses />, new ApiClient(credential), ["read", "write"]);
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Queue offline course screening",
      }),
    );
    await screen.findByText(/Awaiting the actual worker result/);
    const submitted = fetch.mock.calls.filter(
      ([, init]) => init?.method === "POST",
    );
    expect(submitted).toHaveLength(1);
    expect(JSON.parse(String(submitted[0][1]?.body))).toMatchObject({
      revision_id: revision.id,
      mode: "offline",
      research: false,
      idempotency_key: expect.stringMatching(/^ui-screening-/),
    });
    expect(
      screen.queryByText(
        "Evidence needs revalidation. Source-derived findings are withheld.",
      ),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Preliminary course findings"),
    ).not.toBeInTheDocument();
  });
});

describe("attributed PDF and reviewed input", () => {
  it("rejects wrong, empty and oversized file metadata without allocating a large document", () => {
    expect(
      validatePdf(new File(["text"], "notes.txt", { type: "text/plain" })),
    ).toMatch(/Choose a PDF/);
    expect(
      validatePdf(new File([], "empty.pdf", { type: "application/pdf" })),
    ).toMatch(/contain data/);
    const oversized = new File(["%PDF-"], "large.pdf", {
      type: "application/pdf",
    });
    Object.defineProperty(oversized, "size", { value: 20_000_001 });
    expect(validatePdf(oversized)).toMatch(/20 MB/);
  });

  it("does not expose upload controls to a read-only operator", () => {
    renderWorkspace(<UploadPage />, new ApiClient(credential));
    expect(
      screen.getByRole("heading", { name: "Write permission is required" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Curriculum PDF")).not.toBeInTheDocument();
  });

  it("checks PDF signature before any upload request", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    renderWorkspace(<UploadPage />, new ApiClient(credential), [
      "read",
      "write",
    ]);
    await userEvent.upload(
      screen.getByLabelText("Curriculum PDF"),
      new File(["not a PDF"], "fake.pdf", { type: "application/pdf" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Upload and queue extraction/ }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "supported PDF signature",
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("submits actual PDF bytes and shows only the accepted queued job", async () => {
    const job: Model<"JobRead"> = {
      id: id(30),
      institution_id: institution.id,
      programme_revision_id: null,
      kind: "CURRICULUM_PDF_UPLOAD",
      status: "QUEUED",
      is_synthetic: true,
      created_at: now,
      started_at: null,
      completed_at: null,
      error: null,
      result: {},
    };
    const fetch = vi.fn((_input: string, init?: RequestInit) =>
      Promise.resolve(json(job, init?.method === "POST" ? 202 : 200)),
    );
    vi.stubGlobal("fetch", fetch);
    renderWorkspace(<UploadPage />, new ApiClient(credential), [
      "read",
      "write",
    ]);
    const file = new File(["%PDF-1.7\nfictional input"], "fictional.pdf", {
      type: "application/pdf",
    });
    await userEvent.upload(screen.getByLabelText("Curriculum PDF"), file);
    await userEvent.type(
      screen.getByLabelText(/Original document URL/),
      "https://curriculum.example.invalid/original.pdf",
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Upload and queue extraction/ }),
    );
    await screen.findByText(/Queue status does not prove worker availability/);
    const submitted = fetch.mock.calls.find(
      ([, init]) => init?.method === "POST",
    );
    expect(submitted?.[0]).toContain(
      "source_url=https%3A%2F%2Fcurriculum.example.invalid",
    );
    expect(submitted?.[1]?.body).toBe(file);
    expect(
      screen.queryByRole("table", {
        name: "Committed courses from this import",
      }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/worker has finished/i)).not.toBeInTheDocument();
  });

  it("requires explicit reviewed-input confirmation and resets it after editing", async () => {
    renderWorkspace(<UploadPage />, new ApiClient(credential), [
      "read",
      "write",
    ]);
    await userEvent.click(
      screen.getByRole("button", { name: "Reviewed input" }),
    );
    const manifest = screen.getByLabelText("Programme import JSON");
    fireEvent.change(manifest, {
      target: { value: '{"name":"Fictional draft"}' },
    });
    const queue = screen.getByRole("button", {
      name: /Queue reviewed curriculum import/,
    });
    expect(queue).toBeDisabled();
    await userEvent.click(
      screen.getByRole("checkbox", { name: /I reviewed these course titles/ }),
    );
    expect(queue).toBeEnabled();
    fireEvent.change(manifest, {
      target: { value: '{"name":"Changed fictional draft"}' },
    });
    expect(queue).toBeDisabled();
    expect(
      screen.getByRole("checkbox", { name: /I reviewed these course titles/ }),
    ).not.toBeChecked();
  });

  it("submits the exact reviewed source inventory as a new queued import", async () => {
    const job: Model<"JobRead"> = {
      id: id(31),
      institution_id: institution.id,
      programme_revision_id: null,
      kind: "CURRICULUM_IMPORT",
      status: "QUEUED",
      is_synthetic: true,
      created_at: now,
      started_at: null,
      completed_at: null,
      error: null,
      result: {},
    };
    const fetch = vi.fn((_input: string, init?: RequestInit) =>
      Promise.resolve(json(job, init?.method === "POST" ? 202 : 200)),
    );
    vi.stubGlobal("fetch", fetch);
    renderWorkspace(<UploadPage />, new ApiClient(credential), [
      "read",
      "write",
    ]);
    await userEvent.click(
      screen.getByRole("button", { name: "Reviewed input" }),
    );
    const source = {
      course_name: "Fictional reviewed title",
      source_locator: "synthetic:page:1:line:1",
      source_excerpt: "Fictional reviewed title",
    };
    const manifest = {
      name: programme.name,
      canonical_url: programme.canonical_url,
      source_url: "https://curriculum.example.invalid/original.pdf",
      source_locator: "Synthetic reviewed course list",
      retrieved_at: now,
      courses: [source],
      reviewed: false,
    };
    fireEvent.change(screen.getByLabelText("Programme import JSON"), {
      target: { value: JSON.stringify(manifest) },
    });
    await userEvent.click(
      screen.getByRole("checkbox", { name: /I reviewed these course titles/ }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Queue reviewed curriculum import/ }),
    );
    await screen.findByText(/Queue status does not prove worker availability/);
    const submitted = fetch.mock.calls.filter(
      ([, init]) => init?.method === "POST",
    );
    expect(submitted).toHaveLength(1);
    expect(submitted[0][0]).toBe(`/api/v1/programmes/${programme.id}/imports`);
    expect(JSON.parse(String(submitted[0][1]?.body))).toEqual({
      ...manifest,
      reviewed: true,
      is_synthetic: true,
      idempotency_key: expect.stringMatching(/^ui-import-/),
    });
    expect(
      screen.queryByRole("table", {
        name: "Committed courses from this import",
      }),
    ).not.toBeInTheDocument();
  });
});

describe("current source evidence drawer", () => {
  it.each([
    "javascript:alert(1)",
    "data:text/html,private",
    "https://user:password@source.example.invalid",
  ])("refuses unsafe original link %s", (url) => {
    expect(safeUrl(url)).toBeNull();
  });

  it("retrieves a valid citation beyond the first page and safely closes the dialog", async () => {
    const rows = Array.from({ length: 101 }, (_, n) => evidence(n + 1));
    const fetch = vi.fn((input: string) => {
      const url = new URL(input, window.location.origin),
        offset = Number(url.searchParams.get("offset"));
      return Promise.resolve(
        json({
          ...page(rows.slice(offset, offset + 100)),
          total: rows.length,
          offset,
          status: "SUCCEEDED",
          error: null,
          needs_evidence_revalidation: false,
          evidence_access_limitations: [],
        }),
      );
    });
    vi.stubGlobal("fetch", fetch);
    render(
      <EvidenceProvider api={new ApiClient(credential)}>
        <EvidenceOpener
          path={`/api/v1/career-analyses/${id(10)}/evidence`}
          referenceId={rows[100].id}
        />
      </EvidenceProvider>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Inspect source evidence" }),
    );
    const dialog = screen.getByRole("dialog", {
      name: "Evidence & limitations",
    });
    expect(
      await within(dialog).findByText(rows[100].excerpt!),
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(
      within(dialog).getByRole("link", { name: /Open original source/ }),
    ).toHaveAttribute("href", rows[100].source_url);
    expect(
      within(dialog).queryByText(rows[0].excerpt!),
    ).not.toBeInTheDocument();
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Close evidence" }),
    );
    expect(dialog).not.toHaveAttribute("open");
    expect(screen.queryByText(rows[100].excerpt!)).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Inspect source evidence" }),
    );
    await within(dialog).findByText(rows[100].excerpt!);
    fireEvent(dialog, new Event("cancel", { bubbles: true, cancelable: true }));
    await waitFor(() => expect(dialog).not.toHaveAttribute("open"));
  });

  it.each(["revoked", "read-error"])(
    "removes previously permitted excerpts after %s revalidation",
    async (mode) => {
      let revalidation = false;
      const row = evidence(1);
      vi.stubGlobal(
        "fetch",
        vi.fn(() => {
          if (revalidation && mode === "read-error")
            return Promise.resolve(
              json(
                {
                  error: {
                    code: "DATABASE_UNAVAILABLE",
                    message: "PRIVATE-BACKEND-ERROR",
                    details: [],
                  },
                },
                503,
              ),
            );
          return Promise.resolve(
            json({
              ...page(revalidation ? [] : [row]),
              status: "SUCCEEDED",
              error: null,
              needs_evidence_revalidation: revalidation,
              evidence_access_limitations: revalidation
                ? ["Source rights were withdrawn"]
                : [],
            }),
          );
        }),
      );
      render(
        <EvidenceProvider api={new ApiClient(credential)}>
          <EvidenceOpener
            path={`/api/v1/career-analyses/${id(10)}/evidence`}
            referenceId={row.id}
          />
        </EvidenceProvider>,
      );
      await userEvent.click(
        screen.getByRole("button", { name: "Inspect source evidence" }),
      );
      await screen.findByText(row.excerpt!);
      revalidation = true;
      act(() => window.dispatchEvent(new Event("focus")));
      expect(screen.queryByText(row.excerpt!)).not.toBeInTheDocument();
      await screen.findByRole("heading", {
        name: "Evidence unavailable or withheld",
      });
      expect(
        screen.queryByRole("link", { name: /Open original source/ }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("PRIVATE-BACKEND-ERROR"),
      ).not.toBeInTheDocument();
    },
  );
});
