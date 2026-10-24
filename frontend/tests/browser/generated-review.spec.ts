import { test, expect } from "@playwright/test";
import type {
  CareerResult,
  CareerRun,
  PlanResult,
  PlanRun,
} from "../../src/api/types";
import {
  actualGet,
  emptyStorage,
  localNetworkOnly,
  login,
  navigate,
} from "./helpers";
import { syntheticPdf } from "./synthetic-inputs";

test("actual uploaded PDF generates offline course findings, evidence-review recommendation and action plan", async ({
  page,
}, testInfo) => {
  test.setTimeout(180_000);
  await localNetworkOnly(page);
  // Isolate this write acceptance from the read-only judge institution scopes.
  await login(page, "admin");
  const get = (path: string) => actualGet(page, path, "admin");
  const stamp = Date.now();
  const name = `Synthetic Generated Review ${stamp}`;
  const website = `https://synthetic-generated-${stamp}.example.invalid`;
  const canonicalUrl = new URL(`/synthetic-generated-review-${stamp}`, website)
    .href;
  await page.getByRole("button", { name: /New curriculum/ }).click();
  const modal = page.getByRole("dialog", { name: "New curriculum" });
  await modal
    .getByText("Create an authorised institution record", { exact: true })
    .click();
  await modal
    .getByLabel("Institution name", { exact: true })
    .fill(`Fictional Generated Review University ${stamp}`);
  await modal
    .getByLabel("Official institution website", { exact: true })
    .fill(website);
  await modal
    .getByLabel("This is a fictional demonstration institution", {
      exact: true,
    })
    .check();
  const institutionResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/v1/institutions" &&
      response.request().method() === "POST",
  );
  await modal
    .getByRole("button", { name: "Create institution record", exact: true })
    .click();
  const createdInstitution = await institutionResponse;
  expect(createdInstitution.status()).toBe(201);
  const institution = await createdInstitution.json();
  expect(institution.is_synthetic).toBe(true);
  await modal
    .getByRole("combobox", { name: "Institution", exact: true })
    .selectOption(institution.id);
  await modal.getByLabel("Programme name", { exact: true }).fill(name);
  await modal.getByLabel(/Official programme URL/).fill(canonicalUrl);
  await modal.getByLabel(/Discipline/).fill("computing");
  const createdResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/institutions/${institution.id}/programmes`) &&
      response.request().method() === "POST",
  );
  await modal
    .getByRole("button", { name: "Create curriculum workspace" })
    .click();
  const created = await createdResponse;
  expect(created.status()).toBe(201);
  const programme = await created.json();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: /Bring your curriculum into focus/,
    }),
  ).toBeVisible();

  const chooserReady = page.waitForEvent("filechooser");
  await page.getByLabel("Curriculum PDF", { exact: true }).click();
  await (
    await chooserReady
  ).setFiles({
    name: "generated-review.synthetic.pdf",
    mimeType: "application/pdf",
    buffer: syntheticPdf(),
  });
  await expect(page.getByRole("status")).toContainText(
    "generated-review.synthetic.pdf selected",
  );
  // A native file picker returns window focus. This must preserve the attached
  // file and upload form while the real programme-context refresh completes.
  const inputBeforeFocus = await page
    .getByLabel("Curriculum PDF", { exact: true })
    .elementHandle();
  const refreshed = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/v1/programmes/${programme.id}`) &&
      response.request().method() === "GET",
  );
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  expect((await refreshed).status()).toBe(200);
  await expect(page.getByRole("status")).toContainText(
    "generated-review.synthetic.pdf selected",
  );
  expect(
    await inputBeforeFocus!.evaluate(
      (element) =>
        element.isConnected &&
        (element as HTMLInputElement).files?.[0]?.name ===
          "generated-review.synthetic.pdf",
    ),
  ).toBe(true);
  const uploadedResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/programmes/${programme.id}/curriculum-pdf`) &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Upload and queue extraction" })
    .click();
  const uploaded = await uploadedResponse;
  expect(uploaded.status()).toBe(202);
  const pdfJob = await uploaded.json();
  await expect(
    page.getByRole("heading", {
      name: "Revision ready for review",
      exact: true,
    }),
  ).toBeVisible({ timeout: 75_000 });
  const extractedJob = await get(`/api/v1/catalogue/jobs/${pdfJob.id}`);
  expect(extractedJob.status).toBe(200);
  expect(["SUCCEEDED", "PARTIAL"]).toContain(extractedJob.body.status);
  const imported = extractedJob.body.result.entries.find(
    (row: { programme_id: string }) => row.programme_id === programme.id,
  );
  expect(imported).toBeDefined();
  const revisionId = imported.revision_id as string;
  expect(imported.active).toBe(true);
  const courses = await get(
    `/api/v1/programmes/${programme.id}/revisions/${revisionId}/courses?limit=100&offset=0`,
  );
  expect(courses.status).toBe(200);
  expect(courses.body.items).toHaveLength(3);

  const submissions: { path: string; body: Record<string, unknown> }[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (
      request.method() === "POST" &&
      /\/(analyses|career-analyses|action-plans)$/.test(path)
    )
      submissions.push({ path, body: request.postDataJSON() });
  });
  await page
    .getByRole("button", { name: "Generate results", exact: true })
    .click();
  await expect(page).toHaveURL(
    new RegExp(`/programmes/${programme.id}/recommendations\\?`),
    { timeout: 100_000 },
  );
  await expect(
    page.getByRole("heading", { level: 1, name: /Academic recommendations/i }),
  ).toBeVisible();
  const selection = new URL(page.url()).searchParams;
  expect(selection.get("revision")).toBe(revisionId);
  const analysisId = selection.get("analysis");
  const careerId = selection.get("career");
  const planId = selection.get("plan");
  expect(analysisId).toBeTruthy();
  expect(careerId).toBeTruthy();
  expect(planId).toBeTruthy();
  expect(submissions).toHaveLength(3);
  expect(submissions.every((row) => row.body.mode === "offline")).toBe(true);
  expect(submissions[0].body).toMatchObject({
    revision_id: revisionId,
    research: false,
  });
  expect(submissions[1].body).toMatchObject({ revision_id: revisionId });
  expect(submissions[1].body).not.toHaveProperty("mappings");
  expect(submissions[1].body).not.toHaveProperty("assertions");
  expect(submissions[2].body).toMatchObject({ phase4_analysis_id: analysisId });

  const analysis = await get(`/api/v1/analyses/${analysisId}`);
  const findings = await get(
    `/api/v1/analyses/${analysisId}/courses?limit=100&offset=0`,
  );
  expect(analysis.status).toBe(200);
  expect(["SUCCEEDED", "PARTIAL"]).toContain(analysis.body.status);
  expect(analysis.body.mode).toBe("offline");
  expect(analysis.body.programme_revision_id).toBe(revisionId);
  expect(findings.status).toBe(200);
  expect(findings.body.items).toHaveLength(courses.body.items.length);
  expect(
    new Set(
      findings.body.items.map((row: { course_id: string }) => row.course_id),
    ),
  ).toEqual(new Set(courses.body.items.map((row: { id: string }) => row.id)));
  expect(
    findings.body.items.every(
      (row: { result_json: { needs_syllabus_confirmation: boolean } }) =>
        row.result_json.needs_syllabus_confirmation,
    ),
  ).toBe(true);

  const storedCareer = await get(`/api/v1/career-analyses/${careerId}`);
  const storedPlan = await get(`/api/v1/action-plans/${planId}`);
  expect(storedCareer.status).toBe(200);
  expect(storedPlan.status).toBe(200);
  const career = storedCareer.body as CareerRun;
  const plan = storedPlan.body as PlanRun;
  const careerResult = career.result_json as CareerResult;
  const planResult = plan.result_json as PlanResult;
  expect(career.status).toBe("PARTIAL");
  expect(career.mode).toBe("offline");
  expect(career.programme_id).toBe(programme.id);
  expect(career.programme_revision_id).toBe(revisionId);
  expect(career.needs_evidence_revalidation).toBe(false);
  expect(careerResult.status).toBe("insufficient_evidence");
  expect(careerResult.occupations || []).toHaveLength(0);
  expect(careerResult.recommendations?.length).toBeGreaterThan(0);
  expect(
    careerResult.recommendations?.every(
      (row) =>
        row.category === "request_review" &&
        row.evidence_sufficiency === "insufficient_evidence" &&
        row.automatic_curriculum_change === false,
    ),
  ).toBe(true);
  expect(plan.status).toBe("PARTIAL");
  expect(plan.mode).toBe("offline");
  expect(plan.programme_revision_id).toBe(revisionId);
  expect(plan.career_run_id).toBe(career.id);
  expect(plan.career_fingerprint).toBe(career.fingerprint);
  expect(plan.needs_evidence_revalidation).toBe(false);
  expect(planResult.inputs.phase4_analysis_id).toBe(analysisId);
  expect(
    planResult.pathways?.some(
      (row) =>
        row.pathway_type === "evidence_review" &&
        row.steps.some((step) => step.step_type === "evidence_review"),
    ),
  ).toBe(true);
  expect(planResult.review?.academic_approval).toBe(false);
  expect(planResult.review?.implementation_authorised).toBe(false);
  await expect(
    page
      .getByText(careerResult.recommendations![0].action, { exact: true })
      .first(),
  ).toBeVisible();
  await navigate(page, "Academic pathways", /academic pathways/i);
  await expect(page.locator(".pathway-timeline")).not.toHaveCount(0);
  await navigate(page, "Academic Action Plan", /academic action plan/i);
  await expect(page.locator(".report-section")).toHaveCount(8);
  await emptyStorage(page);
  await testInfo.attach("actual-generated-review-scope", {
    body: JSON.stringify({
      programme_id: programme.id,
      revision_id: revisionId,
      pdf_job_id: pdfJob.id,
      analysis_id: analysisId,
      career_id: careerId,
      plan_id: planId,
      courses: courses.body.items.length,
      persisted_findings: findings.body.items.length,
      career_status: career.status,
      plan_status: plan.status,
      recommendation_categories: careerResult.recommendations?.map(
        (row) => row.category,
      ),
      evidence_review_pathways: planResult.pathways?.filter(
        (row) => row.pathway_type === "evidence_review",
      ).length,
      focus_preserved_file_selection: true,
      offline_job_submissions: submissions.length,
      live_requests: 0,
      scope:
        "Actual fictional PDF import and protected offline worker results; evidence-review proposals, no invented occupation mapping, academic approval or paid model call.",
    }),
    contentType: "application/json",
  });
});
