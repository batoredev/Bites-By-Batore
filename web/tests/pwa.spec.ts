import { test, expect } from "@playwright/test";
test("PWA has install icons and keeps private API data out of offline storage", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Find my plan", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Find my plan", exact: true }),
  ).toBeVisible();
  const manifest = await (
    await page.request.get("/manifest.webmanifest")
  ).json();
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons.map((x: { sizes: string }) => x.sizes)).toEqual([
    "192x192",
    "512x512",
  ]);
  for (const icon of manifest.icons) {
    const r = await page.request.get(icon.src);
    expect(r.headers()["content-type"]).toContain("image/png");
  }
  const cached = await page.evaluate(async () => {
    const urls: string[] = [];
    for (const name of await caches.keys()) {
      for (const r of await (await caches.open(name)).keys()) urls.push(r.url);
    }
    return urls;
  });
  expect(cached.some((u) => new URL(u).pathname.startsWith("/api"))).toBe(
    false,
  );
  await context.setOffline(true);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Let’s reconnect." }),
  ).toBeVisible();
  await context.setOffline(false);
});
