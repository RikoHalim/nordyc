import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "../src/App";
import { ApiClient } from "../src/api/client";

vi.mock("../src/pages/Library", () => ({
  default: () => <h1>Direct local demonstration</h1>,
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

it("opens the enabled local demonstration without a credential form", async () => {
  vi.stubEnv("DEV", true);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response('{"enabled":true}', {
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
  vi.spyOn(ApiClient.prototype, "get").mockResolvedValue({
    permissions: ["read", "write"],
    institution_ids: ["00000000-0000-4000-8000-000000000001"],
  });
  render(<App />);
  expect(await screen.findByText("Direct local demonstration")).toBeVisible();
  expect(screen.queryByLabelText("Scoped operator credential")).toBeNull();
});

it("retains protected sign-in when automatic local access is disabled", async () => {
  vi.stubEnv("DEV", true);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("", { status: 404 })),
  );
  const api = vi.spyOn(ApiClient.prototype, "get");
  render(<App />);
  expect(
    await screen.findByLabelText("Scoped operator credential"),
  ).toBeVisible();
  expect(api).not.toHaveBeenCalled();
});

it("does not attempt automatic access in a production build", () => {
  vi.stubEnv("DEV", false);
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  expect(screen.getByLabelText("Scoped operator credential")).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
});

it("opens an explicitly enabled public read-only workspace using server access context", async () => {
  vi.stubEnv("DEV", false);
  vi.stubEnv("VITE_PUBLIC_DEMO", "true");
  const fetch = vi.fn().mockResolvedValue(new Response('{"enabled":true}'));
  vi.stubGlobal("fetch", fetch);
  const api = vi.spyOn(ApiClient.prototype, "get").mockResolvedValue({
    permissions: ["read"],
    institution_ids: ["00000000-0000-4000-8000-000000000001"],
  });
  render(<App />);
  expect(await screen.findByText("Direct local demonstration")).toBeVisible();
  expect(fetch).toHaveBeenCalledWith("/__public_demo", expect.any(Object));
  expect(api).toHaveBeenCalledWith("/api/v1/access-context", "AccessContext");
  expect(screen.queryByLabelText("Scoped operator credential")).toBeNull();
});

it("retains sign-in when the public marker is disabled", async () => {
  vi.stubEnv("DEV", false);
  vi.stubEnv("VITE_PUBLIC_DEMO", "true");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response('{"enabled":false}')),
  );
  const api = vi.spyOn(ApiClient.prototype, "get");
  render(<App />);
  expect(
    await screen.findByLabelText("Scoped operator credential"),
  ).toBeVisible();
  expect(api).not.toHaveBeenCalled();
});

it("does not open a public workspace when the server denies access", async () => {
  vi.stubEnv("DEV", false);
  vi.stubEnv("VITE_PUBLIC_DEMO", "true");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response('{"enabled":true}')),
  );
  vi.spyOn(ApiClient.prototype, "get").mockRejectedValue(
    new Error("Forbidden"),
  );
  render(<App />);
  expect(
    await screen.findByLabelText("Scoped operator credential"),
  ).toBeVisible();
  expect(screen.queryByText("Direct local demonstration")).toBeNull();
});
