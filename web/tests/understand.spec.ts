import { test, expect } from "@playwright/test";

// The request box reads the person's words with Bites' own model (real model, throwaway DB),
// fills the form, shows what it understood, and lets the person remove any of it.

test("typing a request fills the form and explains what was understood", async ({ page }) => {
  await page.goto("/");
  const box = page.getByLabel("What would you like to do?");
  await box.fill("biryani for 4, 800 per head, tonight");

  const chips = page.getByRole("list", { name: "What Bites understood" });
  await expect(chips.getByText("4 people")).toBeVisible();
  await expect(chips.getByText("₹800 per person")).toBeVisible();
  await expect(chips.getByText("Evening")).toBeVisible();
  await expect(chips.getByText("biryani")).toBeVisible();
  await page.locator(".planner-form").screenshot({ path: test.info().outputPath("understood.png") });
  const people = page.getByRole("spinbutton", { name: "People", exact: true });
  await expect(people).toHaveValue("4");
  await expect(page.getByLabel("Budget in rupees")).toHaveValue("800");
  await expect(page.getByLabel("Budget applies to")).toHaveValue("person");

  // Removing a chip puts the field back the way it was.
  await page.getByRole("button", { name: "Remove 4 people" }).click();
  await expect(people).toHaveValue("2");
  await expect(chips.getByText("4 people")).toHaveCount(0);

  // A field the person sets by hand stays theirs when they keep typing.
  await page.getByLabel("Budget in rupees").fill("1200");
  await box.fill("biryani for 4, 800 per head, tonight, near Peelamedu");
  await expect(chips.getByText("From Peelamedu").or(page.getByText(/couldn't place Peelamedu/))).toBeVisible();
  await expect(page.getByLabel("Budget in rupees")).toHaveValue("1200");
});

test("an out of scope request is told so before planning", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("What would you like to do?").fill("plan a weekend trip to Ooty");
  await expect(page.getByText(/plans food and outings inside Coimbatore/)).toBeVisible();
});
