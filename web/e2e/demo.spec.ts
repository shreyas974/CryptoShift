import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

const PASSWORD = process.env.E2E_PASSWORD ?? "";
const SCREENS = "../docs/webapp/screens";
const OUT = "../scratch/derived/webapp";
const PAGES = [
  ["overview", /Find, plan and verify/],
  ["sources", "Data & evidence"],
  ["activity", "Activity"],
  ["inventory", "Inventory"],
  ["dependencies", "Dependencies"],
  ["evaluation", "Detection evaluation"],
  ["plan", "Migration plan"],
  ["verification", "Verification"],
  ["approval", "Approval & rollback"],
  ["runs", "Datasets & runs"],
  ["reports", "Reports"],
  ["claims", "Claims & limits"],
  ["ml", "ML & AI"],
  ["audit", "Audit log"],
  ["users", "Users & roles"],
  ["settings", "Settings"],
] as const;
const FIXTURE = "../tests/fixtures/multiservice_bank";

async function login(page: Page, user = "e2e-approver") {
  await page.goto("/");
  await page.getByLabel("Username").fill(user);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();
}

/** Display toggles and sign-out live in the account menu (top right). */
async function accountMenu(page: Page, item: RegExp) {
  await page.getByRole("button", { name: /^Account: / }).click();
  await page.getByRole("button", { name: item }).click();
  await page.keyboard.press("Escape");
}

async function setTheme(page: Page, theme: "dark" | "light") {
  const current = await page.evaluate(() => document.documentElement.dataset.theme);
  if (current !== theme) await accountMenu(page, theme === "light" ? /^Light theme/ : /^Dark theme/);
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
}

test("demo path: every page loads real data, passes axe (or records it), screenshots saved", async ({ page }) => {
  const cspErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    (m.text().includes("Content Security Policy") ? cspErrors : consoleErrors).push(m.text().slice(0, 200));
  });
  mkdirSync(SCREENS, { recursive: true });
  await login(page);
  const axe: Record<
    string,
    {
      violations: { id: string; impact: string | null | undefined; nodes: number; targets: string[] }[];
      incomplete: string[];
    }
  > = {};
  for (const theme of ["dark", "light"] as const) {
    await setTheme(page, theme);
    for (const [id, title] of PAGES) {
      await page.goto(`/#/${id}`);
      await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
      await expect(page.getByText(/^Loading /)).toHaveCount(0, { timeout: 30_000 });
      await expect(page.getByText(/Could not load data/)).toHaveCount(0);
      await page.waitForTimeout(300);
      const r = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .exclude("canvas")
        .analyze();
      axe[`${theme}/${id}`] = {
        violations: r.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          nodes: v.nodes.length,
          targets: v.nodes.slice(0, 4).map((n) => `${n.target.join(" ")} :: ${n.failureSummary?.slice(0, 160) ?? ""}`),
        })),
        incomplete: r.incomplete.map((i) => i.id),
      };
      await page.screenshot({ path: `${SCREENS}/${theme}-${id}.png`, fullPage: false });
    }
  }
  writeFileSync(`${OUT}/axe-results.json`, JSON.stringify({ axe, cspErrors, consoleErrors }, null, 2));
  expect(cspErrors, "Content-Security-Policy violations").toEqual([]);
  expect(
    Object.entries(axe).filter(([, a]) => a.violations.length),
    "axe violations",
  ).toEqual([]);
});

