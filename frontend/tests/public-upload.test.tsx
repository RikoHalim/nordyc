import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ApiClient } from "../src/api/client";
import type { AccessContext } from "../src/api/types";
import { SessionContext } from "../src/app/session";
import PublicUploadEntry from "../src/components/PublicUploadEntry";
import {
  createPublicUploadWorkspace,
  publicWorkspaceAccess,
} from "../src/lib/public-upload-session";

const institutionId = "00000000-0000-4000-8000-000000000001";
const programmeId = "00000000-0000-4000-8000-000000000002";
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const input = {
  institution_name: "Fictional Public Test University",
  institution_url: "https://university.example.invalid",
  programme_name: "Fictional programme",
  programme_url: "https://university.example.invalid/programme",
  permitted_public_document: true as const,
};
const access = {
  permissions: ["read", "write"],
  institution_ids: [institutionId],
} as AccessContext;

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value(this: HTMLDialogElement) {
      this.open = true;
    },
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

function show(enabled = true, refreshed = access) {
  const refreshAccess = vi.fn().mockResolvedValue(refreshed);
  render(
    <SessionContext.Provider
      value={{
        api: new ApiClient(""),
        access,
        disconnect: vi.fn(),
        publicUploadsEnabled: enabled,
        refreshAccess,
      }}
    >
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<PublicUploadEntry />} />
          <Route
            path={`/programmes/${programmeId}/upload`}
            element={<h1>Private session PDF upload</h1>}
          />
        </Routes>
      </MemoryRouter>
    </SessionContext.Provider>,
  );
  return refreshAccess;
}
async function fill() {
  await userEvent.click(
    screen.getByRole("button", { name: "Try your own PDF" }),
  );
  await userEvent.type(
    screen.getByLabelText("Programme name"),
    input.programme_name,
  );
  await userEvent.type(
    screen.getByLabelText("Institution name"),
    input.institution_name,
  );
  await userEvent.type(
    screen.getByLabelText("Official programme page"),
    input.programme_url,
  );
}

