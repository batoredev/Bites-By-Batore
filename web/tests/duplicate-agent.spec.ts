import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const side = (
  id: string,
  name: string,
  area: string,
  status = "identified",
) => ({
  id,
  name,
  area,
  status,
  venue_id: "",
});

const ambiguousPair = {
  key: "branch-fixture",
  left: side("left-fixture", "Zircon Cafe", "RS Puram"),
  right: side("right-fixture", "Zircon Cafe", "Peelamedu"),
  decision: "review" as const,
  reasons: ["Similar extracted names need an exact branch check."],
  conflicts: ["Different neighbourhood evidence; branch identity unresolved."],
};

function spot(record: ReturnType<typeof side>) {
  return {
    ...record,
    category: "cafe",
    updated_at: "2026-11-08T10:00:00Z",
    missing: ["Maps review"],
    map_search_url: "https://www.google.com/maps/search/?api=1&query=fixture",
    data: {},
  };
}

async function mockDesk(
  page: Page,
  options: {
    candidates?: (typeof ambiguousPair)[];
    spots?: ReturnType<typeof spot>[];
  } = {},
) {
  let candidates = options.candidates || [];
  const spots = options.spots || [];
  let state = "completed";
  const writes: { path: string; body: Record<string, unknown> }[] = [];
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(() => {
    localStorage.setItem("batore-demo-session", "duplicate-ui-fixture");
  });
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (request.method() !== "GET") {
      writes.push({ path, body: request.postDataJSON() });
      if (path === "/api/admin/spots/duplicates/run") {
        state = "queued";
        return route.fulfill({ json: { job_id: "scan-fixture", state } });
      }
      if (path.endsWith("/merge")) {
        candidates = [];
        return route.fulfill({ json: { published: false } });
      }
      return route.fulfill({
        status: 500,
        json: { detail: "Unexpected mutation" },
      });
    }
    if (path === "/api/config")
      return route.fulfill({
        json: {
          mode: "local",
          city: "Coimbatore",
          supabase_url: "",
          supabase_key: "",
          max_media_mb: 20,
        },
      });
    if (path === "/api/me")
      return route.fulfill({
        json: {
          id: "operator-fixture",
          name: "Test operator",
          profile: {},
          is_admin: true,
        },
      });
    if (path === "/api/venues") return route.fulfill({ json: [] });
    if (path === "/api/admin/overview")
      return route.fulfill({
        json: {
          mode: "local",
          venues: [],
          review: [],
          jobs: [],
          coverage: {},
          expired_claims: 0,
          integrations: [],
          provider_calls_today: 0,
          provider_limit: 0,
          worker_heartbeat_age_seconds: 1,
          audit: [],
        },
      });
    if (path === "/api/admin/spots/duplicates")
      return route.fulfill({
        json: {
          agent: {
            state,
            last_completed_at: "2026-11-08T10:00:00Z",
            job_id: state === "queued" ? "scan-fixture" : "completed-fixture",
          },
          candidates,
          pending_count: candidates.length,
        },
      });
    if (path === "/api/admin/spots")
      return route.fulfill({
        json: {
          held: spots.filter((row) =>
            ["quarantined", "merged", "rejected"].includes(row.status),
          ).length,
          spots: spots.filter(
            (row) =>
              url.searchParams.get("include_held") === "true" ||
              !["quarantined", "merged", "rejected"].includes(row.status),
          ),
        },
      });
    if (path === "/api/admin/city-collection")
      return route.fulfill({
        json: {
          active_drafts: spots.length,
          directory_linked: 0,
          missing_menu_or_price: spots.length,
          missing_hours_observation: spots.length,
          missing_vibes: spots.length,
          maps_unreviewed: spots.length,
          queries_scheduled: 0,
          discovery_queries: 168,
        },
      });
    return route.fulfill({
      status: 404,
      json: { detail: "Unexpected fixture request" },
    });
  });
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Identified spots", exact: true })
    .click();
  await expect(page.getByLabel("Duplicate agent status")).toContainText(
    "Duplicate agent: completed",
  );
  return {
    writes,
    errors,
    desk: page.getByRole("region", { name: "Duplicate review desk" }),
  };
}

