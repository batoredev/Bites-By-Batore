import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("main screens meet automated WCAG A/AA checks", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Find my plan", exact: true }),
  ).toBeVisible();
  for (const path of [
    "/",
    "/places",
    "/saved",
    "/taste",
    "/sources",
    "/admin",
  ]) {
    if (path !== "/") {
      await page.goto(path);
      await expect(page.locator("main h1")).toBeVisible();
    }
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(
      results.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
      path,
    ).toEqual([]);
  }
});
