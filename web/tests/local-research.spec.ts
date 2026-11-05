import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ request }) => {
  const config = await (await request.get("/api/config")).json();
  test.skip(
    config.mode !== "local",
    "Requires the isolated local research instance",
  );
});

test("local operator can inspect autonomous research without cloud sign-in", async ({
  page,
}) => {
  await page.goto("/admin");
  await expect(page.getByText("LOCAL RESEARCH", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Coimbatore research agent" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Find the next examples for me" }),
  ).toBeVisible();
  await expect(
    page.getByText(/Local model: qwen3-vl:2b-instruct/),
  ).toBeVisible();
  await expect(
    page.getByText(/Direct browser: (enabled|disabled)/),
  ).toBeVisible();
  const issues = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(
    issues.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.reload();
  await expect(page.getByText("LOCAL RESEARCH", { exact: true })).toBeVisible();
});

test("review correction form sends scoped feedback and can revoke it", async ({
  page,
}) => {
  let rows: object[] = [];
  await page.route("**/api/admin/investigations", (route) =>
    route.fulfill({
      json: [
        {
          id: "ui-fixture",
          query: "UI test source",
          state: "review",
          created_at: "2026-11-04T10:00:00Z",
          result: {},
          tasks: [],
          sources: [
            {
              id: "ui-source",
              url: "https://www.instagram.com/reel/test123/",
              platform: "instagram",
              creator: "",
              state: "partial",
              content: { search_preview: "Test fixture, not a real venue" },
              analysis: {},
            },
          ],
        },
      ],
    }),
  );
  await page.route("**/api/admin/research-corrections", (route) =>
    route.fulfill({ json: rows }),
  );
  await page.route(
    "**/api/admin/research-sources/ui-source/corrections",
    async (route) => {
      const data = route.request().postDataJSON();
      expect(data.scope).toBe("Fixture cafe");
      expect(data.role).toBe("caption");
      rows = [
        { ...data, id: "ui-correction", source_id: "ui-source", active: true },
      ];
      await route.fulfill({ json: rows[0] });
    },
  );
  await page.route(
    "**/api/admin/research-corrections/ui-correction",
    async (route) => {
      rows = rows.map((r) => ({ ...r, active: false }));
      await route.fulfill({ json: { active: false } });
    },
  );
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await page.getByRole("button", { name: /UI test source/ }).click();
  await page.getByText("Teach the agent a correction", { exact: true }).click();
  await page.getByLabel("Scope phrase").fill("Fixture cafe");
  await page
    .getByLabel("What did the agent get wrong?")
    .fill("Price was interpreted per person");
  await page.getByLabel("Correct interpretation").fill("The price is per dish");
  await page
    .getByLabel("Evidence and reason")
    .fill("The fixture menu explicitly labels one dish serving.");
  await page.getByRole("button", { name: "Save learning example" }).click();
  await expect(
    page.getByRole("button", { name: "Stop reusing this correction" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Stop reusing this correction" })
    .click();
  await expect(page.getByText("Revoked", { exact: true })).toBeVisible();
});

test("identified spots show evidence and stay behind location approval", async ({
  page,
}) => {
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Identified spots", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Coimbatore identified spots" }),
  ).toBeVisible();
  await expect(
    page.getByText(/Every location needs your approval/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Collect official menus and details" }),
  ).toBeVisible();
  await expect(page.getByText(/drafts are not recommendations/)).toBeVisible();
  const issues = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(issues.violations.map((v) => v.id)).toEqual([]);
});
