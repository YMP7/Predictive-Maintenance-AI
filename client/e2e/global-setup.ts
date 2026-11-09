// Flow 1, part one: each role signs in through the form once. The sessions are saved and reused, because
// the API allows 5 sign-in attempts a minute per address (a security control the tests must not loosen).
import { chromium, type FullConfig } from '@playwright/test';

import { authFile, signIn, type Role } from './helpers';

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL;
  const browser = await chromium.launch();
  for (const role of ['admin', 'operator', 'viewer'] as Role[]) {
    const context = await browser.newContext({ baseURL });
    await signIn(await context.newPage(), role);
    await context.storageState({ path: authFile(role) });
    await context.close();
  }
  await browser.close();
}
