import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("known-location skips show incomplete coverage and keep original evidence accessible", async ({
  page,
}) => {
  await page.route("**/api/admin/investigations", (route) =>
    route.fulfill({
      json: [
        {
          id: "known-fixture",
          query: "Known cafe fixture",
          state: "review",
          created_at: "2026-11-08T00:00:00Z",
          result: {},
          tasks: [],
          sources: [
            {
              id: "source-fixture",
              url: "https://www.instagram.com/reel/fixture/",
              platform: "instagram",
              creator: "",
              state: "known_spot_reference",
              content: { processing_outcome: "skipped_known_location" },
              analysis: {
                discovery_skip: {
                  spot_ids: ["spot-fixture"],
                  coverage_complete: false,
                },
                caption: { status: "skipped_known_location" },
                video: { status: "skipped_known_location" },
                comments: { status: "skipped_known_location" },
              },
            },
          ],
        },
      ],
    }),
  );
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await page.getByRole("button", { name: /Known cafe fixture/ }).click();
  await expect(
    page.getByText(/Remaining reel processing was skipped; new facts/),
  ).toBeVisible();
  await expect(
    page.getByText(/video: skipped, location already recorded/),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open original source", exact: true }),
  ).toHaveAttribute("href", "https://www.instagram.com/reel/fixture/");
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()
    ).violations.map((v) => v.id),
  ).toEqual([]);
});

test("full known-location inspection is an explicit request option", async ({
  page,
}) => {
  let sent = false;
  await page.route("**/api/investigations", async (route) => {
    if (route.request().method() === "POST") {
      expect(route.request().postDataJSON().force_full_analysis).toBe(true);
      sent = true;
      await route.fulfill({
        json: {
          id: "full-fixture",
          query: "Coimbatore fixture",
          state: "queued",
          result: {},
          tasks: [],
          sources: [],
        },
      });
    } else await route.fulfill({ json: [] });
  });
  await page.goto("/sources");
  await page
    .getByLabel("What should we investigate?")
    .fill("Coimbatore fixture");
  await page
    .getByLabel(
      "Inspect known locations again, including the remaining reel evidence",
    )
    .check();
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  await expect.poll(() => sent).toBe(true);
});
