import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function navigate(page: Page, label: string) {
  const menu = page.getByRole("button", { name: "Open navigation" });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("link", { name: label, exact: true }).click();
}
test.beforeEach(async ({ request }) => {
  const config = await (await request.get("/api/config")).json();
  test.skip(
    config.mode !== "demo",
    "Mutation tests require the isolated demo database, never the real inventory",
  );
});

test("reviewed dish search, private wishlist and reversible dish feedback persist", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/places");
  await page.getByRole("textbox", { name: "Search places" }).fill("miso");
  await expect(
    page.getByRole("button", { name: "Explore Nori & Rice", exact: true }),
  ).toHaveCount(1);
  await page
    .getByRole("button", { name: "Explore Nori & Rice", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: "Menu & dishes", exact: true }).click();
  await expect(
    dialog.getByRole("heading", { name: "Menu and dish suggestions" }),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Save Avocado maki to try", exact: true })
    .click();
  await expect(
    dialog.getByRole("status").filter({ hasText: "does not record a visit" }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Close dialog" }).click();
  await navigate(page, "My taste");
  await expect(
    page.getByRole("heading", { name: "Your private dish diary" }),
  ).toBeVisible();
  await expect(
    page.getByText("Nori & Rice · Want to try", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Your story starts with a visit" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Nori & Rice · Want to try", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit dish", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Your experience", exact: true })
    .selectOption("favourite");
  await page
    .getByLabel("Your private note")
    .fill("A favourite fixture dish for this private diary.");
  await page.getByRole("button", { name: "Update dish experience" }).click();
  await expect(
    page.getByText("A favourite fixture dish for this private diary.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("Leaning toward").first()).toBeVisible();
  await page.getByRole("button", { name: "Remove dish", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "No dishes in this collection" }),
  ).toBeVisible();
  await expect(page.getByText("Leaning toward")).toHaveCount(0);
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);
  expect(errors).toEqual([]);
});

test("reviewed filters exclude unknown amenities and preserve dish versus outing prices", async ({
  page,
}) => {
  await page.goto("/places");
  await page
    .getByText("Filter by cuisine, area and practical details", { exact: true })
    .click();
  await page.getByLabel("Cuisine", { exact: true }).fill("Japanese");
  await page.getByLabel("Maximum listed dish price (INR)").fill("150");
  await page.getByLabel("Reviewed vegetarian dish required").check();
  await expect(
    page.getByRole("button", { name: "Explore Nori & Rice", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Confirmed parking").check();
  await expect(
    page.getByRole("heading", { name: "Nothing here yet" }),
  ).toBeVisible();
  await page.getByLabel("Confirmed parking").uncheck();
  await page.getByLabel("Confirmed washroom").check();
  await expect(
    page.getByRole("button", { name: "Explore Nori & Rice", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Explore Nori & Rice", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: "Menu & dishes", exact: true }).click();
  await expect(dialog.getByText("₹120 / item", { exact: true })).toBeVisible();
  await expect(
    dialog.getByText(/Menu item and package prices are separate/),
  ).toBeVisible();
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("quiet and unfamiliar preferences remain independent of group and budget inputs", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "What would you like to do?" })
    .fill("quiet food");
  await page
    .getByRole("button", { name: "Not sure? Help me decide.", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Something outside my usual choices",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Use this direction", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Slow & quiet", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByLabel("How different should it feel?")).toHaveValue(
    "new_taste",
  );
  // Existing labelled controls keep the hard planning inputs in their own fields.
  const before = await page
    .locator(".planner-form")
    .evaluate((form) =>
      Array.from(form.querySelectorAll("input[type=number]")).map(
        (e) => (e as HTMLInputElement).value,
      ),
    );
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/api/plans") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Find my plan", exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  const request = result.request().postDataJSON();
  expect(request.mood).toBe("quiet");
  expect(request.novelty).toBe("new_taste");
  expect(request.party_size).toBe(2);
  expect(request.budget).toBe(2400);
  for (const option of (await result.json()).options) {
    expect(option.result.total_cost).toBeLessThanOrEqual(2400);
    expect(option.result.total_minutes).toBeLessThanOrEqual(
      request.duration_minutes,
    );
  }
  expect(
    await page
      .locator(".planner-form")
      .evaluate((form) =>
        Array.from(form.querySelectorAll("input[type=number]")).map(
          (e) => (e as HTMLInputElement).value,
        ),
      ),
  ).toEqual(before);
});

test("editing and deleting a visit reverses its private learning contribution", async ({
  page,
}) => {
  await page.goto("/places");
  await page.getByRole("textbox", { name: "Search places" }).fill("Nori");
  await page
    .getByRole("button", { name: "Explore Nori & Rice", exact: true })
    .click();
  await page.getByRole("tab", { name: "I visited", exact: true }).click();
  await page
    .getByLabel("What made it work, or not?")
    .fill("A real form flow in the isolated fixture database.");
  await page
    .getByRole("button", { name: "Record my visit", exact: true })
    .click();
  await expect(
    page.getByText(
      "Visit recorded. Your feedback will help future suggestions.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await navigate(page, "My taste");
  await page.getByRole("button", { name: "Edit visit", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Food score", exact: true })
    .selectOption("1");
  await page
    .getByRole("textbox", { name: "Your visit note", exact: true })
    .fill("Corrected the earlier food score.");
  await page.getByRole("button", { name: "Update visit", exact: true }).click();
  await expect(
    page.getByText("Corrected the earlier food score.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Delete visit", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your story starts with a visit" }),
  ).toBeVisible();
  await expect(page.getByText("Leaning toward")).toHaveCount(0);
});

test("review samples show both praise and complaints with source links", async ({
  page,
}) => {
  await page.route(/\/api\/venues(?:\?.*)?$/, async (route) => {
    const response = await route.fetch();
    const venues = await response.json();
    const venue = venues.find(
      (item: { id: string }) => item.id === "demo-sushi",
    );
    if (!venue) {
      await route.fulfill({ json: venues });
      return;
    }
    const at = new Date(Date.now() - 3600000).toISOString();
    const expiry = new Date(Date.now() + 86400000).toISOString();
    venue.menu.items[0].review_support = {
      groups: 2,
      counts: { praise: 1, complaint: 1, mixed: 0, mention: 0 },
      basis: "Isolated UI fixture; bounded reviewed source groups",
      sources: [
        {
          sentiment: "praise",
          sources: [
            {
              url: "https://fixture.invalid/praise",
              observed_at: at,
              expires_at: expiry,
            },
          ],
        },
        {
          sentiment: "complaint",
          sources: [
            {
              url: "https://fixture.invalid/complaint",
              observed_at: at,
              expires_at: expiry,
            },
          ],
        },
      ],
    };
    await route.fulfill({ json: venues });
  });
  await page.goto("/places");
  await page.getByRole("textbox", { name: "Search places" }).fill("Nori");
  await page
    .getByRole("button", { name: "Explore Nori & Rice", exact: true })
    .click();
  await page.getByRole("tab", { name: "Menu & dishes", exact: true }).click();
  await page
    .getByText("Reviewed review evidence (2 groups)", { exact: true })
    .click();
  await expect(page.getByText("praise", { exact: true })).toBeVisible();
  await expect(page.getByText("complaint", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Source evidence", exact: true }),
  ).toHaveCount(2);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(result.violations.map((v) => v.id)).toEqual([]);
});
