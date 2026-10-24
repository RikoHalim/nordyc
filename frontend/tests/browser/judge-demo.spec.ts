import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import type {
  CareerResult,
  CareerRun,
  PlanResult,
  PlanRun,
} from "../../src/api/types";
import {
  actualGet,
  deniedReviewStatus,
  emptyStorage,
  localNetworkOnly,
  login,
  navigate,
  noOverflow,
  observeErrors,
  receipt,
} from "./helpers";
import { syntheticPdf } from "./synthetic-inputs";

const syntheticLabel = "Demo data — fictional example.";

async function deniedJudgeSubmissions(
  page: Page,
  programmeId: string,
  revisionId: string,
) {
  if (!/^[a-f\d-]{36}$/.test(programmeId) || !/^[a-f\d-]{36}$/.test(revisionId))
    throw new Error(
      "Only known local synthetic programme probes are supported.",
    );
  try {
    const grants = JSON.parse(
      readFileSync(process.env.SHIFTOS_PREVIEW_AUTH!, "utf8"),
    ) as { reader: { token: string } };
    const headers = { Authorization: `Bearer ${grants.reader.token}` };
    const analysis = await page.request.post(
      `/api/v1/programmes/${programmeId}/analyses`,
      {
        headers,
        data: { revision_id: revisionId, mode: "live", research: true },
      },
    );
    const upload = await page.request.post(
      `/api/v1/programmes/${programmeId}/curriculum-pdf`,
      {
        headers: { ...headers, "Content-Type": "application/pdf" },
        data: syntheticPdf(),
      },
    );
    return { analysis: analysis.status(), upload: upload.status() };
  } catch {
    throw new Error(
      "The bounded reader-denial probes failed; credential details are withheld.",
    );
  }
}

