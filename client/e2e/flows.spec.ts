// Playwright flows from the redesign brief §4: 1 login per role, 2 onboarding wizard, 3 push data and
// see it live within 2 s, 4 alarm -> acknowledge -> work order -> approve, 5 Cognition replay, 6 operator cannot see Cognition.
// Flow 5 (Cognition replay) arrived in P5; flow 7 (2-minute kiosk tour) arrives with P7.
import { execFileSync } from 'node:child_process';

import { expect, test, type Page } from '@playwright/test';

import { api, H, pageAs, type Role } from './helpers';

const ADMIN_ONLY = ['Cognition', 'Sensor onboarding', 'Devices', 'Users & roles', 'Diagnostics'];

test.describe('1. Sign in per role', () => {
  const expected: Record<Role, { sees: string[]; hidden: string[] }> = {
    admin: { sees: ['Fleet overview', 'Agent chat', ...ADMIN_ONLY], hidden: [] },
    operator: { sees: ['Fleet overview', 'Alarms & events', 'Agent chat'], hidden: ADMIN_ONLY },
    viewer: { sees: ['Fleet overview', 'Work orders'], hidden: ['Agent chat', ...ADMIN_ONLY] },
  };
  for (const role of ['admin', 'operator', 'viewer'] as Role[]) {
    test(role, async ({ browser }) => {
      // the form sign-in itself ran in global-setup; this checks what the signed-in role sees
      const page = await pageAs(browser, role);
      await page.goto('/fleet');
      const user = { admin: 'test_admin', operator: 'test_operator', viewer: 'demo_viewer' }[role];
      const rail = page.getByRole('complementary', { name: 'Main' });
      for (const name of expected[role].sees) await expect(rail.getByRole('link', { name })).toBeVisible();
      for (const name of expected[role].hidden) await expect(rail.getByRole('link', { name })).toHaveCount(0);
      await expect(page.getByRole('banner')).toContainText(user);
      await page.getByRole('button', { name: 'Sign out' }).click();
      await expect(page).toHaveURL(/\/login/);
    });
  }

  test('wrong password is refused with a plain message', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Username').fill('test_operator');
    await page.getByLabel('Password', { exact: true }).fill('not-the-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByRole('alert')).toHaveText('Wrong username or password.');
  });
});

