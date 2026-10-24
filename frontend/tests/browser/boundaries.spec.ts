import { test, expect } from "@playwright/test";
import {
  actualGet,
  deniedReviewStatus,
  emptyStorage,
  localNetworkOnly,
  login,
  navigate,
  openProgramme,
  programme,
} from "./helpers";

test.beforeEach(async ({ page }) => {
  await localNetworkOnly(page);
});

test("actual scoped reader has no write/review controls and foreign institution is withheld", async ({
  page,
}) => {
  await login(page, "reader", `/programmes/${programme.programme_id}/plan`);
  await expect(
    page.getByRole("heading", { level: 1, name: /academic action plan/i }),
  ).toBeVisible();
  await expect(page.locator(".report-section")).toHaveCount(8);
  await expect(
    page.getByRole("button", { name: "Record review decision" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Queue offline career assessment" }),
  ).toHaveCount(0);
  await expect(
    page
      .locator("#programme-navigation")
      .getByRole("link", { name: "Upload & extraction" }),
  ).toHaveCount(0);
  expect(
    await deniedReviewStatus(
      page,
      `/api/v1/action-plans/${programme.plan_id}/reviews`,
    ),
  ).toBe(403);
  const denied = await actualGet(
    page,
    `/api/v1/programmes/${programme.programme_id}`,
    "foreign",
  );
  expect(denied.status).toBe(404);
  await emptyStorage(page);
});

test("mocked source-withdrawal response removes already displayed academic findings", async ({
  page,
}, testInfo) => {
  await login(page);
  await openProgramme(page);
  await navigate(page, "Competency analysis", /competency coverage/i);
  await expect(
    page.getByText("Synthetic governance review", { exact: true }),
  ).toBeVisible();
  const pattern = `**/api/v1/career-analyses/${programme.career_id}`;
  await page.route(pattern, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: {
        ...body,
        needs_evidence_revalidation: true,
        result_json: {
          source_text_withheld: true,
          revalidation_required: true,
        },
        manifest_json: {},
        model_usage_json: {},
      },
    });
  });
  await page
    .getByRole("button", { name: "Refresh records", exact: true })
    .click();
  await expect(
    page.getByText(
      /Source-derived findings, citations and proposals are withheld/,
    ),
  ).toBeVisible();
  await expect(
    page.getByText("Synthetic governance review", { exact: true }),
  ).toHaveCount(0);
  await expect(page.locator("main .citation")).toHaveCount(0);
  await testInfo.attach("fault-scope", {
    body: "Browser-only mocked API withholding fault over a real baseline. No source permission or PostgreSQL record was changed; backend withdrawal is accepted separately by regression tests.",
    contentType: "text/plain",
  });
});

test("mocked pending worker and unavailable API do not become successful results", async ({
  page,
}, testInfo) => {
  await login(page);
  await openProgramme(page);
  const pending = `**/api/v1/analyses/${programme.phase4_id}`;
  await page.route(pending, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: { ...body, status: "RUNNING", completed_at: null },
    });
  });
  await navigate(page, "Course intelligence", /learning journey/i);
  await expect(
    page.getByText(/worker availability is not established by queue status/),
  ).toBeVisible();
  await page.locator(".course-card summary").first().click();
  await expect(
    page
      .getByText("No currently validated finding is displayed for this course.")
      .first(),
  ).toBeVisible();
  await page.unroute(pending);
  const unavailable = `**/api/v1/career-analyses/${programme.career_id}`;
  await page.route(unavailable, (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "DATABASE_UNAVAILABLE",
          message: "Mocked controlled transport fault",
          details: [],
        },
      }),
    }),
  );
  await navigate(page, "Career alignment", /future career alignment/i);
  await expect(
    page.getByText(/backend database is unavailable/i),
  ).toBeVisible();
  await expect(
    page.getByText("Synthetic Data Systems Analyst", { exact: true }),
  ).toHaveCount(0);
  await page.unroute(unavailable);
  await page
    .getByRole("button", { name: "Refresh records", exact: true })
    .click();
  await expect(
    page.getByText("Synthetic Data Systems Analyst", { exact: true }),
  ).toBeVisible();
  await testInfo.attach("fault-scope", {
    body: "Pending-worker and unavailable-API faults were explicitly mocked in the browser. No actual worker outage or database failure is claimed.",
    contentType: "text/plain",
  });
});
