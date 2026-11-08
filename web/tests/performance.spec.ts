import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("processing stages distinguish execution and quota waits without claiming accuracy", async ({
  page,
}) => {
  await page.route("**/api/admin/investigations", (route) =>
    route.fulfill({
      json: [
        {
          id: "performance-fixture",
          query: "Controlled timing fixture",
          state: "queued",
          created_at: "2026-11-07T10:00:00Z",
          result: {},
          tasks: [],
          sources: [],
          performance: {
            execution_seconds: 12.5,
            measured_jobs: 2,
            pending_jobs: 4,
            wait_reasons: ["quota_or_collection_cooldown"],
            next_due_at: "2026-11-08T01:00:00Z",
            phases: { local_model: { calls: 2, seconds: 10.5, failures: 1 } },
          },
        },
      ],
    }),
  );
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await page.getByRole("button", { name: /Controlled timing fixture/ }).click();
  const panel = page.getByRole("region", {
    name: "Investigation processing time",
  });
  await expect(
    panel.getByText("12.5 seconds measured processing", { exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByText(/waiting for its allowance or cooldown/),
  ).toBeVisible();
  await panel.getByText("Measured processing stages", { exact: true }).click();
  await expect(panel.getByText(/local model: 10.50s/)).toBeVisible();
  await expect(panel.getByText(/1 failed/)).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()
    ).violations.map((v) => v.id),
  ).toEqual([]);
});

test("extraction benchmark explains the independent-label gate", async ({
  page,
}) => {
  await page.route("**/api/admin/evaluation", (route) =>
    route.fulfill({
      json: {
        collection_coverage: {
          sources_found: 1,
          classified_comments: 0,
          active_spots: 0,
          maps_reviewed: 0,
          indexed_reference_images: 0,
          missing_menu: 0,
          missing_hours: 0,
          missing_vibes: 0,
          limitation: "Controlled fixture only",
        },
        labelled_tasks: 0,
        heldout_tasks: 0,
        status: "needs_evaluation",
        blockers: ["Need independent labels"],
        name_precision: null,
        name_recall: null,
        creator_calibration: {
          groups: 0,
          brier_score: null,
          status: "insufficient_prospective_labels",
        },
        sources: [
          {
            id: "benchmark-fixture",
            url: "https://www.instagram.com/reel/fixture/",
            roles: ["caption"],
            labels: [],
          },
        ],
        comparisons: [],
      },
    }),
  );
  await page.route(
    "**/api/admin/evaluation/sources/benchmark-fixture",
    (route) =>
      route.fulfill({
        json: {
          id: "benchmark-fixture",
          url: "https://www.instagram.com/reel/fixture/",
          comment_texts: [],
          predictions: {
            caption: { venue_candidates: [] },
            comments: {},
            video: {},
          },
        },
      }),
  );
  await page.route(
    "**/api/admin/evaluation/sources/benchmark-fixture/benchmark",
    (route) =>
      route.fulfill({
        status: 409,
        json: {
          detail:
            "Local benchmark requires independent labels for the unchanged retained input",
        },
      }),
  );
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Data readiness", exact: true })
    .click();
  await page
    .getByLabel("Discovered source")
    .selectOption("benchmark-fixture");
  await page
    .getByRole("button", {
      name: "Measure extraction against saved labels",
      exact: true,
    })
    .click();
  await expect(
    page.getByText(
      "Local benchmark requires independent labels for the unchanged retained input",
      { exact: true },
    ),
  ).toBeVisible();
});
