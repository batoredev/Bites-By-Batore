import { test, expect } from "@playwright/test";

test("directory leads show attribution and coverage gaps without claiming verification", async ({
  page,
}) => {
  await page.route("**/api/admin/city-collection", (route) =>
    route.fulfill({
      json: {
        active_drafts: 1,
        directory_linked: 1,
        missing_menu_or_price: 1,
        missing_hours_observation: 0,
        missing_vibes: 1,
        maps_unreviewed: 1,
        queries_scheduled: 2,
        discovery_queries: 168,
      },
    }),
  );
  await page.route("**/api/admin/spots?*", (route) =>
    route.fulfill({
      json: {
        held: 0,
        spots: [
          {
            id: "directory-fixture",
            name: "Zircon Cafe",
            category: "cafe",
            area: "",
            status: "identified",
            venue_id: "",
            missing: ["Maps confirmation"],
            map_search_url:
              "https://www.google.com/maps/search/?api=1&query=fixture",
            data: {
              source_licenses: [
                {
                  attribution: "© OpenStreetMap contributors",
                  url: "https://www.openstreetmap.org/copyright",
                  license: "ODbL 1.0",
                },
              ],
              hours_candidates: [
                {
                  value: "Mo-Fr 10:00-18:00",
                  basis: "OSM raw tag; current hours unverified",
                  source_url: "https://www.openstreetmap.org/node/1",
                },
              ],
            },
          },
        ],
      },
    }),
  );
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Identified spots", exact: true })
    .click();
  await expect(page.getByLabel("Coimbatore collection coverage")).toContainText(
    "City-wide completeness and accuracy are unverified",
  );
  await expect(
    page.getByRole("link", { name: "© OpenStreetMap contributors · ODbL 1.0" }),
  ).toHaveAttribute("href", "https://www.openstreetmap.org/copyright");
  await expect(
    page.getByText("Extracted name — Maps identity unconfirmed"),
  ).toBeVisible();
  await expect(
    page.getByText(/Unverified hours observation: Mo-Fr/),
  ).toBeVisible();
  await expect(page.getByText("Opening hours unknown.")).toBeVisible();
});
