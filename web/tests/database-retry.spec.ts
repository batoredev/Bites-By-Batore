import { test, expect } from "@playwright/test";

test("a temporary database conflict retries a read and displays the saved inventory", async ({
  page,
}) => {
  let reads = 0;
  await page.route("**/api/admin/spots?*", (route) => {
    reads++;
    return reads === 1
      ? route.fulfill({
          status: 503,
          headers: { "Retry-After": "1" },
          json: {
            detail: "Local data updates are busy. Please retry shortly.",
          },
        })
      : route.fulfill({ json: { spots: [], held: 0 } });
  });
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Identified spots", exact: true })
    .click();
  await expect(
    page.getByText("0 identified locations · drafts are not recommendations"),
  ).toBeVisible();
  expect(reads).toBe(2);
});

test("a temporary database conflict never repeats a mutation automatically", async ({
  page,
}) => {
  let writes = 0;
  await page.route("**/api/admin/spots?*", (route) =>
    route.fulfill({ json: { spots: [], held: 0 } }),
  );
  await page.route("**/api/admin/spots/collect", (route) => {
    writes++;
    return route.fulfill({
      status: 503,
      headers: { "Retry-After": "1" },
      json: { detail: "Local data updates are busy. Please retry shortly." },
    });
  });
  await page.goto("/admin");
  await page
    .getByRole("button", { name: "Identified spots", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Collect official menus and details",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("Local data updates are busy. Please retry shortly.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(writes).toBe(1);
});
