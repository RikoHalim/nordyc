import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { expect, type Page } from "@playwright/test";

type Grant = {
  token: string;
  institution_ids: string[];
  permissions: string[];
};
const authPath = process.env.SHIFTOS_PREVIEW_AUTH;
if (!authPath) throw new Error("Private preview configuration is required.");
const grants = JSON.parse(readFileSync(authPath, "utf8")) as Record<
  string,
  Grant
>;
export const receipt = JSON.parse(
  readFileSync(resolve(dirname(authPath), "receipt.json"), "utf8"),
) as {
  is_synthetic: boolean;
  live_requests: number;
  programmes: {
    programme_id: string;
    institution_id: string;
    revision_id: string;
    discipline: string;
    career_id: string;
    phase4_id: string;
    plan_id: string;
  }[];
};
if (!receipt.is_synthetic || receipt.live_requests !== 0)
  throw new Error(
    "Browser acceptance requires an explicitly fictional, non-billable preview receipt.",
  );
export const programme = receipt.programmes.find(
  (row) => row.discipline === "computing",
)!;
if (!programme)
  throw new Error("The labelled computing preview is unavailable.");

export async function login(page: Page, role = "operator", path = "/") {
  const grant = grants[role];
  if (!grant?.token)
    throw new Error("The requested local test grant is unavailable.");
  await page.goto(path);
  await expect(page.getByLabel("Scoped operator credential")).toBeVisible();
  // Populate only the real password control. No traced fill arguments, storage
  // state, screenshots, headers or credential-bearing assertion values exist.
  try {
    await page
      .getByLabel("Scoped operator credential")
      .evaluate((element, value) => {
        Object.getOwnPropertyDescriptor(
          HTMLInputElement.prototype,
          "value",
        )!.set!.call(element, value);
        element.dispatchEvent(new Event("input", { bubbles: true }));
      }, grant.token);
    await page
      .getByRole("button", { name: "Connect workspace", exact: true })
      .click();
    await expect(
      page.getByLabel("Scoped operator credential"),
    ).not.toBeVisible();
  } catch {
    throw new Error(
      "The private UI connection could not be completed; credential details are withheld.",
    );
  }
}

export async function actualGet(page: Page, path: string, role = "operator") {
  if (!path.startsWith("/api/v1/"))
    throw new Error("Only local protected acceptance routes are supported.");
  try {
    const response = await page.request.get(path, {
      headers: { Authorization: `Bearer ${grants[role].token}` },
    });
    return { status: response.status(), body: await response.json() };
  } catch {
    throw new Error(
      "The protected acceptance read failed; request details are withheld.",
    );
  }
}
export async function deniedReviewStatus(page: Page, path: string) {
  if (!/^\/api\/v1\/action-plans\/[a-f\d-]+\/reviews$/.test(path))
    throw new Error(
      "Only the bounded reader-denial review probe is supported.",
    );
  try {
    return (
      await page.request.post(path, {
        headers: { Authorization: `Bearer ${grants.reader.token}` },
        data: {
          decision: "under_review",
          reason:
            "Fictional reader-denial acceptance probe; must never be persisted.",
          expected_plan_fingerprint: "0".repeat(64),
        },
      })
    ).status();
  } catch {
    throw new Error(
      "The bounded denial check failed; request details are withheld.",
    );
  }
}

export async function openProgramme(page: Page) {
  await page
    .locator(
      `.programme-card[href="/programmes/${programme.programme_id}/overview"]`,
    )
    .click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: /A clearer view of your curriculum/i,
    }),
  ).toBeVisible();
}
export async function navigate(page: Page, label: string, heading: RegExp) {
  let link = page
    .getByRole("link", { name: label, exact: true })
    .filter({ visible: true })
    .first();
  const box = (await link.count()) ? await link.boundingBox() : null;
  const viewport = page.viewportSize();
  if (
    !(await link.count()) ||
    !(await link.isVisible()) ||
    !box ||
    box.x < 0 ||
    (viewport && box.x >= viewport.width)
  ) {
    await page.getByRole("button", { name: "Open programme menu" }).click();
    link = page
      .getByRole("link", { name: label, exact: true })
      .filter({ visible: true })
      .first();
  }
  await link.click();
  await expect(
    page.getByRole("heading", { level: 1, name: heading }),
  ).toBeVisible();
  await expect(
    page.getByText("Loading workspace records…", { exact: true }),
  ).not.toBeVisible();
}
export async function noOverflow(page: Page) {
  const geometry = await page.evaluate(() => ({
    overflow:
      Math.max(
        document.documentElement.scrollWidth,
        document.body.scrollWidth,
      ) - innerWidth,
    elements: Array.from(document.body.querySelectorAll("*"))
      .filter((element) => {
        const style = getComputedStyle(element);
        const box = element.getBoundingClientRect();
        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          (box.right > innerWidth + 1 || box.left < -1)
        );
      })
      .slice(0, 20)
      .map((element) => {
        const box = element.getBoundingClientRect();
        return {
          tag: element.tagName,
          class: element.className,
          left: Math.round(box.left),
          right: Math.round(box.right),
          width: Math.round(box.width),
        };
      }),
  }));
  expect(
    geometry.overflow,
    `Page-level horizontal overflow in the actual preview: ${JSON.stringify(geometry.elements)}`,
  ).toBeLessThanOrEqual(1);
}
export async function emptyStorage(page: Page) {
  expect(
    await page.evaluate(() => ({
      local: Object.keys(localStorage),
      session: Object.keys(sessionStorage),
    })),
  ).toEqual({ local: [], session: [] });
}
export function observeErrors(page: Page) {
  const errors: string[] = [];
  const scrub = (value: string) =>
    Object.values(grants).reduce(
      (text, grant) => text.replaceAll(grant.token, "[private credential]"),
      value,
    );
  page.on("pageerror", (error) => errors.push(scrub(error.message)));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(scrub(message.text()));
  });
  return errors;
}

export async function localNetworkOnly(page: Page) {
  await page.context().route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (
      ["http:", "https:"].includes(url.protocol) &&
      !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
    )
      return route.abort();
    return route.continue();
  });
}
