import { defineConfig } from "@playwright/test";

const origin = new URL(
  process.env.SHIFTOS_FRONTEND_ORIGIN || "http://127.0.0.1:5178",
);
if (
  origin.protocol !== "http:" ||
  !["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname) ||
  origin.username ||
  origin.password ||
  origin.pathname !== "/"
)
  throw new Error(
    "Browser acceptance requires an explicit loopback preview origin.",
  );
if (!process.env.SHIFTOS_PREVIEW_AUTH)
  throw new Error(
    "Configure the private local preview credential file through SHIFTOS_PREVIEW_AUTH.",
  );

export default defineConfig({
  testDir: "./tests/browser",
  outputDir: "./test-results/browser-artifacts",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [["line"]],
  use: {
    baseURL: origin.origin,
    viewport: { width: 1440, height: 900 },
    browserName: "chromium",
    trace: "off",
    screenshot: "off",
    video: "off",
    actionTimeout: 15_000,
  },
});
