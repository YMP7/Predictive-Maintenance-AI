import { expect, type APIRequestContext, type Browser, type Page } from '@playwright/test';

export type Role = 'admin' | 'operator' | 'viewer';

export const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';

// The seeded test accounts; their passwords are public by design (scripts/seed_dev.py, SECURITY.md).
const ACCOUNTS: Record<Role, { user: string; password: string }> = {
  admin: { user: process.env.E2E_ADMIN_USER ?? 'test_admin', password: process.env.E2E_ADMIN_PASSWORD ?? 'test_admin_public_pw_123' },
  operator: { user: process.env.E2E_OPERATOR_USER ?? 'test_operator', password: process.env.E2E_OPERATOR_PASSWORD ?? 'test_operator_public_pw_123' },
  viewer: { user: process.env.E2E_VIEWER_USER ?? 'demo_viewer', password: process.env.E2E_VIEWER_PASSWORD ?? 'demo_viewer_public_pw_123' },
};

export const H = { 'X-API-Request': 'true' };

/** Sign in through the form, as a person would. Lands on the fleet overview. */
export async function signIn(page: Page, role: Role) {
  const a = ACCOUNTS[role];
  await page.goto('/login');
  await page.getByLabel('Username').fill(a.user);
  await page.getByLabel('Password', { exact: true }).fill(a.password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/fleet$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Fleet overview' })).toBeVisible();
  return a.user;
}

/** API calls with the page's session cookie. */
export const api = (page: Page): APIRequestContext => page.request;

/** Where global-setup saves each role's session (gitignored). */
export const authFile = (role: Role) => `e2e/.auth/${role}.json`;

/** A page already signed in as `role`, from the session global-setup saved. */
export async function pageAs(browser: Browser, role: Role): Promise<Page> {
  const context = await browser.newContext({ baseURL: BASE_URL, storageState: authFile(role) });
  return context.newPage();
}
