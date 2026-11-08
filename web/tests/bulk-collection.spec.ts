import { test, expect } from "@playwright/test";

test("initial collection shows unlimited usage and keeps source pacing explicit", async ({
  page,
}) => {
  await page.route("**/api/admin/overview", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({
      json: { ...data, provider_limit: 0, provider_calls_today: 321 },
    });
  });
  await page.goto("/admin");
  await page.getByRole("button", { name: "Integrations", exact: true }).click();
  await expect(
    page.getByText("Unlimited daily requests during initial collection", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    page.getByText(
      /Paid spending controls and source retry times remain active/,
    ),
  ).toBeVisible();
});
