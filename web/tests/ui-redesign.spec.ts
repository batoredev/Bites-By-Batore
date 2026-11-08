import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ request }) => {
  test.skip(
    (await (await request.get("/api/config")).json()).mode !== "demo",
    "Use the isolated UI review database",
  );
});

test("mobile navigation traps focus, closes with Escape and restores focus", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Find my plan", exact: true }),
  ).toBeVisible();
  const trigger = page.getByRole("button", { name: "Open navigation" });
  test.skip(!(await trigger.isVisible()), "Mobile navigation only");
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
  await trigger.click();
  const menu = page.getByRole("dialog", { name: "Main menu" });
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("button", { name: "Close menu" })).toBeFocused();
  const first = menu.locator("a[href]").first();
  await first.focus();
  await page.keyboard.press("Shift+Tab");
  await expect(
    menu.getByRole("button", { name: "Start a new demo account" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(first).toBeFocused();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(
    audit.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(menu).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole("link", { name: "Explore places", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Good places. More possibilities." }),
  ).toBeVisible();
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
});

test("venue tabs support keyboard navigation and expose a dedicated menu panel", async ({
  page,
}) => {
  await page.goto("/places");
  await page.getByRole("textbox", { name: "Search places" }).fill("Nori");
  const opener = page.getByRole("button", {
    name: "Explore Nori & Rice",
    exact: true,
  });
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "Nori & Rice" });
  const about = dialog.getByRole("tab", { name: "The place", exact: true });
  await about.focus();
  await page.keyboard.press("ArrowRight");
  const menu = dialog.getByRole("tab", { name: "Menu & dishes", exact: true });
  await expect(menu).toBeFocused();
  await expect(menu).toHaveAttribute("aria-selected", "true");
  await expect(dialog.getByRole("tabpanel")).toHaveAccessibleName(
    "Menu & dishes",
  );
  await expect(
    dialog.getByRole("heading", { name: "Avocado maki", exact: true }),
  ).toBeVisible();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(
    audit.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.keyboard.press("End");
  await expect(
    dialog.getByRole("tab", { name: "Report a change" }),
  ).toBeFocused();
  await page.keyboard.press("Home");
  await expect(about).toBeFocused();
  await expect(menu).toHaveAttribute("tabindex", "-1");
  await page.keyboard.press("Escape");
  await expect(opener).toBeFocused();
});

test("failed searches have a retry state and do not claim an empty inventory", async ({
  page,
}) => {
  let failed = false;
  await page.route(/\/api\/venues\?.*q=miso/, async (route) => {
    if (!failed) {
      failed = true;
      await route.fulfill({
        status: 503,
        json: { detail: "Temporary search failure" },
      });
    } else await route.continue();
  });
  await page.goto("/places");
  await page.getByRole("textbox", { name: "Search places" }).fill("miso");
  await expect(page.getByRole("alert")).toHaveText("Temporary search failure");
  await expect(
    page.getByRole("heading", { name: "Nothing here yet" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Retry search" }).click();
  await expect(
    page.getByRole("button", { name: "Explore Nori & Rice", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("taste shortcuts lead directly to diary and history", async ({ page }) => {
  await page.goto("/taste");
  const shortcuts = page.getByRole("navigation", { name: "Taste sections" });
  await shortcuts
    .getByRole("link", { name: "Dish diary", exact: true })
    .click();
  await expect(page).toHaveURL(/#dish-diary$/);
  expect(
    await page
      .locator("#dish-diary")
      .evaluate((el) => el.getBoundingClientRect().top),
  ).toBeGreaterThanOrEqual(0);
  await shortcuts
    .getByRole("link", { name: "Visit history", exact: true })
    .click();
  await expect(page).toHaveURL(/#visit-history$/);
  await expect(
    page.getByRole("heading", { name: "Your story starts with a visit" }),
  ).toBeVisible();
});

test("all screens fit phone, tablet and desktop widths", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Width matrix is run once");
  test.setTimeout(120000);
  for (const width of [360, 600, 768, 900, 1024, 1440]) {
    await page.setViewportSize({ width, height: 940 });
    for (const route of ["/", "/places", "/taste", "/sources", "/admin"]) {
      await page.goto(route);
      await expect(page.locator("main h1")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `${width}px ${route}`,
      ).toBe(true);
      const main = await page.locator("main").boundingBox();
      expect(main!.x).toBeGreaterThanOrEqual(0);
      expect(main!.x + main!.width).toBeLessThanOrEqual(width + 1);
    }
  }
});