test.describe.serial('2-3. Onboard a sensor, then push data and see it live', () => {
  const id = `e2e_pump_${Date.now().toString(36)}`;
  let token = '';

  test('2. onboard through the wizard', async ({ browser }) => {
    const page = await pageAs(browser, 'admin');
    await page.goto('/admin/onboarding');
    await page.getByLabel('Asset id').fill(id);
    await page.getByLabel('Display name').fill('E2E cooling water pump');
    await page.getByRole('button', { name: /^Next: Domain and profile/ }).click();

    await page.getByLabel('Machine type').selectOption('modbus');
    await page.getByLabel(/Data comes from a simulator/).check();
    await page.getByRole('button', { name: 'Load the register map for this machine type' }).click();
    await page.getByRole('button', { name: /^Next: Protocol/ }).click();

    await page.getByRole('radio', { name: 'HTTP push' }).click();
    await expect(page.locator('.ax-code')).toContainText(`/api/ingest/${id}`);
    await page.getByRole('button', { name: /^Next: Map channels/ }).click();

    await expect(page.getByLabel('Device sends, row 1')).toHaveValue('temperature_c');
    await page.getByRole('button', { name: /^Next: Live preview/ }).click();

    await page.getByRole('button', { name: 'Save profile and open preview' }).click();
    await expect(page.getByText('Profile saved')).toBeVisible();
    await expect(page.getByText('Connected', { exact: true }).last()).toBeVisible();
    await page.getByLabel('temperature_c (raw)').fill('55.5');
    await page.getByRole('button', { name: 'Send test sample' }).click();
    await expect(page.getByText(/1 points accepted, 0 rejected/)).toBeVisible();
    // the validated sample comes back over the live stream
    await expect(page.locator('ul[aria-live="polite"] li').first()).toContainText('temperature_c');

    await page.getByRole('button', { name: /^Next: Bind to 3D parts/ }).click();
    await expect(page.getByLabel('3D part for vibration_mms')).toHaveValue('bearing_de');
    await page.getByRole('button', { name: /^Next: Activate/ }).click();
    await page.getByRole('button', { name: 'Activate and issue token' }).click();

    const dialog = page.getByRole('dialog', { name: 'Device token' });
    await expect(dialog).toBeVisible();
    token = (await dialog.locator('code').first().textContent())?.trim() ?? '';
    expect(token.length).toBeGreaterThan(20);
    await dialog.getByRole('button', { name: 'I have copied it' }).click();
    await expect(page.getByText(/is active/)).toBeVisible();
  });

  test('3. HTTP push shows in Asset Detail and the 3D view within 2 s', async ({ browser }) => {
    test.skip(!token, 'needs the token from flow 2');
    const page = await pageAs(browser, 'operator');
    await page.goto(`/assets/modbus/${id}`);
    await expect(page.getByRole('heading', { level: 1, name: id })).toBeVisible();
    await page.getByRole('button', { name: /Front bearing/ }).click();

    const sent = Date.now();
    const res = await api(page).post(`/api/ingest/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { values: { vibration_mms: 9.4, temperature_c: 61.5, current_a: 12.2, speed_rpm: 1460 } },
    });
    expect(res.status()).toBe(200);
    // the part's live value in the side panel and the callout in the 3D stage, both within 2 s of the push
    await expect(page.locator('.ax-asset__detail')).toContainText('9.40', { timeout: 2000 });
    const panel = Date.now() - sent;
    await expect(page.locator('.ax-stage__callout')).toContainText('9.40', { timeout: Math.max(1, 2000 - panel) });
    console.log(`push to screen: side panel ${panel} ms, 3D callout ${Date.now() - sent} ms`);
  });

  test('3b. MQTT push shows in Asset Detail within 2 s', async ({ browser }) => {
    // Broker accounts are per device (mosquitto/config); onboarding does not create them.
    // Set E2E_MQTT_USER / E2E_MQTT_PASSWORD / E2E_MQTT_MACHINE for a profiled machine the account may publish for.
    const user = process.env.E2E_MQTT_USER;
    const password = process.env.E2E_MQTT_PASSWORD;
    const machine = process.env.E2E_MQTT_MACHINE;
    test.skip(!user || !password || !machine, 'no broker account for a profiled machine (E2E_MQTT_* not set)');
    const page = await pageAs(browser, 'operator');
    await page.goto(`/assets/modbus/${machine}`);
    await page.getByRole('button', { name: /Front bearing/ }).click();
    execFileSync('docker', ['exec', 'mosquitto', 'mosquitto_pub', '-u', user!, '-P', password!, '-t', `factory/${machine}/telemetry`, '-m', JSON.stringify({ values: { vibration_mms: 7.77 } })]);
    await expect(page.locator('.ax-asset__detail')).toContainText('7.77', { timeout: 2000 });
  });
});

async function raiseAlarm(page: Page): Promise<number> {
  // A real alarm from the pipeline: inject a fault into the simulator and run it until an alarm appears.
  const r = api(page);
  const newest = async () => ((await (await r.get('/api/alarms?limit=1', { headers: H })).json()).alarms[0]?.id ?? 0) as number;
  const before = await newest();
  await r.post('/api/machines/M001/fault', { headers: H, data: { fault_mode: 'overheating' } });
  await r.post('/api/simulation/start?interval=0.5', { headers: H });
  try {
    await expect.poll(newest, { timeout: 30_000 }).toBeGreaterThan(before);
  } finally {
    await r.post('/api/simulation/stop', { headers: H });
    await r.post('/api/machines/M001/fault', { headers: H, data: { fault_mode: 'normal' } });
  }
  return newest();
}

test('4. alarm, acknowledge, work order, approve', async ({ browser }) => {
  const adminPage = await pageAs(browser, 'admin');
  await adminPage.goto('/fleet');
  const alarmId = await raiseAlarm(adminPage);

  const page = await pageAs(browser, 'operator');
  await page.goto(`/alarms?alarm=${alarmId}`);
  const drawer = page.getByRole('dialog', { name: `Alarm ${alarmId}` });
  await expect(drawer).toBeVisible();
  await drawer.getByRole('button', { name: 'Acknowledge' }).click();
  await expect(drawer).toContainText('Acknowledged');
  await expect(drawer).toContainText('test_operator');

  await drawer.getByRole('link', { name: 'Create a work order for this alarm' }).click();
  const create = page.getByRole('dialog', { name: 'New work order' });
  await expect(create).toContainText(`Linked to alarm ${alarmId}`);
  const action = `Check M001 cooling, alarm ${alarmId}`;
  await create.getByLabel('Action').fill(action);
  await create.getByLabel('Urgency').selectOption('High');
  await create.getByRole('button', { name: 'Create, pending approval' }).click();

  const row = page.getByRole('row', { name: new RegExp(action) });
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: 'Approve' }).click();
  await page.getByRole('dialog', { name: 'Approve work order' }).getByRole('button', { name: 'Approve' }).click();
  await expect(row).toHaveCount(0); // gone from the pending list

  const orders = (await (await api(page).get('/api/work-orders?machine_id=M001&limit=50', { headers: H })).json()).work_orders;
  const wo = orders.find((o: { action: string }) => o.action === action);
  expect(wo).toMatchObject({ status: 'Open', alarm_id: alarmId, created_by: 'test_operator' });
});

test('5. admin opens Cognition, traces a machine and replays a stored window', async ({ browser }) => {
  const page = await pageAs(browser, 'admin');
  await page.goto('/admin/cognition?domain=cmapss&machine=unit_3');
  await expect(page.getByRole('heading', { level: 1, name: 'Cognition' })).toBeVisible();
  // all ten stages, each with its latency
  for (const stage of ['Adapter', 'World Model', 'Memory (AMKB)', 'Machine DNA', 'Adaptive Context', 'RUL prediction', 'Simulation', 'Decision Graph', 'Explainability', 'Learning Engine']) {
    await expect(page.getByRole('heading', { level: 2, name: new RegExp(`^\\d+\\. ${stage.replace(/[()]/g, '\\$&')}`) })).toBeVisible({ timeout: 20_000 });
  }
  await expect(page.getByText('Live trace', { exact: true })).toBeVisible();
  // a second live trace, so there are at least two stored windows to scrub between
  await page.getByRole('button', { name: 'Run live trace' }).click();
  const scrub = page.getByRole('slider', { name: 'Replay a stored trace' });
  await expect(scrub).toBeVisible({ timeout: 20_000 });
  await scrub.focus();
  await page.keyboard.press('Home'); // the oldest stored trace
  await expect(page).toHaveURL(/ts=/);
  await expect(page.getByText('Replay', { exact: true })).toBeVisible();
  await expect(page.getByText(/Replaying the trace stored at/)).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: /^8\. Decision Graph/ })).toBeVisible();
  await page.getByRole('button', { name: 'Back to live' }).click();
  await expect(page.getByText('Live trace', { exact: true })).toBeVisible({ timeout: 20_000 });
  // the model registry lists the active version for every trained domain
  await page.goto('/admin/models');
  await expect(page.getByRole('heading', { level: 2, name: 'Turbofan (C-MAPSS)' })).toBeVisible();
  await expect(page.getByText('Active', { exact: true }).first()).toBeVisible();
});

test('6. an operator cannot see the Cognition dashboard', async ({ browser }) => {
  const page = await pageAs(browser, 'operator');
  await page.goto('/fleet');
  await expect(page.getByRole('complementary', { name: 'Main' }).getByRole('link', { name: 'Cognition' })).toHaveCount(0);
  await page.goto('/admin/cognition');
  await expect(page.getByText('Not available for your role')).toBeVisible();
  const res = await api(page).get('/api/admin/cognition/unit_1/trace?domain=cmapss', { headers: H });
  expect(res.status()).toBe(403);
});

test('evidence: every number loads and every link opens a real page', async ({ browser }) => {
  const page = await pageAs(browser, 'admin');
  await page.goto('/about/evidence');
  await expect(page.getByRole('heading', { level: 1, name: 'Evidence' })).toBeVisible();
  for (const term of ['Adaptive', 'Machine Cognition', 'Platform', 'Explainable', 'Predictive Maintenance', 'Heterogeneous Machine Systems']) {
    await expect(page.getByRole('heading', { level: 2, name: term, exact: true })).toBeVisible();
  }
  // live numbers came from the result files, not placeholders
  await expect(page.getByText(/RMSE 15\.42, MAE 11\.81, PHM score 394\.7/)).toBeVisible();
  await expect(page.getByText(/Deletion test on 100 FD001 test units/)).toBeVisible();
  await expect(page.getByText('result file not found on this server')).toHaveCount(0);

  const hrefs = [...new Set(await page.locator('main a[href^="/"]').evaluateAll(as => as.map(a => a.getAttribute('href')!)))];
  expect(hrefs.length).toBeGreaterThan(8);
  for (const href of hrefs) {
    await page.goto(href);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByText('No page at this address'), href).toHaveCount(0);
    await expect(page.getByText('Not available for your role'), href).toHaveCount(0);
  }
});
