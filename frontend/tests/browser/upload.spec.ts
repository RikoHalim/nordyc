import { test, expect } from "@playwright/test";
import {
  actualGet,
  localNetworkOnly,
  login,
  programme as existingProgramme,
} from "./helpers";
import { reviewedManifest, syntheticPdf } from "./synthetic-inputs";

test("actual programme creation, PDF worker extraction, reviewed correction and offline screening", async ({
  page,
}, testInfo) => {
  test.setTimeout(180_000);
  await localNetworkOnly(page);
  await login(page);
  const institution = await actualGet(
    page,
    `/api/v1/institutions/${existingProgramme.institution_id}`,
  );
  expect(institution.status).toBe(200);
  expect(institution.body.is_synthetic).toBe(true);
  const stamp = Date.now();
  const name = `Bachelor of Synthetic Browser Review ${stamp}`;
  const canonicalUrl = new URL(
    `/synthetic-browser-review-${stamp}`,
    institution.body.website_url,
  ).href;
  const manifest = reviewedManifest(name, canonicalUrl);
  const template = {
    institution_id: existingProgramme.institution_id,
    canonical_url: canonicalUrl,
    discipline_key: "computing",
  };
  await page.getByRole("button", { name: /New curriculum/ }).click();
  const modal = page.getByRole("dialog", { name: "New curriculum" });
  await expect(modal).toBeVisible();
  await modal
    .getByRole("combobox", { name: "Institution", exact: true })
    .selectOption(template.institution_id);
  await modal.getByLabel("Programme name", { exact: true }).fill(name);
  await modal.getByLabel(/Official programme URL/).fill(template.canonical_url);
  await modal.getByLabel(/Discipline/).fill(template.discipline_key);
  const createdResponse = page.waitForResponse(
    (response) =>
      response
        .url()
        .includes(`/institutions/${template.institution_id}/programmes`) &&
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
  const chooser = await chooserReady;
  await chooser.setFiles({
    name: "curriculum-upload.synthetic.pdf",
    mimeType: "application/pdf",
    buffer: syntheticPdf(),
  });
  await expect(page.getByRole("status")).toContainText(
    "curriculum-upload.synthetic.pdf selected",
  );
  // Exercise the fallback used when a host's native picker opens a PDF viewer.
  // File selection/drop must only attach bytes; the explicit submit does the POST.
  const attachedUrl = page.url();
  const droppedFiles = await page.evaluateHandle((bytes) => {
    const transfer = new DataTransfer();
    transfer.items.add(
      new File([new Uint8Array(bytes)], "curriculum-drop.synthetic.pdf", {
        type: "application/pdf",
      }),
    );
    return transfer;
  }, Array.from(syntheticPdf()));
  await page
    .getByRole("region", { name: "PDF file drop zone" })
    .dispatchEvent("drop", { dataTransfer: droppedFiles });
  await droppedFiles.dispose();
  await expect(page.getByRole("status")).toContainText(
    "curriculum-drop.synthetic.pdf selected",
  );
  expect(page.url()).toBe(attachedUrl);
  const uploadResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/programmes/${programme.id}/curriculum-pdf`) &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Upload and queue extraction" })
    .click();
  const uploaded = await uploadResponse;
  expect(uploaded.status()).toBe(202);
  const job = await uploaded.json();
  await expect(
    page.getByRole("heading", {
      name: "Review extracted courses",
      exact: true,
    }),
  ).toBeVisible({ timeout: 75_000 });
  const persistedJob = await actualGet(
    page,
    `/api/v1/catalogue/jobs/${job.id}`,
  );
  expect(persistedJob.status).toBe(200);
  expect(["SUCCEEDED", "PARTIAL"]).toContain(persistedJob.body.status);
  await expect(page.locator(".data-table tbody tr")).not.toHaveCount(0);
  await page.screenshot({
    path: "test-results/phase8-upload-extracted.png",
    fullPage: true,
  });

  await page
    .getByRole("button", { name: "Reviewed input", exact: true })
    .click();
  manifest.name = name;
  manifest.canonical_url = programme.canonical_url;
  // This fictional transcription is reviewed now, after the PDF import. Dating
  // it at test setup would correctly preserve it as an older historical revision.
  manifest.retrieved_at = new Date().toISOString();
  await page
    .getByLabel("Programme import JSON", { exact: true })
    .fill(JSON.stringify(manifest));
  await page
    .getByLabel(
      "I reviewed these course titles and source excerpts against the original document.",
    )
    .check();
  const correctionResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/programmes/${programme.id}/imports`) &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Queue reviewed curriculum import" })
    .click();
  const corrected = await correctionResponse;
  expect(corrected.status()).toBe(202);
  const correctedJob = await corrected.json();
  await expect
    .poll(
      async () =>
        (await actualGet(page, `/api/v1/catalogue/jobs/${correctedJob.id}`))
          .body.status,
      { timeout: 75_000 },
    )
    .toMatch(/^(SUCCEEDED|PARTIAL)$/);
  const reviewedJob = await actualGet(
    page,
    `/api/v1/catalogue/jobs/${correctedJob.id}`,
  );
  const reviewedEntry = reviewedJob.body.result.entries.find(
    (entry: { programme_id: string }) => entry.programme_id === programme.id,
  );
  expect(reviewedEntry.active).toBe(true);
  const currentProgramme = await actualGet(
    page,
    `/api/v1/programmes/${programme.id}`,
  );
  expect(currentProgramme.body.active_revision_id).toBe(
    reviewedEntry.revision_id,
  );
  await expect(
    page.getByRole("link", { name: "Inspect this extracted revision" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Inspect this extracted revision" })
    .click();
  await expect(page.locator(".course-card")).toHaveCount(
    manifest.courses.length,
  );
  const screeningResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/programmes/${programme.id}/analyses`) &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Queue offline course screening" })
    .click();
  const screening = await screeningResponse;
  expect(screening.status()).toBe(202);
  const run = await screening.json();
  await expect
    .poll(
      async () =>
        (await actualGet(page, `/api/v1/analyses/${run.id}`)).body.status,
      { timeout: 75_000 },
    )
    .toMatch(/^(SUCCEEDED|PARTIAL)$/);
  const findings = await actualGet(
    page,
    `/api/v1/analyses/${run.id}/courses?limit=100&offset=0`,
  );
  expect(findings.body.items).toHaveLength(manifest.courses.length);
  expect(
    findings.body.items.every(
      (row: { result_json: { needs_syllabus_confirmation: boolean } }) =>
        row.result_json.needs_syllabus_confirmation,
    ),
  ).toBeTruthy();
  await testInfo.attach("actual-upload-scope", {
    body: JSON.stringify({
      programme_id: programme.id,
      pdf_job_id: job.id,
      correction_job_id: correctedJob.id,
      offline_analysis_id: run.id,
      courses: findings.body.items.length,
      live_requests: 0,
    }),
    contentType: "application/json",
  });
});
