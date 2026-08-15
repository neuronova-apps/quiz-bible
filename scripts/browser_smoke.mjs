import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const baseURL = process.env.SMOKE_BASE_URL || 'http://127.0.0.1:4173/';
const baseOrigin = new URL(baseURL).origin;
const artifactsDir = 'artifacts/smoke';
const viewports = [
  ['desktop-1440', 1440, 900],
  ['tablet-1024', 1024, 768],
  ['tablet-768', 768, 1024],
  ['mobile-390', 390, 844],
  ['mobile-360', 360, 800]
];
const isLocal = (value) => { try { return new URL(value).origin === baseOrigin; } catch { return false; } };
const browser = await chromium.launch({ headless: true });
const failures = [];
for (const [name, width, height] of viewports) {
  const context = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(`JavaScript runtime error: ${error.message}`));
  page.on('console', (message) => { if (message.type() === 'error') { const location = message.location(); if (!location.url || isLocal(location.url)) errors.push(`Console error: ${message.text()}`); } });
  page.on('requestfailed', (request) => { if (isLocal(request.url())) errors.push(`Local request failed: ${request.url()} (${request.failure()?.errorText || 'unknown error'})`); });
  page.on('response', (response) => { if (isLocal(response.url()) && response.status() >= 400) errors.push(`Local response ${response.status()}: ${response.url()}`); });
  try {
    const response = await page.goto(baseURL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    if (!response || response.status() >= 400) errors.push(`Homepage failed to load: HTTP ${response?.status() ?? 'no response'}`);
    await page.waitForTimeout(700);
    if (!(await page.title()).trim()) errors.push('Document title is empty.');
    for (const selector of ['header', 'main', 'h1', 'footer']) {
      const locator = page.locator(selector).first();
      if ((await locator.count()) === 0) errors.push(`Missing essential element: ${selector}`);
      else if (!(await locator.isVisible())) errors.push(`Essential element is not visible: ${selector}`);
    }
    const layout = await page.evaluate(() => {
      const root = document.documentElement;
      const oldBehavior = root.style.scrollBehavior;
      root.style.scrollBehavior = 'auto';
      const y = window.scrollY;
      window.scrollTo(100000, y);
      const reachableScrollX = Math.round(window.scrollX);
      window.scrollTo(0, y);
      root.style.scrollBehavior = oldBehavior;
      const controls = [...document.querySelectorAll('header a, header button')]
        .filter((element) => { const style = getComputedStyle(element); const rect = element.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0; })
        .map((element) => { const rect = element.getBoundingClientRect(); return { label: (element.getAttribute('aria-label') || element.textContent || element.tagName).trim().replace(/\s+/g, ' ').slice(0, 80), left: Math.round(rect.left), right: Math.round(rect.right) }; })
        .filter((item) => item.left < -2 || item.right > window.innerWidth + 2);
      return { reachableScrollX, controls };
    });
    if (layout.reachableScrollX > 2) errors.push(`Page can scroll horizontally by ${layout.reachableScrollX}px.`);
    layout.controls.forEach((control) => errors.push(`Header control outside viewport: "${control.label}" [${control.left}, ${control.right}] within ${width}px.`));
    if (width <= 900) {
      const menuButton = page.locator('header .menu-button, header .menu').first();
      const nav = page.locator('header .main-nav').first();
      if ((await menuButton.count()) > 0 && (await menuButton.isVisible()) && (await nav.count()) > 0) {
        await menuButton.click();
        if ((await menuButton.getAttribute('aria-expanded')) !== 'true') errors.push('Mobile menu button did not set aria-expanded="true".');
        if (!(await nav.isVisible())) errors.push('Mobile navigation did not become visible after opening the menu.');
        else { const box = await nav.boundingBox(); if (box && (box.x < -2 || box.x + box.width > width + 2)) errors.push('Open mobile navigation extends outside the viewport.'); }
      }
    }
  } catch (error) { errors.push(`Smoke test exception: ${error.message}`); }
  if (errors.length) {
    await mkdir(artifactsDir, { recursive: true });
    await page.screenshot({ path: `${artifactsDir}/${name}.png`, fullPage: true }).catch(() => {});
    failures.push({ name, errors });
    console.error(`\n✗ ${name}`); errors.forEach((error) => console.error(`  - ${error}`));
  } else console.log(`✓ ${name} (${width}×${height})`);
  await context.close();
}
await browser.close();
if (failures.length) { console.error(`\n${failures.length} viewport(s) failed responsive smoke checks.`); process.exit(1); }
console.log(`\nAll ${viewports.length} responsive smoke checks passed.`);
