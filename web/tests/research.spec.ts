import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("guided discovery preserves budget and research exposes honest demo outcomes", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Find my plan", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Budget in rupees").fill("1800");
  await page.getByRole("button", { name: "Not sure? Help me decide." }).click();
  await page
    .getByRole("button", { name: "Try a new flavour", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Relax and talk", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Something outside my usual choices",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Use this direction", exact: true })
    .click();
  await expect(page.getByLabel("Budget in rupees")).toHaveValue("1800");
  await page.goto("/sources");
  await page
    .getByLabel("What should we investigate?")
    .fill("Coimbatore sushi test investigation");
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: /Coimbatore sushi test investigation/ }),
  ).toBeVisible();
  await expect(page.locator(".research-tasks")).toBeVisible();
  await expect(
    page
      .locator(".research-section")
      .getByText("unavailable", { exact: true })
      .first(),
  ).toBeVisible({ timeout: 30000 });
  await page.reload();
  await expect(
    page.getByRole("button", { name: /Coimbatore sushi test investigation/ }),
  ).toBeVisible();
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Data readiness", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Coimbatore readiness" }),
  ).toBeVisible();
  await expect(
    page.getByText("Only fictional demo inventory is being assessed"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Record completed data review" }),
  ).toBeDisabled();
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(
    accessibility.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
});
