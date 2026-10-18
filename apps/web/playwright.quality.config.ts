import { defineConfig, devices } from '@playwright/test'

const apiPython = process.platform === 'win32'
  ? '..\\api\\.venv\\Scripts\\python.exe'
  : '../api/.venv/bin/python'
const webOrigin = 'http://127.0.0.1:3300'
const apiOrigin = 'http://127.0.0.1:8300'

export default defineConfig({
  testDir: './tests/quality',
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
      command: apiPython + ' ../api/scripts/run_e2e.py --port 8300 --web-origin ' + webOrigin,
      port: 8300,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run preview',
      port: 3300,
      env: {
        HOST: '127.0.0.1',
        PORT: '3300',
        NITRO_HOST: '127.0.0.1',
        NITRO_PORT: '3300',
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
      name: 'quality-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
