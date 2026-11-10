import { defineConfig, devices } from '@playwright/test';

import { BASE_URL } from './e2e/helpers';

// End-to-end flows against a running stack: the Vite dev server (proxying /api to the API) and the API itself.
//   npm run dev                      (ATLAS_API_TARGET picks the API; default http://localhost:8000)
//   npx playwright test
// Accounts come from scripts/seed_dev.py (test_admin, test_operator, demo_viewer); override with E2E_* variables.
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        // Render WebGL on the GPU as a real browser does; headless software rendering starves the main thread.
        launchOptions: { args: [...(process.platform === 'win32' ? ['--use-angle=d3d11'] : []), '--ignore-gpu-blocklist', '--enable-gpu-rasterization'] },
      },
    },
  ],
});
