import { defineConfig, devices } from '@playwright/test'
import { E2E_API_PORT, resolveE2EWebPort } from './tests/support/e2e-env'

const apiPython = process.platform === 'win32'
  ? '..\\api\\.venv\\Scripts\\python.exe'
  : '../api/.venv/bin/python'
const webPort = resolveE2EWebPort()
const webOrigin = `http://127.0.0.1:${webPort}`
const apiOrigin = `http://127.0.0.1:${E2E_API_PORT}`
const runRoot = process.env.GAVIN_E2E_RUN_ROOT || ''

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 180_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: webOrigin,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: apiPython + ` ../api/scripts/run_e2e.py --port ${E2E_API_PORT} --web-origin ` + webOrigin,
      url: apiOrigin + '/api/health',
      env: {
        GAVIN_E2E_RUN_ROOT: runRoot,
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${webPort}`,
      url: webOrigin,
      env: {
        NUXT_IGNORE_LOCK: '1',
        NUXT_BUILD_DIR: '.nuxt/e2e',
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
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
