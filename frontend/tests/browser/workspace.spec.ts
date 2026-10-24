import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
import {
  actualGet,
  emptyStorage,
  localNetworkOnly,
  login,
  navigate,
  noOverflow,
  observeErrors,
  openProgramme,
  programme,
} from "./helpers";

test.beforeEach(async ({ page }) => {
  await localNetworkOnly(page);
});

test("actual PostgreSQL workspace navigation, evidence, review and desktop captures", async ({
  page,
}, testInfo) => {
  test.setTimeout(180_000);
  const errors = observeErrors(page);
  const network = { responses: 0, httpErrors: 0, failed: 0, cancelled: 0 };
  page.on("response", (response) => {
    network.responses += 1;
    if (response.status() >= 400) network.httpErrors += 1;
  });
  page.on("requestfailed", (request) => {
    if (request.failure()?.errorText.includes("ERR_ABORTED"))
      network.cancelled += 1;
    else network.failed += 1;
  });
  const initialConnectionStarted = Date.now();
  await login(page);
  await expect(
    page.getByRole("heading", { name: "Your curricula." }),
  ).toBeVisible();
  const firstConnectedLibraryMs = Date.now() - initialConnectionStarted;
  await page
    .getByRole("link", { name: "Skip to content", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
  await emptyStorage(page);
  await page.screenshot({
    path: "test-results/phase8-library-desktop.png",
    fullPage: true,
  });
  await noOverflow(page);
  await openProgramme(page);
  await navigate(page, "Industry outlook", /industry outlook/i);
  await expect(
    page.getByRole("heading", { name: /Understand the context/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/phase8-industry-desktop.png",
    fullPage: true,
  });
  await navigate(page, "Course intelligence", /learning journey/i);
  await expect(page.locator(".course-card")).toHaveCount(6);
  await page.screenshot({
    path: "test-results/phase8-journey-desktop.png",
    fullPage: true,
  });
  await page.locator(".course-card summary").first().click();
  await expect(
    page
      .getByText(/Learning outcomes cannot be inferred from this title/)
      .first(),
  ).toBeVisible();
  await navigate(page, "Career alignment", /future career alignment/i);
  await expect(
    page.getByText("Synthetic Data Systems Analyst", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/phase8-career-desktop.png",
    fullPage: true,
  });
  await navigate(page, "Competency analysis", /competency coverage/i);
  await page.getByLabel("Competency evidence").selectOption("unknown");
  await expect(page.locator(".data-table tbody tr")).toHaveCount(1);
  await expect(
    page.getByText("Synthetic governance review", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Competency evidence").selectOption("all");
  await page.screenshot({
    path: "test-results/phase8-competencies-desktop.png",
    fullPage: true,
  });
  const citation = page.locator("main .citation").first();
  await citation.click();
  const dialog = page.getByRole("dialog", { name: "Evidence & limitations" });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(".evidence-record").first()).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Close evidence" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(citation).toBeFocused();
  await navigate(page, "Academic recommendations", /academic recommendations/i);
  await expect(page.getByText("Suggested next step").first()).toBeVisible();
  await navigate(page, "Academic pathways", /academic pathways/i);
  await expect(page.locator(".pathway-timeline")).toHaveCount(4);
  await page.screenshot({
    path: "test-results/phase8-pathways-desktop.png",
    fullPage: true,
  });
  await navigate(page, "Future scenarios", /future scenarios/i);
  await expect(page.locator(".scenario-grid > section")).toHaveCount(2);
  await page.screenshot({
    path: "test-results/phase8-scenarios-desktop.png",
    fullPage: true,
  });
  await navigate(page, "SDG alignment", /sdg contribution/i);
  await expect(
    page.getByRole("heading", { name: /Target 4.4/ }).first(),
  ).toBeVisible();
  await navigate(page, "Academic Action Plan", /academic action plan/i);
  await expect(page.locator(".report-section")).toHaveCount(8);
  await page.screenshot({
    path: "test-results/phase8-plan-desktop.png",
    fullPage: true,
  });
  const reason = `Explicit fictional browser acceptance review ${Date.now()}; no curriculum implementation authorised.`;
  await page.getByLabel("Review decision").selectOption("under_review");
  await page.getByLabel("Reason", { exact: true }).fill(reason);
  const response = page.waitForResponse(
    (value) =>
      value.url().includes(`/action-plans/${programme.plan_id}/reviews`) &&
      value.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Record review decision" }).click();
  const written = await response;
  expect(written.status()).toBe(201);
  expect(written.request().postDataJSON()).toMatchObject({
    decision: "under_review",
    reason,
    expected_plan_fingerprint: expect.stringMatching(/^[a-f\d]{64}$/),
  });
  const persisted = await actualGet(
    page,
    `/api/v1/action-plans/${programme.plan_id}/reviews?limit=100&offset=0`,
  );
  expect(persisted.status).toBe(200);
  expect(
    persisted.body.items.some(
      (row: { reason: string; decision: string }) =>
        row.reason === reason && row.decision === "under_review",
    ),
  ).toBeTruthy();
  await expect(page.locator(".report-section")).toHaveCount(8);
  await navigate(page, "Review history", /review history/i);
  for (let pageIndex = 0; pageIndex < 10; pageIndex += 1) {
    if (await page.getByText(reason, { exact: true }).count()) break;
    const older = page.getByRole("button", {
      name: "Older reviews",
      exact: true,
    });
    if (await older.isDisabled()) break;
    await older.click();
    await expect(
      page.getByText("Loading version-bound review history", { exact: true }),
    ).not.toBeVisible();
  }
  await expect(page.getByText(reason, { exact: true })).toBeVisible();
  await navigate(page, "Evidence & sources", /evidence & sources/i);
  await expect(page.locator("main .detail-list > .card").first()).toBeVisible();
  const freshEvidence = page.waitForResponse(
    (response) =>
      response.url().includes("/evidence") &&
      response.request().method() === "GET",
  );
  await page.locator("main .citation").first().click();
  expect((await freshEvidence).status()).toBe(200);
  await expect(
    page
      .getByRole("dialog", { name: "Evidence & limitations" })
      .locator(".evidence-record")
      .first(),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await navigate(page, "Academic Action Plan", /academic action plan/i);
  await expect(page.locator(".report-section")).toHaveCount(8);
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  await testInfo.attach("axe-desktop", {
    body: JSON.stringify(accessibility.violations),
    contentType: "application/json",
  });
  expect(
    accessibility.violations
      .filter((row) => ["critical", "serious"].includes(row.impact || ""))
      .map((row) => ({
        id: row.id,
        impact: row.impact,
        nodes: row.nodes.map((node) => ({
          target: node.target,
          failure: node.failureSummary,
        })),
      })),
  ).toEqual([]);
  await emptyStorage(page);
  await page
    .getByRole("link", { name: "Workspace access", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Disconnect workspace", exact: true })
    .click();
  await expect(page.getByLabel("Scoped operator credential")).toHaveValue("");
  await emptyStorage(page);
  expect(errors).toEqual([]);
  await writeFile(
    "test-results/phase8-desktop-observations.json",
    JSON.stringify(
      {
        scope:
          "Single controlled local synthetic browser session; not a performance benchmark or comprehensive accessibility certification.",
        first_connected_library_ms: firstConnectedLibraryMs,
        network,
        severe_console_or_page_errors: errors.length,
        axe: accessibility.violations.map((row) => ({
          id: row.id,
          impact: row.impact,
          node_count: row.nodes.length,
        })),
      },
      null,
      2,
    ),
  );
  await testInfo.attach("acceptance-scope", {
    body: "Actual local PostgreSQL-backed API and worker; fictional source data; no live model/search requests. Review persisted through protected API.",
    contentType: "text/plain",
  });
});

test("actual responsive library, industry and journey remain usable on mobile and tablet", async ({
  page,
}, testInfo) => {
  test.setTimeout(120_000);
  const errors = observeErrors(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await expect(
    page.getByRole("heading", { name: "Your curricula." }),
  ).toBeVisible();
  await noOverflow(page);
  await page.screenshot({
    path: "test-results/phase8-library-mobile.png",
    fullPage: true,
  });
  await openProgramme(page);
  const menu = page.getByRole("button", { name: "Open programme menu" });
  await menu.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("dialog", { name: "Programme navigation" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Close navigation" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await navigate(page, "Industry outlook", /industry outlook/i);
  await expect(
    page.getByRole("heading", { name: /Understand the context/ }),
  ).toBeVisible();
  await noOverflow(page);
  await page.screenshot({
    path: "test-results/phase8-industry-mobile.png",
    fullPage: true,
  });
  await navigate(page, "Course intelligence", /learning journey/i);
  await expect(page.locator(".course-card")).toHaveCount(6);
  await noOverflow(page);
  await page.screenshot({
    path: "test-results/phase8-journey-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 820, height: 1180 });
  await navigate(page, "Academic Action Plan", /academic action plan/i);
  await expect(page.locator(".report-section")).toHaveCount(8);
  await noOverflow(page);
  await page.screenshot({
    path: "test-results/phase8-plan-tablet.png",
    fullPage: true,
  });
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  await testInfo.attach("axe-tablet", {
    body: JSON.stringify(accessibility.violations),
    contentType: "application/json",
  });
  expect(
    accessibility.violations
      .filter((row) => ["critical", "serious"].includes(row.impact || ""))
      .map((row) => ({
        id: row.id,
        impact: row.impact,
        nodes: row.nodes.map((node) => ({
          target: node.target,
          failure: node.failureSummary,
        })),
      })),
  ).toEqual([]);
  expect(errors).toEqual([]);
  await writeFile(
    "test-results/phase8-responsive-observations.json",
    JSON.stringify(
      {
        scope:
          "Actual 390px mobile and820px tablet synthetic session; Axe sampled the completed tablet plan only.",
        page_overflow: 0,
        severe_console_or_page_errors: errors.length,
        axe: accessibility.violations.map((row) => ({
          id: row.id,
          impact: row.impact,
          node_count: row.nodes.length,
        })),
      },
      null,
      2,
    ),
  );
});
