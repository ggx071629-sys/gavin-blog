import { defineConfig, devices } from '@playwright/test'

const apiPython = process.platform === 'win32'
  ? '..\\api\\.venv\\Scripts\\python.exe'
  : '../api/.venv/bin/python'
const webPort = 3101
const apiPort = 8101
const webOrigin = `http://127.0.0.1:${webPort}`
const apiOrigin = `http://127.0.0.1:${apiPort}`
const runRoot = process.env.GAVIN_E2E_RUN_ROOT || ''

export default defineConfig({
  testDir: './tests/e2e-assistant',
  timeout: 180_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: webOrigin,
    trace: 'retain-on-failure',
    extraHTTPHeaders: {
      'X-Gavin-Edge-Client-IP': '198.51.100.42',
    },
  },
  webServer: [
    {
      command: `${apiPython} ../api/scripts/run_assistant_e2e.py --port ${apiPort} --web-origin ${webOrigin}`,
      url: apiOrigin + '/api/health',
      env: { GAVIN_E2E_RUN_ROOT: runRoot },
      reuseExistingServer: false,
      timeout: 180_000,
    },
    {
      command: `npm run build && npm run preview -- --port ${webPort}`,
      url: webOrigin,
      env: {
        NUXT_IGNORE_LOCK: '1',
        NITRO_HOST: '127.0.0.1',
        NUXT_BUILD_DIR: '.nuxt',
        NUXT_TYPECHECK: '0',
        NUXT_VITE_FS_STRICT: '0',
        NUXT_PUBLIC_API_BASE: '/api/v1',
        NUXT_API_UPSTREAM: apiOrigin,
        NUXT_PUBLIC_SITE_URL: webOrigin,
        NUXT_PUBLIC_ASSISTANT_UI_ENABLED: 'true',
        NUXT_PUBLIC_ASSISTANT_LOCAL_DEV_MODE: 'true',
        NUXT_ASSISTANT_TRUSTED_EDGE_PROXIES: '127.0.0.1/32,::1/128',
        NUXT_ASSISTANT_EDGE_CLIENT_IP_HEADER: 'X-Gavin-Edge-Client-IP',
        NUXT_ASSISTANT_API_CLIENT_IP_HEADER: 'X-Gavin-Client-IP',
        NUXT_ASSISTANT_PROXY_HMAC_SECRET: 'assistant-proxy-secret-value-32bytes',
      },
      reuseExistingServer: false,
      timeout: 180_000,
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