describe("public upload workspace entry", () => {
  it("does not offer public bootstrap in ordinary operator mode", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    show(false);
    expect(
      screen.queryByRole("button", { name: "Try your own PDF" }),
    ).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("requires consent and obtains only a private session before opening the existing upload page", async () => {
    const fetch = vi.fn().mockResolvedValue(
      json({
        programme_id: programmeId,
        institution_id: institutionId,
        expires_in_seconds: 3600,
      }),
    );
    const storage = vi.spyOn(Storage.prototype, "setItem");
    vi.stubGlobal("fetch", fetch);
    const refresh = show();
    await fill();
    const submit = screen.getByRole("button", {
      name: "Continue to PDF upload",
    });
    expect(submit).toBeDisabled();
    expect(fetch).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(submit);
    expect(
      await screen.findByRole("heading", {
        name: "Private session PDF upload",
      }),
    ).toBeVisible();
    expect(fetch).toHaveBeenCalledOnce();
    const [path, options] = fetch.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/__public_upload_session");
    expect(options).toMatchObject({
      method: "POST",
      credentials: "same-origin",
      redirect: "error",
      mode: "same-origin",
      cache: "no-store",
    });
    expect(options.headers).not.toHaveProperty("Authorization");
    expect(JSON.parse(String(options.body))).toEqual(input);
    expect(refresh).toHaveBeenCalledOnce();
    expect(storage).not.toHaveBeenCalled();
    expect(window.location.href).not.toMatch(/token|credential/);
  });

  it("does not navigate if refreshed access grants review or administration", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          json({ programme_id: programmeId, institution_id: institutionId }),
        ),
    );
    show(true, { ...access, permissions: ["read", "write", "review"] });
    await fill();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(
      screen.getByRole("button", { name: "Continue to PDF upload" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "could not be opened",
    );
    expect(screen.queryByText("Private session PDF upload")).toBeNull();
  });

  it("rejects a non-HTTPS programme page before contacting the server", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    show();
    await fill();
    fireEvent.change(screen.getByLabelText("Official programme page"), {
      target: { value: "http://university.example.invalid/programme" },
    });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(
      screen.getByRole("button", { name: "Continue to PDF upload" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "official HTTPS programme page",
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("explains a server request limit without retrying or exposing its response", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(json({ secret: "PRIVATE-ERROR-CANARY" }, 429));
    vi.stubGlobal("fetch", fetch);
    show();
    await fill();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(
      screen.getByRole("button", { name: "Continue to PDF upload" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "temporary upload limit",
    );
    expect(screen.queryByText("PRIVATE-ERROR-CANARY")).toBeNull();
    expect(fetch).toHaveBeenCalledOnce();
  });
});

describe("public upload bootstrap transport", () => {
  it("keeps the saved example read-only while allowing writes only in the session institution", () => {
    const ownAndExample = {
      ...access,
      institution_ids: [institutionId, programmeId],
    };
    expect(
      publicWorkspaceAccess(ownAndExample, true, institutionId, programmeId)
        .permissions,
    ).toEqual(["read"]);
    expect(
      publicWorkspaceAccess(ownAndExample, true, institutionId, institutionId)
        .permissions,
    ).toEqual(["read", "write"]);
    expect(
      publicWorkspaceAccess(ownAndExample, true, undefined, institutionId)
        .permissions,
    ).toEqual(["read"]);
    expect(
      publicWorkspaceAccess(ownAndExample, false, undefined, institutionId),
    ).toBe(ownAndExample);
  });
  it("never grants public review/admin controls even if the input context contains them", () => {
    const broad = {
      ...access,
      global_admin: true,
      permissions: [
        "read",
        "write",
        "review",
        "admin",
      ] as AccessContext["permissions"],
    };
    const result = publicWorkspaceAccess(
      broad,
      true,
      institutionId,
      institutionId,
    );
    expect(result.permissions).toEqual(["read", "write"]);
    expect(result.global_admin).toBe(false);
  });
  it.each([
    { programme_id: "https://outside.invalid", institution_id: institutionId },
    { programme_id: programmeId },
    { programme_id: programmeId, institution_id: "unscoped" },
    { token: "PRIVATE-TOKEN-NOT-A-CONTRACT" },
  ])("rejects an invalid workspace response %j", async (response) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(response)));
    await expect(createPublicUploadWorkspace(input)).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
    });
  });
  it("rejects a bounded-body violation before rendering anything", async () => {
    const canceled = vi.fn();
    const body = new ReadableStream<Uint8Array>({
      start: (controller) => controller.enqueue(new Uint8Array(16_385)),
      cancel: canceled,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, {
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(createPublicUploadWorkspace(input)).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
    });
    expect(canceled).toHaveBeenCalledOnce();
  });
  it("bounds timeouts to one request and never retries", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn(
      (_path, options) =>
        new Promise((_resolve, reject) =>
          options.signal.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          ),
        ),
    );
    vi.stubGlobal("fetch", fetch);
    const pending = createPublicUploadWorkspace(input).catch((error) => error);
    await vi.advanceTimersByTimeAsync(30_001);
    expect(await pending).toMatchObject({ code: "TIMEOUT" });
    expect(fetch).toHaveBeenCalledOnce();
  });
  it("honours caller cancellation without retaining the form", async () => {
    const controller = new AbortController();
    const fetch = vi.fn(
      (_path, options) =>
        new Promise((_resolve, reject) =>
          options.signal.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          ),
        ),
    );
    vi.stubGlobal("fetch", fetch);
    const pending = createPublicUploadWorkspace(input, controller.signal).catch(
      (error) => error,
    );
    controller.abort();
    await waitFor(async () => expect((await pending).name).toBe("AbortError"));
    expect(fetch).toHaveBeenCalledOnce();
  });
});
