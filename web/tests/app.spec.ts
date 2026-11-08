import { test, expect, type Page } from "@playwright/test";

async function navigate(page: Page, label: string) {
  const mobile = page.getByRole("button", { name: "Open navigation" });
  if (await mobile.isVisible()) await mobile.click();
  await page.getByRole("link", { name: label, exact: true }).click();
}

test("plan, save, reload, record a visit and retain a private taste profile", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Your next good plan/ }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "What would you like to do?" })
    .fill("sushi");
  await page.getByRole("button", { name: "Find my plan", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A few good possibilities." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "See this plan" }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByRole("heading", { name: /Nori & Rice/, level: 2 }),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Save this plan", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Remove from saved" }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Close dialog" }).click();
  await navigate(page, "Saved for later");
  await expect(
    page.getByRole("heading", { name: "Your little collection." }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "See this plan" })).toHaveCount(
    1,
  );
  await page.reload();
  await expect(page.getByRole("button", { name: "See this plan" })).toHaveCount(
    1,
  );
  await navigate(page, "Explore places");
  await page.getByRole("textbox", { name: "Search places" }).fill("Nori");
  await page
    .getByRole("button", { name: "Explore Nori & Rice", exact: true })
    .click();
  await page.getByRole("tab", { name: "I visited" }).click();
  await page
    .getByLabel("What made it work, or not?")
    .fill("Loved the sushi and quiet atmosphere.");
  await page.getByRole("button", { name: "Record my visit" }).click();
  await expect(
    page.getByText(
      "Visit recorded. Your feedback will help future suggestions.",
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await navigate(page, "My taste");
  await expect(page.getByText("Leaning toward").first()).toBeVisible();
  await expect(
    page.getByText("Loved the sushi and quiet atmosphere."),
  ).toBeVisible();
  await page.getByLabel("What should we call you?").fill("Local Explorer");
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByText("Your preferences are saved.")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("What should we call you?")).toHaveValue(
    "Local Explorer",
  );
  expect(errors).toEqual([]);
});

test("source submission is queued and processed without fabricated video claims", async ({
  page,
}) => {
  await page.goto("/sources");
  await expect(
    page.getByRole("heading", { name: "Found something worth a look?" }),
  ).toBeVisible();
  await page
    .getByLabel("Caption or description")
    .fill("A quiet sushi spot in RS Puram. Sample caption for testing.");
  await page.getByRole("button", { name: "Add to analysis" }).click();
  await expect(
    page.getByText(
      "Added to your analysis queue. The worker will process it in the background.",
    ),
  ).toBeVisible();
  await navigate(page, "Operations");
  await page
    .getByRole("button", { name: "Background work", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Process next job", exact: true })
    .click();
  await expect(
    page.getByText("Action completed. The queue and records are up to date."),
  ).toBeVisible();
  await navigate(page, "From my feed");
  await page
    .getByRole("button", { name: /Shared text & media/ })
    .first()
    .click();
  await expect(
    page.getByText("No sentiment or reliability claim has been inferred"),
  ).toBeVisible({ timeout: 20000 });
});

test("mobile and desktop layout has no overflow or inaccessible unlabeled main inputs", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Find my plan", exact: true }),
  ).toBeVisible();
  const fits = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
  expect(fits).toBe(true);
  for (const card of await page.locator(".venue-card").all()) {
    expect(
      await card.evaluate((el) => {
        const content = el
          .querySelector(".venue-card-body")!
          .getBoundingClientRect();
        const bounds = el.getBoundingClientRect();
        return (
          content.bottom <= bounds.bottom + 1 &&
          content.right <= bounds.right + 1
        );
      }),
    ).toBe(true);
  }
  await page.screenshot({
    path: `test-results/discover-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Fine-tune my plan" }).click();
  await expect(page.getByLabel("Vegetarian options required")).toBeVisible();
  await page.getByLabel("Vegetarian options required").check();
  await page
    .getByRole("textbox", { name: "What would you like to do?" })
    .fill("sushi");
  await page.getByRole("spinbutton", { name: "Budget in rupees" }).fill("50");
  await page.getByRole("button", { name: "Find my plan", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Let’s adjust the plan." }),
  ).toBeVisible();
  await expect(page.getByText(/your budget was not changed/)).toBeVisible();
});
