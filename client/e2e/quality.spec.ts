// P7 checks: an axe-core accessibility pass on every product page in both themes, and flow 7 (the kiosk tour
// runs for two minutes without a console error).
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

import { BASE_URL, authFile } from './helpers';

const PAGES = [
  '/fleet',
  '/assets',
  '/assets/cmapss/unit_3',
  '/alarms',
  '/work-orders',
  '/cross-domain',
  '/chat',
  '/about/evidence',
  '/admin/cognition?domain=cmapss&machine=unit_3',
  '/admin/models',
  '/admin/onboarding',
  '/admin/devices',
  '/admin/users',
  '/admin/diagnostics',
];

for (const scheme of ['light', 'dark'] as const) {
  test(`axe: every page has no WCAG 2.2 A/AA violations (${scheme})`, async ({ browser }) => {
    test.setTimeout(240_000);
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: authFile('admin'), colorScheme: scheme });
    await context.addInitScript(t => {
      try {
        localStorage.setItem('dt-theme', t);
      } catch {
        /* storage blocked: the page follows the system scheme */
      }
    }, scheme);
    const page = await context.newPage();
    const found: string[] = [];
    for (const path of PAGES) {
      await page.goto(path);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      await page.waitForTimeout(2500); // let polled data and charts render
      const r = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
      for (const v of r.violations) found.push(`${path}: ${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0]?.target.join(' ')}`);
    }
    expect(found, found.join('\n')).toEqual([]);
    await context.close();
  });
}

test('7. kiosk tour runs for two minutes without a console error', async ({ browser }) => {
  test.setTimeout(200_000);
  const context = await browser.newContext({ baseURL: BASE_URL, storageState: authFile('viewer'), viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on('console', m => {
    if (m.type() === 'error') errors.push(m.text());
  });
  page.on('pageerror', e => errors.push(String(e)));
  const visited = new Set<string>();
  page.on('framenavigated', f => {
    if (f === page.mainFrame()) visited.add(new URL(f.url()).pathname);
  });
  await page.goto('/assets/kind/turbofan?kiosk=1');
  await page.waitForTimeout(120_000);
  expect(errors, errors.join('\n')).toEqual([]);
  expect(visited.size).toBeGreaterThanOrEqual(5); // 20 s per stop
  await context.close();
});

test('keyboard only: skip link, Ctrl K to Alarms, open an alarm with Enter, close with Escape', async ({ browser }) => {
  const context = await browser.newContext({ baseURL: BASE_URL, storageState: authFile('operator') });
  const page = await context.newPage();
  await page.goto('/fleet');
  await expect(page.getByRole('heading', { level: 1, name: 'Fleet overview' })).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Control+k');
  const palette = page.getByRole('dialog');
  await expect(palette).toBeVisible();
  await page.keyboard.type('alarms');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { level: 1, name: 'Alarms & events' })).toBeVisible();
  // Tab into the table until a row has focus, then open it
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press('Tab');
    if (await page.evaluate(() => document.activeElement?.tagName === 'TR')) break;
  }
  expect(await page.evaluate(() => document.activeElement?.tagName)).toBe('TR');
  await page.keyboard.press('Enter');
  const drawer = page.getByRole('dialog', { name: /^Alarm \d+/ });
  await expect(drawer).toBeVisible();
  await expect(page).toHaveURL(/alarm=\d+/);
  await page.keyboard.press('Escape');
  await expect(drawer).toBeHidden();
  await context.close();
});
