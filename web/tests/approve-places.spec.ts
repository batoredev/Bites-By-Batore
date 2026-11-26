import { test, expect, type Route } from "@playwright/test";

// Operations > Approve places: the owner approves every place personally. The API is
// faked here so the flow is tested without real places; the backend has its own tests.

const week = Object.fromEntries([0, 1, 2, 3, 4, 5, 6].map((d) => [String(d), [[600, 1320]]]));

const place = (id: string, name: string, over: Record<string, unknown> = {}) => ({
  id,
  name,
  category: "cafe",
  area: "RS Puram",
  address: "DB Road",
  lat: 11.0,
  lng: 76.95,
  tags: ["coffee"],
  hours: week,
  hours_basis: "approx.",
  price_per_person: 250,
  price_basis: "checked",
  fee_per_group: 0,
  visit_minutes: 60,
  max_group: 6,
  min_age: 0,
  child_friendly: true,
  vegetarian: null,
  sources: [{ type: "overture", url: "https://example.org/a" }],
  source_groups: ["overture"],
  last_seen: "2026-11-20T00:00:00+00:00",
  state: "waiting",
  blockers: [] as string[],
  hints: ["Only one kind of source backs this place."],
  decided_at: null,
  note: "",
  maps_link: "https://www.google.com/maps/search/?api=1&query=11,76.95",
  embed: "about:blank",
  ...over,
});

test("the owner approves places one at a time, and blocked places can't be approved", async ({ page }) => {
  const decided: Record<string, unknown>[] = [];
  let items = [place("v1", "Brew Corner"), place("v2", "Shut Cafe", { blockers: ["marked closed"], state: "blocked" })];
  const counts = () => ({
    waiting: items.filter((i) => i.state === "waiting").length,
    changed: 0,
    blocked: items.filter((i) => i.state === "blocked").length,
    approved: decided.filter((d) => d.decision === "approve").length,
    rejected: 0,
  });
  await page.route("**/api/admin/publish/places*", (route: Route) =>
    route.fulfill({
      json: { counts: counts(), total_places: 2, categories: { cafe: items.length }, matching: items.length, items },
    }),
  );
  await page.route("**/api/admin/publish/decide", async (route: Route) => {
    const body = route.request().postDataJSON();
    decided.push(body);
    items = items.filter((i) => i.id !== body.venue_id);
    await route.fulfill({ json: { ...place(body.venue_id, "x"), state: "approved" } });
  });

  await page.goto("/admin");
  await page.getByRole("button", { name: "Approve places", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Brew Corner" })).toBeVisible();
  await expect(page.getByText("Every day 10am–10pm")).toBeVisible();
  await expect(page.getByText("checked", { exact: true })).toBeVisible();
  await expect(page.getByText("Only one kind of source backs this place.")).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("approve-places.png"), fullPage: true });

  await page.getByLabel("Note, kept with your decision (optional)").fill("went there");
  await page.getByRole("heading", { name: "Brew Corner" }).click();
  await page.keyboard.press("a");
  await expect.poll(() => decided.length).toBe(1);
  expect(decided[0]).toMatchObject({ venue_id: "v1", decision: "approve", note: "went there" });

  await expect(page.getByRole("heading", { name: "Shut Cafe" })).toBeVisible();
  await expect(page.getByText("marked closed")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Approve\s*A$/ })).toBeDisabled();
  await page.keyboard.press("a");
  await page.waitForTimeout(300);
  expect(decided).toHaveLength(1);
});
