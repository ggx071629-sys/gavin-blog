import { defineConfig, devices } from '@playwright/test'

const webOrigin = 'http://127.0.0.1:3200'
const apiOrigin = 'http://127.0.0.1:8200'

export default defineConfig({
  testDir: './tests/failure',
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: webOrigin,
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: 'node tests/fixtures/failure-api.mjs',
      url: `${apiOrigin}/health`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 3200',
      url: `${webOrigin}/admin/login`,
      env: {
        NUXT_IGNORE_LOCK: '1',
        NUXT_BUILD_DIR: '.nuxt/failure',
        NUXT_TYPECHECK: '0',
        NUXT_VITE_FS_STRICT: '0',
        NUXT_PUBLIC_API_BASE: '/api/v1',
        NUXT_API_UPSTREAM: apiOrigin,
        NUXT_PUBLIC_SITE_URL: webOrigin,
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
