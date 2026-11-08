import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const base = process.env.BATORE_UI_BASE_URL || "http://127.0.0.1:8001";
const stage = process.argv[2] || "after";
const folder = resolve("../data/ui-redesign", stage);
await mkdir(folder, { recursive: true });
const config = await (await fetch(`${base}/api/config`)).json();
if (config.mode !== "demo")
  throw new Error("UI review requires a separate demo instance");
const browser = await chromium.launch();
const report = [];
try {
  for (const width of [390, 1440]) {
    const context = await browser.newContext({
      viewport: { width, height: width < 600 ? 844 : 1000 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const route of [
      "/",
      "/places",
      "/saved",
      "/taste",
      "/sources",
      "/admin",
    ]) {
      await page.goto(`${base}${route}`);
      await page.locator("main h1").waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(250);
      const measurements = await page.evaluate(() => ({
        viewport: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        overflow: [...document.querySelectorAll("main *")]
          .filter((el) => {
            const rect = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            return (
              rect.width > 0 &&
              style.visibility !== "hidden" &&
              rect.right > innerWidth + 2
            );
          })
          .slice(0, 12)
          .map((el) => ({
            tag: el.tagName,
            className: el.className,
            text: el.textContent?.slice(0, 65),
          })),
      }));
      const name = route === "/" ? "discover" : route.slice(1);
      await page.screenshot({
        path: resolve(folder, `${name}-${width}.png`),
        fullPage: true,
      });
      if (route === "/places") {
        const card = page.locator(".venue-card").first();
        if (await card.count())
          await card.screenshot({
            path: resolve(folder, `place-card-${width}.png`),
          });
      }
      report.push({ route, width, ...measurements, errors: [...errors] });
    }
    await page.goto(`${base}/places`);
    await page.getByRole("textbox", { name: "Search places" }).fill("Nori");
    await page
      .getByRole("button", { name: "Explore Nori & Rice", exact: true })
      .click();
    await page.getByRole("tab", { name: "Menu & dishes", exact: true }).click();
    await page
      .getByRole("dialog", { name: "Nori & Rice" })
      .screenshot({ path: resolve(folder, `menu-${width}.png`) });
    await page.getByRole("button", { name: "Close dialog" }).click();
    await page.goto(base);
    await page
      .getByRole("textbox", { name: "What would you like to do?" })
      .fill("sushi");
    await page
      .getByRole("button", { name: "Find my plan", exact: true })
      .click();
    await page.getByRole("button", { name: "See this plan" }).first().click();
    await page
      .getByRole("dialog")
      .screenshot({ path: resolve(folder, `plan-${width}.png`) });
    await context.close();
  }
} finally {
  await browser.close();
}
await writeFile(resolve(folder, "audit.json"), JSON.stringify(report, null, 2));
console.log(
  JSON.stringify(
    report.map(({ route, width, scrollWidth, errors }) => ({
      route,
      width,
      scrollWidth,
      errors,
    })),
    null,
    2,
  ),
);
