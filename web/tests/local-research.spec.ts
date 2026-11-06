import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("maintenance packets expose blockers and require reviewed evidence without publication", async ({ page }) => {
  let reviewed = false;
  const packet = {
    id: "maintenance-fixture", name: "Zircon Cafe", area: "RS Puram", category: "cafe", status: "identified",
    maps_url: "https://www.google.com/maps/search/?api=1&query=fixture", venue_id: "",
    blockers: ["Independently confirm exact Maps name, address and branch"], missing: ["Current opening hours"],
    ready_for_final_approval: false, location_approved: false, conflicts: [], possible_duplicates: [], sources: [],
    page_checks: {}, fact_evidence: [],
  };
  await page.route("**/api/admin/maintenance", route => route.fulfill({ json: {
    draft_count: 1, approved_count: 0, ready_for_approval: 0, open_alerts: reviewed ? 0 : 1,
    pages_monitored: 1, pages_overdue: 0, unavailable_pages: 0, coverage: "UI fixture only",
    cadence: { page_hours: 24, reel_days: 7, reel_checks_per_day: 6, note: "Checks may be delayed" },
    packets: [{...packet, alerts: reviewed ? [] : [{ id: "alert-fixture", kind: "source_changed", url: "https://fixture.example/", detail: {fields:["hours"]}, at: "2026-11-06T00:00:00Z" }]}],
    grid: [], evaluation_queue: [], failed_jobs: [],
  }}));
  await page.route("**/api/admin/maintenance/packets/maintenance-fixture/alerts/alert-fixture/resolve", async route => {
    const body = route.request().postDataJSON();
    expect(body.checked_original).toBe(true);
    expect(body.reason).toContain("Fixture"); reviewed = true;
    await route.fulfill({ json: { reviewed: true, published: false } });
  });
  await page.goto("/admin");
  await page.getByRole("button", { name: "Data readiness", exact: true }).click();
  await page.getByLabel("Location approval packet").selectOption("maintenance-fixture");
  await expect(page.getByText("Independently confirm exact Maps name, address and branch", {exact:true})).toBeVisible();
  await page.getByText(/source changed ·/).click();
  await page.getByLabel("What changed and how was it checked?").fill("Fixture opening hours independently reviewed against original evidence.");
  await page.getByLabel("I inspected the source and reviewed the affected facts.").check();
  await page.getByRole("button", { name: "Record alert review" }).click();
  await expect.poll(() => reviewed).toBe(true);
  await expect(page.getByText(/1 active records · 0 approved/)).toBeVisible();
  const issues = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(issues.violations.map(v => v.id)).toEqual([]);
});

test("accuracy review saves checked labels without publishing a venue", async ({ page }) => {
  let saved = false;
  await page.route("**/api/admin/evaluation", route => route.fulfill({ json: {
    collection_coverage: { sources_found: 1, classified_comments: 0, active_spots: 0, maps_reviewed: 0, indexed_reference_images: 0, missing_menu: 0, missing_hours: 0, missing_vibes: 0, limitation: "UI fixture only" },
    labelled_tasks: saved ? 1 : 0, heldout_tasks: 0, status: "needs_evaluation",
    blockers: ["Need independent labels"], name_precision: null, name_recall: null,
    creator_calibration: { groups: 0, brier_score: null, status: "insufficient_prospective_labels" },
    sources: [{ id: "evaluation-fixture", url: "https://www.instagram.com/p/fixture/", roles: ["caption"], labels: [] }], comparisons: []
  } }));
  await page.route("**/api/admin/evaluation/sources/evaluation-fixture", route => route.fulfill({ json: {
    id: "evaluation-fixture", url: "https://www.instagram.com/p/fixture/", comment_texts: [], predictions: { caption: { venue_candidates: [] } }
  } }));
  await page.route("**/api/admin/evaluation/sources/evaluation-fixture/label", async route => {
    const body = route.request().postDataJSON();
    expect(body.source_checked).toBe(true);
    expect(body.expected_names).toEqual(["Zircon Cafe"]);
    saved = true;
    await route.fulfill({ json: { saved: true, split: "development", publication: false } });
  });
  await page.goto("/admin");
  await page.getByRole("button", { name: "Data readiness", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Instagram accuracy review" })).toBeVisible();
  await page.getByLabel("Discovered source").selectOption("evaluation-fixture");
  await page.getByLabel(/Correct venue names/).fill("Zircon Cafe");
  await page.getByLabel("Review notes", { exact: true }).fill("Independent original-source fixture review.");
  await page.getByLabel(/I inspected the original source/).check();
  await page.getByRole("button", { name: "Save evaluation labels" }).click();
  await expect(page.getByRole("status").filter({ hasText: "No location was approved" })).toBeVisible();
  const issues = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(issues.violations.map(v => v.id)).toEqual([]);
});

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

test("identity review requires a Maps place and exposes held records without writing fixtures", async ({
  page,
}) => {
  const fixture = {
    id: "quality-fixture",
    name: "Zircon Cafe",
    category: "cafe",
    area: "RS Puram",
    status: "identified",
    venue_id: "",
    updated_at: "2026-11-06T00:00:00Z",
    missing: ["Maps identity"],
    map_search_url: "https://www.google.com/maps/search/?api=1&query=Zircon",
    data: {
      name_status: "unconfirmed_extraction",
      sources: [],
      aliases: ["Zircon Cafe", "Cafe Zircon"],
    },
  };
  let heldRequested = false;
  await page.route("**/api/admin/spots**", async (route) => {
    const url = route.request().url();
    if (url.endsWith("/maps-candidates")) {
      await route.fulfill({
        json: {
          status: "unavailable",
          reason: "Google Places access is not configured",
          candidates: [],
        },
      });
    } else if (route.request().method() === "GET") {
      heldRequested = url.includes("include_held=true");
      await route.fulfill({
        json: { spots: [fixture], total: 2, active: 1, held: 1 },
      });
    } else {
      await route.abort();
    }
  });
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Identified spots", exact: true })
    .click();
  await expect(
    page.getByText("Extracted name — Maps identity unconfirmed"),
  ).toBeVisible();
  await page.getByLabel(/Show held and merged records/).check();
  await expect.poll(() => heldRequested).toBe(true);
  await page
    .getByRole("button", { name: "Prepare location for approval" })
    .click();
  await expect(page.getByLabel(/Exact Google Maps place URL/)).toHaveAttribute(
    "required",
    "",
  );
  await page.getByRole("button", { name: "Look up Maps candidates" }).click();
  await expect(
    page.getByText(/Google Places access is not configured/),
  ).toBeVisible();
  await expect(
    page.getByLabel(/I checked that this location name matches/),
  ).not.toBeChecked();
  const issues = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(issues.violations.map((v) => v.id)).toEqual([]);
});
