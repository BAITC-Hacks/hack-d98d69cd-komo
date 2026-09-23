import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 120000,
  reporter: [['list']],
  use: { channel: process.env.PLAYWRIGHT_CHANNEL || undefined, baseURL: process.env.TEST_BASE_URL || 'http://localhost:3000', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
});
