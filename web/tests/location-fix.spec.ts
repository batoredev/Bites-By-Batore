import { test, expect, type Route } from "@playwright/test";

// "Wrong location?" in Quick review and Approve places: the owner pastes the right Maps
// link or coordinates. The API is faked; the backend has its own tests for the checks.

const week = Object.fromEntries([0, 1, 2, 3, 4, 5, 6].map((d) => [String(d), [[600, 1320]]]));
const place = {
  id: "v1", name: "Brew Corner", category: "cafe", area: "RS Puram", address: "", lat: 11.0, lng: 76.9,
  tags: [], hours: week, hours_basis: "approx.", price_per_person: 250, price_basis: "approx.",
  fee_per_group: 0, visit_minutes: 60, max_group: 6, min_age: 0, child_friendly: true, vegetarian: null,
  sources: [], source_groups: ["overture"], last_seen: null, spot_id: "s1", state: "approved",
  blockers: [], hints: [], decided_at: null, note: "", maps_link: "https://www.google.com/maps?q=11,76.9",
  embed: "about:blank",
};

test("approve places: fix a wrong location and get told to re-approve", async ({ page }) => {
  let sent: unknown = null;
  await page.route("**/api/admin/publish/places*", (route: Route) =>
    route.fulfill({
      json: { counts: { waiting: 0, changed: 0, blocked: 0, approved: 1, rejected: 0 }, total_places: 1,
              categories: { cafe: 1 }, matching: 1, items: [sent ? { ...place, state: "changed" } : place] },
    }),
  );
  await page.route("**/api/admin/spots/s1/edit", async (route: Route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: { id: "s1" } });
  });
  await page.goto("/admin");
  await page.getByRole("button", { name: "Approve places", exact: true }).click();
  await page.getByRole("button", { name: "Wrong location?" }).click();
  await page.getByLabel("Paste the right place from Google Maps").fill("https://maps.app.goo.gl/AbC123");
  await page.getByRole("button", { name: "Save location" }).click();
  await expect(page.getByText(/approve it again with the new one/)).toBeVisible();
  expect(sent).toEqual({ maps_url: "https://maps.app.goo.gl/AbC123" });
});

test("quick review: fix a wrong location on the row", async ({ page }) => {
  const item = {
    sheet: "live", row: 0, title: "Brew Corner", question: "Is this live place real, open and right?",
    claim: "Customers can see this as a cafe in RS Puram.", answer: "", note: "", options: ["yes", "no", "closed"],
    maps_link: "https://www.google.com/maps?q=11,76.9", embed: "about:blank", other: "", hints: [], links: [],
    matches: [{ id: "s1", name: "Brew Corner", area: "RS Puram", category: "cafe", status: "approved",
                coords: [11.0, 76.9], address: "", sources: ["overture"], corroboration: "", websites: [],
                search: [], notes: [], taught: false }],
  };
  let sent: Record<string, unknown> | null = null;
  await page.route("**/api/admin/review-desk/items", (route: Route) =>
    route.fulfill({ json: { items: [item], total: 1, done: 0 } }),
  );
  await page.route("**/api/admin/review-desk/location", async (route: Route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: { ...item, note: "Location corrected by owner" } });
  });
  await page.goto("/admin");
  await page.getByRole("button", { name: "Quick review", exact: true }).click();
  await page.getByRole("button", { name: "Wrong location?" }).click();
  await page.getByLabel("Paste the right place from Google Maps").fill("11.0203, 76.9612");
  await page.getByRole("button", { name: "Save location" }).click();
  await expect(page.getByText("Location corrected by owner")).toBeVisible();
  expect(sent).toEqual({ sheet: "live", row: 0, spot_id: "s1", maps_url: "11.0203, 76.9612" });
});