test("overview shows real pipeline stages and the honesty banner", async ({ page }) => {
  await login(page, "e2e-viewer");
  await expect(page.getByText(/Hackathon prototype \(PQC-01\)/)).toBeVisible();
  for (const stage of ["Inventory", "Dependency graph", "Risk score", "QpiAI Opt", "QCloud QAOA", "Gates"]) {
    await expect(page.getByText(stage, { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByText("SIMULATOR").first()).toBeVisible();
  await expect(page.getByText("provisional, not validated").first()).toBeVisible();
});

test("evidence drawer and command palette", async ({ page }) => {
  await login(page, "e2e-viewer");
  await page.getByRole("button", { name: "Evidence for Findings" }).click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toContainText("reports/member3/plan.json");
  await expect(drawer).toContainText("scripts/member3_pipeline.py");
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await page.keyboard.press("Control+k");
  await page.getByLabel("Search commands").fill("Verification");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { level: 1, name: "Verification" })).toBeVisible();
});

test("approval dialog stays disabled until READY + name + plan hash + acknowledgement (never clicked)", async ({
  page,
}) => {
  await login(page, "e2e-approver");
  await page.goto("/#/approval");
  const rows = page.locator("tbody tr");
  await expect(rows.first()).toBeVisible();
  const proposed = rows.filter({ hasText: "PROPOSED" }).first();
  await proposed.getByRole("button", { name: "Review…" }).click();
  const approve = page.getByRole("button", { name: "Approve this step" });
  await page.getByLabel("Approver name").fill("TEST-ONLY");
  await expect(approve).toBeDisabled();
  await page.keyboard.press("Escape");
  const ready = rows.filter({ hasText: "READY" }).first();
  await ready.getByRole("button", { name: "Review…" }).click();
  await page.getByLabel("Approver name").fill("TEST-ONLY");
  await expect(approve).toBeDisabled();
  const hashText =
    (await page
      .getByText(/^Steps \(plan hash/)
      .first()
      .textContent()) ?? "";
  const prefix = /plan hash ([0-9a-f]{12})/.exec(hashText)?.[1] ?? "";
  await page.getByLabel("Plan hash (first 12+ characters)").fill(prefix);
  await expect(approve).toBeDisabled();
  await page.getByLabel("I understand this records my approval").check();
  await expect(approve).toBeEnabled();
});

test("viewer cannot use approver-only controls; assistant answers in TEMPLATE_FALLBACK", async ({ page }) => {
  await login(page, "e2e-viewer");
  await page.goto("/#/approval");
  await expect(page.getByRole("button", { name: "Review…" }).first()).toBeDisabled();
  await page.getByRole("button", { name: /^Account: / }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByLabel("Username")).toBeVisible(); // sign-out really ended the session
  await login(page, "e2e-analyst");
  await page.goto("/#/ml");
  await page.getByRole("button", { name: "Ask the assistant" }).click();
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("TEMPLATE_FALLBACK", { timeout: 30_000 });
});

test("performance on this machine: load time and frame rate on the heaviest page", async ({ page }) => {
  await login(page, "e2e-viewer");
  const t0 = Date.now();
  await page.goto("/#/inventory");
  await expect(page.getByRole("heading", { level: 1, name: "Inventory" })).toBeVisible();
  await expect(page.getByText(/rows$/).first()).toBeVisible();
  const inventoryReadyMs = Date.now() - t0;
  const nav = await page.evaluate(() => {
    const n = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    return n
      ? { domContentLoadedMs: Math.round(n.domContentLoadedEventEnd), loadMs: Math.round(n.loadEventEnd) }
      : null;
  });
  const fps = await page.evaluate(
    () =>
      new Promise<number>((resolve) => {
        let frames = 0;
        const start = performance.now();
        const tick = (now: number) => {
          frames++;
          if (now - start < 3000) requestAnimationFrame(tick);
          else resolve(Math.round((frames * 1000) / (now - start)));
        };
        requestAnimationFrame(tick);
      }),
  );
  writeFileSync(
    `${OUT}/perf.json`,
    JSON.stringify(
      {
        page: "inventory",
        inventoryReadyMs,
        navigation: nav,
        rafFps3s: fps,
        viewport: "1440x900",
        browser: "system Chrome (Playwright channel=chrome)",
      },
      null,
      2,
    ),
  );
  expect(fps).toBeGreaterThan(0);
});

test("anatomy figure: renders from real data in both themes; close-ups for review", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "e2e-viewer");
  const fig = page.locator(".pl-figure");
  await expect(fig).toBeVisible();
  await expect(fig.locator("[data-readout]")).toContainText(
    /wave \d · (READY|PROPOSED|APPROVED|UNKNOWN) · \d+\/\d+ ready · objective /,
  );
  const crates = await fig.locator(".pl-crate").count();
  expect(crates).toBeGreaterThan(0);
  for (const theme of ["dark", "light"] as const) {
    await setTheme(page, theme);
    await accountMenu(page, /^Reduce motion/); // freeze for a stable still
    await fig.screenshot({ path: `${SCREENS}/figure-${theme}.png` });
    await accountMenu(page, /^Reduce motion/);
  }
  // keyboard: arrow keys step through services
  await setTheme(page, "dark");
  const before = await fig.locator("[data-readout]").textContent();
  await fig.locator(".pl-stage").focus();
  await page.keyboard.press("ArrowRight");
  await expect(fig.locator("[data-readout]")).not.toHaveText(before ?? "");
  writeFileSync(`${OUT}/figure-check.json`, JSON.stringify({ crates, readoutBefore: before }, null, 2));
});

test("analyst uploads a dataset, runs discovery and gets findings and downloadable outputs", async ({ page }) => {
  const { readdirSync, statSync } = await import("node:fs");
  const { join } = await import("node:path");
  const files = (readdirSync(FIXTURE, { recursive: true }) as string[])
    .map((f) => join(FIXTURE, f))
    .filter((f) => statSync(f).isFile());
  await login(page, "e2e-analyst");
  await page.goto("/#/runs");
  await page.getByLabel("Choose files or .zip").setInputFiles(files);
  await page.getByLabel("Dataset name (optional)").fill("e2e-fixture");
  await page.getByLabel(/^Discovery\s*Member 2/).check();
  const run = page.getByRole("button", { name: "Upload and run" });
  await expect(run).toBeDisabled(); // authorization not yet acknowledged
  await page.getByLabel(/I am authorized/).check();
  await run.click();
  await expect(page.getByRole("tab", { name: /Findings \(\d+\)/ })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("succeeded").first()).toBeVisible();
  await expect(page.getByRole("link", { name: /summary\.json/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Delete run" })).toHaveCount(0); // analysts cannot delete
});

test("approver manages users; viewer cannot; report and activity bell work", async ({ page }) => {
  await login(page, "e2e-approver");
  await page.goto("/#/users");
  await page.getByLabel("Username").fill("e2e-new-viewer");
  await page.getByLabel(/Initial password/).fill("a-long-test-password-1");
  await page.getByRole("button", { name: "Add user" }).click();
  await expect(page.getByRole("cell", { name: /e2e-new-viewer/ })).toBeVisible();
  await page.goto("/#/reports");
  await expect(page.getByRole("button", { name: "Save as PDF / print" })).toBeVisible();
  await expect(page.getByText("What this report does not claim")).toBeVisible();
  await page.getByRole("button", { name: /^Activity/ }).click();
  await expect(page.getByText(/e2e-approver added a user/).first()).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /^Account: / }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "e2e-viewer");
  await page.goto("/#/users");
  await expect(page.getByText("Only approvers can manage users.")).toBeVisible();
});
