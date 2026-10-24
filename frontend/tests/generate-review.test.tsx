import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { ApiClient, ApiError } from "../src/api/client";
import { Workspace, type WorkspaceContext } from "../src/app/workspace";
import GenerateReview from "../src/components/GenerateReview";

const { prepare } = vi.hoisted(() => ({ prepare: vi.fn() }));
vi.mock("../src/lib/prepare-review", () => ({ prepareReview: prepare }));
const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const api = new ApiClient("SYNTHETIC-UI-REVIEW-TEST-NOT-A-CREDENTIAL");
const coverage = {
  programme_id: id(1),
  programme_revision_id: id(2),
  course_count: 36,
};
function Destination() {
  return <p>Saved recommendations{useLocation().search}</p>;
}
function mount(permissions = ["read", "write"]) {
  const context = {
    api,
    access: { permissions },
    programme: { id: id(1) },
    revisionId: id(2),
  } as WorkspaceContext;
  return render(
    <Workspace.Provider value={context}>
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<GenerateReview courseCount={36} />} />
          <Route
            path="/programmes/:id/recommendations"
            element={<Destination />}
          />
        </Routes>
      </MemoryRouter>
    </Workspace.Provider>,
  );
}
beforeEach(() => {
  prepare.mockReset();
  vi.spyOn(api, "get").mockResolvedValue(coverage);
});
describe("visible upload-to-results entry", () => {
  it("requires write permission and never starts assessment just by rendering", () => {
    mount(["read"]);
    expect(
      screen.queryByRole("button", { name: "Generate results" }),
    ).not.toBeInTheDocument();
    expect(prepare).not.toHaveBeenCalled();
    expect(api.get).not.toHaveBeenCalled();
  });
  it("starts an explicit review and opens exact saved recommendation records", async () => {
    prepare.mockResolvedValue({
      analysisId: id(3),
      careerId: id(4),
      planId: id(5),
      recommendationCount: 1,
    });
    mount();
    expect(prepare).not.toHaveBeenCalled();
    await userEvent.click(
      screen.getByRole("button", { name: "Generate results" }),
    );
    const destination = await screen.findByText(/Saved recommendations/);
    expect(destination).toHaveTextContent(`revision=${id(2)}`);
    expect(destination).toHaveTextContent(`analysis=${id(3)}`);
    expect(destination).toHaveTextContent(`career=${id(4)}`);
    expect(destination).toHaveTextContent(`plan=${id(5)}`);
    expect(prepare).toHaveBeenCalledOnce();
    expect(prepare.mock.calls[0].slice(1, 3)).toEqual([id(1), id(2)]);
  });
  it("does not submit assessments when the revision has no courses", async () => {
    vi.mocked(api.get).mockResolvedValue({ ...coverage, course_count: 0 });
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: "Generate results" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "no extracted courses",
    );
    expect(prepare).not.toHaveBeenCalled();
  });
  it("rejects coverage for another revision rather than showing its output", async () => {
    vi.mocked(api.get).mockResolvedValue({
      ...coverage,
      programme_revision_id: id(99),
    });
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: "Generate results" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "unexpected response",
    );
    expect(prepare).not.toHaveBeenCalled();
  });
  it("checks existing progress with the same idempotency key after an unknown outcome", async () => {
    prepare.mockRejectedValue(new ApiError("TIMEOUT"));
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: "Generate results" }),
    );
    await screen.findByRole("alert");
    await userEvent.click(
      screen.getByRole("button", { name: "Check progress" }),
    );
    await waitFor(() => expect(prepare).toHaveBeenCalledTimes(2));
    expect(prepare.mock.calls[0][3].key).toBe(prepare.mock.calls[1][3].key);
  });
  it("aborts polling when leaving the workspace", async () => {
    prepare.mockImplementation(() => new Promise(() => {}));
    const view = mount();
    await userEvent.click(
      screen.getByRole("button", { name: "Generate results" }),
    );
    await waitFor(() => expect(prepare).toHaveBeenCalledOnce());
    const signal = prepare.mock.calls[0][3].signal as AbortSignal;
    view.unmount();
    expect(signal.aborted).toBe(true);
  });
});