test("ambiguous branches remain separate and review never prechecks or submits a merge", async ({
  page,
}) => {
  const { writes, errors, desk } = await mockDesk(page, {
    candidates: [ambiguousPair],
  });
  await expect(desk).toContainText(
    "Similar extracted names need an exact branch check.",
  );
  await expect(desk).toContainText(
    "Different neighbourhood evidence; branch identity unresolved.",
  );
  await expect(desk).toContainText("RS Puram");
  await expect(desk).toContainText("Peelamedu");
  expect(writes).toEqual([]);
  await desk
    .getByRole("button", { name: "Review this duplicate pair" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Review duplicate branch" });
  const merge = dialog.getByRole("button", {
    name: "Merge checked duplicate and retain evidence",
  });
  const branch = dialog.getByLabel(
    "I checked that both records refer to the exact same branch.",
  );
  await expect(branch).not.toBeChecked();
  await expect(dialog.getByLabel("Surviving draft")).toHaveValue("");
  await expect(merge).toBeDisabled();
  await dialog.getByLabel("Surviving draft").selectOption("left-fixture");
  await dialog
    .getByLabel("Evidence for this exact same branch")
    .fill("Independent evidence is still required.");
  await expect(merge).toBeDisabled();
  expect(writes).toEqual([]);
  await dialog.getByRole("button", { name: "Close dialog" }).click();
  await desk
    .getByRole("button", { name: "Review this duplicate pair" })
    .click();
  await expect(branch).not.toBeChecked();
  await expect(dialog.getByLabel("Surviving draft")).toHaveValue("");
  await expect(
    dialog.getByLabel("Evidence for this exact same branch"),
  ).toHaveValue("");
  expect(writes).toEqual([]);
  expect(errors).toEqual([]);
});

test("explicit checked review merges a held source into the chosen active draft only", async ({
  page,
}) => {
  const heldPair = {
    ...ambiguousPair,
    left: side(
      "held-fixture",
      "Zircon Cafe alternate spelling",
      "RS Puram",
      "quarantined",
    ),
    right: side("active-fixture", "Zircon Cafe", "RS Puram"),
    conflicts: [],
  };
  const { writes, errors, desk } = await mockDesk(page, {
    candidates: [heldPair],
  });
  await desk
    .getByRole("button", { name: "Review this duplicate pair" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Review duplicate branch" });
  const survivor = dialog.getByLabel("Surviving draft");
  await expect(survivor.locator("option")).toHaveCount(2);
  await expect(survivor.locator('option[value="held-fixture"]')).toHaveCount(0);
  await survivor.selectOption("active-fixture");
  await dialog
    .getByLabel("I checked that both records refer to the exact same branch.")
    .check();
  const reason = dialog.getByLabel("Evidence for this exact same branch");
  await reason.fill("short");
  const merge = dialog.getByRole("button", {
    name: "Merge checked duplicate and retain evidence",
  });
  await expect(merge).toBeDisabled();
  expect(writes).toEqual([]);
  await reason.fill(
    "  Operator compared the same address in the retained original evidence.  ",
  );
  await merge.click();
  await expect(dialog).not.toBeVisible();
  expect(writes).toEqual([
    {
      path: "/api/admin/spots/held-fixture/merge",
      body: {
        target_id: "active-fixture",
        same_branch_checked: true,
        reason:
          "Operator compared the same address in the retained original evidence.",
      },
    },
  ]);
  await expect(desk).toContainText(
    "Original records and evidence retained; approvals are unchanged.",
  );
  await expect(desk).toContainText("0 pairs awaiting review");
  expect(errors).toEqual([]);
});

test("existing held-record merge action excludes rejected, merged and prepared drafts", async ({
  page,
}) => {
  const held = spot(
    side("held-card", "Held cafe fixture", "RS Puram", "quarantined"),
  );
  const active = spot(side("active-card", "Active cafe fixture", "RS Puram"));
  const prepared = {
    ...spot(side("prepared-card", "Prepared cafe fixture", "RS Puram")),
    venue_id: "venue-fixture",
  };
  const records = [
    held,
    active,
    prepared,
    spot(side("merged-card", "Merged cafe fixture", "RS Puram", "merged")),
    spot(
      side("rejected-card", "Rejected cafe fixture", "RS Puram", "rejected"),
    ),
  ];
  const { writes } = await mockDesk(page, { spots: records });
  await page.getByLabel(/Show held and merged records/).check();
  const card = page.locator("article.review-card").filter({
    has: page.getByRole("heading", {
      name: "Held cafe fixture",
      exact: true,
    }),
  });
  await card
    .getByRole("button", { name: "Merge duplicate after branch check" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Merge Held cafe fixture" });
  const survivor = dialog.getByLabel("Surviving location");
  await expect(survivor.locator("option")).toHaveCount(2);
  await survivor.selectOption("active-card");
  await dialog
    .getByLabel("Evidence for the same branch")
    .fill(
      "The exact address and original source were checked by the operator.",
    );
  await expect(
    dialog.getByRole("button", { name: "Merge and retain original evidence" }),
  ).toBeDisabled();
  await dialog
    .getByLabel("I checked that both records refer to the same branch.")
    .check();
  await dialog
    .getByRole("button", { name: "Merge and retain original evidence" })
    .click();
  await expect(dialog).not.toBeVisible();
  expect(writes).toHaveLength(1);
  expect(writes[0].path).toBe("/api/admin/spots/held-card/merge");
  expect(writes[0].body.target_id).toBe("active-card");
  for (const name of [
    "Prepared cafe fixture",
    "Merged cafe fixture",
    "Rejected cafe fixture",
  ]) {
    const excluded = page
      .locator("article.review-card")
      .filter({ has: page.getByRole("heading", { name, exact: true }) });
    await expect(
      excluded.getByRole("button", {
        name: "Merge duplicate after branch check",
      }),
    ).toHaveCount(0);
  }
});

test("duplicate review pages limit cards to twenty and scans run only on request", async ({
  page,
}) => {
  const candidates = Array.from({ length: 21 }, (_, i) => ({
    ...ambiguousPair,
    key: `page-fixture-${i}`,
    left: side(`left-${i}`, `Cafe candidate ${i + 1}`, "RS Puram"),
    right: side(`right-${i}`, `Cafe spelling ${i + 1}`, "RS Puram"),
  }));
  const { writes, errors, desk } = await mockDesk(page, { candidates });
  await expect(desk.locator("article.review-card")).toHaveCount(20);
  await expect(desk).toContainText("Showing 1–20 of 21 review pairs.");
  expect(writes).toEqual([]);
  await desk.getByRole("button", { name: "Next duplicate pairs" }).click();
  await expect(desk.locator("article.review-card")).toHaveCount(1);
  await expect(desk).toContainText("Showing 21–21 of 21 review pairs.");
  await desk.getByLabel("Filter duplicate pairs").fill("candidate 21");
  await expect(desk).toContainText(
    "Showing 1–1 of 1 review pairs matching this filter.",
  );
  await desk.getByRole("button", { name: "Refresh duplicate review" }).click();
  expect(writes).toEqual([]);
  await desk.getByRole("button", { name: "Run duplicate agent" }).click();
  await expect(page.getByLabel("Duplicate agent status")).toContainText(
    "Duplicate agent: queued",
  );
  expect(writes).toEqual([
    { path: "/api/admin/spots/duplicates/run", body: {} },
  ]);
  await expect(
    desk.getByRole("button", { name: "Run duplicate agent" }),
  ).toBeDisabled();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()
    ).violations.map((v) => v.id),
  ).toEqual([]);
  expect(errors).toEqual([]);
});