async function readOnlyControls(page: Page) {
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Record review decision" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Review decision")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /^Queue offline/ }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /Upload curriculum|Upload & extraction/ }),
  ).toHaveCount(0);
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`actual scoped judge explores populated sample without upload or generation on ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    test.setTimeout(180_000);
    await page.setViewportSize(viewport);
    await localNetworkOnly(page);
    const errors = observeErrors(page);
    const browserMutations: string[] = [];
    const externalRequests: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (
        ["http:", "https:"].includes(url.protocol) &&
        !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
      )
        externalRequests.push(url.origin);
      if (
        url.pathname.startsWith("/api/") &&
        !["GET", "HEAD", "OPTIONS"].includes(request.method())
      )
        browserMutations.push(`${request.method()} ${url.pathname}`);
      expect(url.searchParams.has("token")).toBe(false);
      expect(url.searchParams.has("credential")).toBe(false);
    });

    await login(page, "reader");
    await expect(
      page.getByRole("heading", { name: "Your curricula." }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /New curriculum/ }),
    ).toBeDisabled();
    const access = await actualGet(page, "/api/v1/access-context", "reader");
    expect(access.status).toBe(200);
    expect(access.body.permissions).toEqual(["read"]);
    expect(access.body.global_admin).toBe(false);
    expect([...access.body.institution_ids].sort()).toEqual(
      [...new Set(receipt.programmes.map((row) => row.institution_id))].sort(),
    );
    expect(access.body.execution.research_enabled).toBe(false);
    // This opt-in preview enables only its in-process synthetic mock path.
    // Its execution flag is not live processing consent or a real provider.
    expect(receipt).toMatchObject({
      provider_execution: "mocked",
      live_requests: 0,
      external_http: "blocked",
      persistent_configuration: "not_read_or_modified",
      process_processing_scope:
        "synthetic_mocks_only_with_provider_http_blocked",
    });
    await expect(
      page.getByText(syntheticLabel, { exact: true }).first(),
    ).toBeVisible();
    const sample = page.getByRole("link", {
      name: "Explore Sample Programme",
      exact: true,
    });
    await expect(sample).toBeVisible();
    const href = await sample.getAttribute("href");
    expect(href).toMatch(/^\/programmes\/[a-f\d-]+\/overview\?/);
    const sampleUrl = new URL(href!, "http://127.0.0.1");
    const sampleId = sampleUrl.pathname.split("/")[2];
    const seeded = receipt.programmes.find(
      (row) => row.programme_id === sampleId,
    );
    expect(seeded).toBeDefined();
    expect(sampleUrl.searchParams.get("revision")).toBe(seeded!.revision_id);
    expect(sampleUrl.searchParams.get("career")).toBe(seeded!.career_id);
    expect(sampleUrl.searchParams.get("plan")).toBe(seeded!.plan_id);
    await noOverflow(page);
    await page.screenshot({
      path: `test-results/phase81-judge-library-${viewport.name}.png`,
      fullPage: true,
    });
    await sample.click();
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: /A clearer view of your curriculum/i,
      }),
    ).toBeVisible();
    await expect(
      page
        .getByText("Stored curriculum · human review required.", {
          exact: true,
        })
        .first(),
    ).toBeVisible();
    await readOnlyControls(page);

    // Independently read the actual protected records selected by the entry.
    // No mocked response or newly submitted analysis substitutes for these.
    const storedProgramme = await actualGet(
      page,
      `/api/v1/programmes/${sampleId}`,
      "reader",
    );
    const storedCareer = await actualGet(
      page,
      `/api/v1/career-analyses/${seeded!.career_id}`,
      "reader",
    );
    const storedPlan = await actualGet(
      page,
      `/api/v1/action-plans/${seeded!.plan_id}`,
      "reader",
    );
    expect(storedProgramme.status).toBe(200);
    expect(storedProgramme.body.is_synthetic).toBe(true);
    expect(storedCareer.status).toBe(200);
    expect(storedPlan.status).toBe(200);
    const career = storedCareer.body as CareerRun;
    const plan = storedPlan.body as PlanRun;
    expect(["SUCCEEDED", "PARTIAL"]).toContain(career.status);
    expect(["SUCCEEDED", "PARTIAL"]).toContain(plan.status);
    expect(career.is_synthetic).toBe(true);
    expect(plan.is_synthetic).toBe(true);
    expect(career.programme_revision_id).toBe(seeded!.revision_id);
    expect(plan.programme_revision_id).toBe(seeded!.revision_id);
    expect(plan.career_run_id).toBe(career.id);
    expect(plan.career_fingerprint).toBe(career.fingerprint);
    expect(career.needs_evidence_revalidation).toBe(false);
    expect(plan.needs_evidence_revalidation).toBe(false);
    // The backend contracts and frontend result guards validate these JSON
    // schemas; these assertions demonstrate actual populated acceptance data.
    const careerResult = career.result_json as CareerResult;
    const planResult = plan.result_json as PlanResult;
    const occupations = careerResult.occupations || [];
    const competencies = careerResult.competencies || [];
    const pathways = planResult.pathways || [];
    const sdgAlignments = planResult.sdg_alignments || [];
    expect(occupations.length).toBeGreaterThan(0);
    expect(competencies.length).toBeGreaterThan(0);
    expect(careerResult.recommendations?.length || 0).toBeGreaterThan(0);
    expect(planResult.overview.course_ids).toHaveLength(6);
    expect(pathways.length).toBeGreaterThan(0);
    expect(planResult.scenarios).toHaveLength(2);
    expect(sdgAlignments.length).toBeGreaterThan(0);
    expect(planResult.evidence?.length || 0).toBeGreaterThan(0);

    await navigate(page, "Course intelligence", /learning journey/i);
    await expect(page.locator(".course-card")).toHaveCount(6);
    await page.locator(".course-card summary").first().click();
    await expect(
      page
        .getByText(/Learning outcomes cannot be inferred from this title/)
        .first(),
    ).toBeVisible();
    await readOnlyControls(page);
    await noOverflow(page);
    await navigate(page, "Industry outlook", /industry outlook/i);
    await expect(
      page.getByRole("heading", { name: /Understand the context/ }),
    ).toBeVisible();
    await navigate(page, "Career alignment", /future career alignment/i);
    await expect(
      page.getByRole("heading", {
        name: occupations[0].occupation_name,
        exact: true,
      }),
    ).toBeVisible();
    await navigate(page, "Competency analysis", /competency coverage/i);
    await expect(page.locator(".data-table tbody tr")).toHaveCount(
      competencies.length,
    );
    await page.locator("main .citation").first().click();
    const evidence = page.getByRole("dialog", {
      name: "Evidence & limitations",
    });
    await expect(evidence.locator(".evidence-record").first()).toBeVisible();
    await expect(
      evidence
        .getByText("Demo source — fictional example", { exact: true })
        .first(),
    ).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(evidence).not.toBeVisible();
    await navigate(
      page,
      "Academic recommendations",
      /academic recommendations/i,
    );
    await expect(page.getByText("Suggested next step").first()).toBeVisible();
    await readOnlyControls(page);
    await navigate(page, "Academic pathways", /academic pathways/i);
    await expect(page.locator(".pathway-timeline")).toHaveCount(
      pathways.length,
    );
    await navigate(page, "Future scenarios", /future scenarios/i);
    await expect(page.locator(".scenario-grid > section")).toHaveCount(2);
    await expect(
      page.getByText(
        /These panels are not forecasts or replacement probabilities/,
      ),
    ).toBeVisible();
    await navigate(page, "SDG alignment", /sdg contribution/i);
    const target = sdgAlignments.find((row) => row.target_code);
    expect(target).toBeDefined();
    await expect(
      page
        .getByRole("heading", {
          name: `Target ${target!.target_code}: ${target!.target_title}`,
          exact: true,
        })
        .first(),
    ).toBeVisible();
    await navigate(page, "Academic Action Plan", /academic action plan/i);
    await expect(page.locator(".report-section")).toHaveCount(8);
    await readOnlyControls(page);
    await page.screenshot({
      path: `test-results/phase81-judge-plan-${viewport.name}.png`,
      fullPage: true,
    });
    if (
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      )
    ) {
      const geometry = JSON.stringify(
        await page.evaluate(() =>
          [...document.body.querySelectorAll<HTMLElement>("*")]
            .filter((element) => element.scrollWidth > element.clientWidth + 1)
            .slice(0, 60)
            .map((element) => {
              const style = getComputedStyle(element);
              const box = element.getBoundingClientRect();
              return {
                tag: element.tagName,
                class: element.className,
                scroll: element.scrollWidth,
                client: element.clientWidth,
                right: box.right,
                overflow: style.overflow,
                overflowX: style.overflowX,
                columns: style.gridTemplateColumns,
                whiteSpace: style.whiteSpace,
                overflowWrap: style.overflowWrap,
                parent: element.parentElement?.className,
              };
            }),
        ),
        null,
        2,
      );
      await writeFile(
        `test-results/phase81-judge-plan-${viewport.name}-overflow.json`,
        geometry,
      );
      await testInfo.attach("action-plan-overflow-geometry", {
        body: geometry,
        contentType: "application/json",
      });
    }
    await noOverflow(page);
    await navigate(page, "Review history", /review history/i);
    const storedReviews = await actualGet(
      page,
      `/api/v1/action-plans/${seeded!.plan_id}/reviews?limit=10&offset=0`,
      "reader",
    );
    expect(storedReviews.status).toBe(200);
    expect(storedReviews.body.items.length).toBeGreaterThan(0);
    await expect(
      page.getByText(storedReviews.body.items[0].reason, { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("No recorded review decisions", { exact: true }),
    ).not.toBeVisible();
    await readOnlyControls(page);
    await navigate(page, "Evidence & sources", /evidence & sources/i);
    await expect(
      page.locator("main .detail-list > .card").first(),
    ).toBeVisible();
    await readOnlyControls(page);
    await emptyStorage(page);
    expect(browserMutations).toEqual([]);
    expect(externalRequests).toEqual([]);
    expect(errors).toEqual([]);

    // Separate explicit server-denial probes: they are not browser writes and
    // must never produce an accepted review or disclose global source records.
    expect(
      await deniedReviewStatus(
        page,
        `/api/v1/action-plans/${seeded!.plan_id}/reviews`,
      ),
    ).toBe(403);
    const beforeSubmissions = await actualGet(
      page,
      `/api/v1/programmes/${sampleId}/analyses?limit=1&offset=0`,
      "reader",
    );
    const deniedSubmissions = await deniedJudgeSubmissions(
      page,
      sampleId,
      seeded!.revision_id,
    );
    expect(deniedSubmissions).toEqual({ analysis: 403, upload: 403 });
    const afterSubmissions = await actualGet(
      page,
      `/api/v1/programmes/${sampleId}/analyses?limit=1&offset=0`,
      "reader",
    );
    expect(afterSubmissions.status).toBe(200);
    expect(afterSubmissions.body.total).toBe(beforeSubmissions.body.total);
    expect(
      (await actualGet(page, "/api/v1/sources?limit=1&offset=0", "reader"))
        .status,
    ).toBe(403);
    expect(
      (await actualGet(page, `/api/v1/programmes/${sampleId}`, "foreign"))
        .status,
    ).toBe(404);
    await testInfo.attach("judge-acceptance-scope", {
      body: JSON.stringify({
        viewport: viewport.name,
        programme_id: sampleId,
        revision_id: seeded!.revision_id,
        career_id: career.id,
        plan_id: plan.id,
        courses: planResult.overview.course_ids.length,
        read_only_navigation_mutations: browserMutations.length,
        external_browser_requests: externalRequests.length,
        actual_review_denial: 403,
        actual_live_analysis_denial: deniedSubmissions.analysis,
        actual_upload_denial: deniedSubmissions.upload,
        synthetic_preview_execution_gate:
          access.body.execution.external_processing_allowed,
        external_provider_http: "blocked",
        live_requests: 0,
        scope:
          "Actual protected PostgreSQL results; authenticated controlled read-only preview, not a public guest session. Fictional sources and mocked models; no uploads or generation required.",
      }),
      contentType: "application/json",
    });
  });
}
