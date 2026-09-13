import { existsSync, realpathSync } from 'node:fs'
import { resolve } from 'node:path'
import { searchForWorkspaceRoot } from 'vite'

const candidateRoots = [
  resolve(process.cwd(), 'node_modules'),
  resolve(process.cwd(), '..', '..', 'node_modules'),
].filter(existsSync)
const devDependencyRoots = [...candidateRoots]
const assistantLocalDevCommand = process.env.NUXT_BUILD_DIR === '.nuxt/assistant-dev'
  && process.env.NUXT_PUBLIC_ASSISTANT_LOCAL_DEV_MODE === 'true'
for (const path of candidateRoots) {
  try {
    const real = realpathSync(path)
    if (!devDependencyRoots.includes(real)) devDependencyRoots.push(real)
  }
  catch {
    // Junctions on Windows can fail realpath; the raw path remains allowed.
  }
}

export default defineNuxtConfig({
  compatibilityDate: '2026-07-31',
  buildDir: process.env.NUXT_BUILD_DIR || undefined,
  devtools: { enabled: process.env.NODE_ENV !== 'production' },
  modules: ['@nuxtjs/tailwindcss', '@nuxtjs/color-mode', '@nuxt/eslint'],
  nitro: {
    esbuild: {
      options: {
        target: 'es2022',
      },
    },
  },
  vite: {
    server: {
      fs: {
        // Isolated Git worktrees often live on another drive than node_modules.
        // Vite @fs then 404s font files even when realpath is listed in allow.
        strict: process.env.NUXT_VITE_FS_STRICT !== '0',
        allow: [searchForWorkspaceRoot(process.cwd()), ...devDependencyRoots],
      },
    },
  },
  hooks: {
    'vite:extendConfig'(config) {
      if (process.env.NUXT_VITE_FS_STRICT !== '0') return
      const fs = config.server?.fs
      if (!fs) return
      fs.strict = false
      const allow = new Set([
        ...((fs.allow as string[] | undefined) ?? []),
        searchForWorkspaceRoot(process.cwd()),
        ...devDependencyRoots,
      ])
      fs.allow = [...allow]
    },
  },
  tailwindcss: {
    config: {
      theme: {
        extend: {
          colors: {
            ee: {
              canvas: 'var(--ee-canvas)',
              surface: {
                DEFAULT: 'var(--ee-surface)',
                low: 'var(--ee-surface-low)',
                high: 'var(--ee-surface-high)',
              },
              ink: {
                DEFAULT: 'var(--ee-ink)',
                muted: 'var(--ee-ink-muted)',
                faint: 'var(--ee-ink-faint)',
              },
              line: {
                DEFAULT: 'var(--ee-line)',
                soft: 'var(--ee-line-soft)',
              },
              primary: {
                DEFAULT: 'var(--ee-primary)',
                strong: 'var(--ee-primary-strong)',
                contrast: 'var(--ee-primary-contrast)',
              },
              signal: {
                DEFAULT: 'var(--ee-signal)',
                ink: 'var(--ee-signal-ink)',
              },
              focus: 'var(--ee-focus)',
              info: {
                bg: 'var(--ee-info-bg)',
                border: 'var(--ee-info-border)',
                ink: 'var(--ee-info-ink)',
              },
              success: {
                bg: 'var(--ee-success-bg)',
                border: 'var(--ee-success-border)',
                ink: 'var(--ee-success-ink)',
              },
              warning: {
                bg: 'var(--ee-warning-bg)',
                border: 'var(--ee-warning-border)',
                ink: 'var(--ee-warning-ink)',
              },
              danger: {
                bg: 'var(--ee-danger-bg)',
                border: 'var(--ee-danger-border)',
                ink: 'var(--ee-danger-ink)',
              },
            },
          },
          borderRadius: {
            ee: 'var(--ee-radius)',
            'ee-soft': 'var(--ee-radius-soft)',
          },
        },
      },
    },
  },
  css: [
    '@fontsource/inter/latin-400.css',
    '@fontsource/inter/latin-500.css',
    '@fontsource/inter/latin-600.css',
    '@fontsource/inter/latin-700.css',
    '@fontsource/space-grotesk/latin-500.css',
    '@fontsource/space-grotesk/latin-700.css',
    '@fontsource/noto-sans-sc/chinese-simplified-400.css',
    '@fontsource/noto-sans-sc/chinese-simplified-700.css',
    '@fontsource/jetbrains-mono/latin-400.css',
    '@fontsource/jetbrains-mono/latin-500.css',
    '@fontsource/jetbrains-mono/latin-600.css',
    '~/assets/css/main.css',
    '~/assets/css/public-reading.css',
    '~/assets/css/writing-desk.css',
    '~/assets/css/studio.css',
  ],
  colorMode: {
    classSuffix: '',
    preference: 'system',
    fallback: 'light',
  },
  runtimeConfig: {
    apiUpstream: process.env.NUXT_API_UPSTREAM || 'http://127.0.0.1:8000',
    assistantTrustedEdgeProxies: process.env.NUXT_ASSISTANT_TRUSTED_EDGE_PROXIES || '',
    assistantEdgeClientIpHeader: process.env.NUXT_ASSISTANT_EDGE_CLIENT_IP_HEADER || '',
    assistantApiClientIpHeader: process.env.NUXT_ASSISTANT_API_CLIENT_IP_HEADER || '',
    assistantProxyHmacSecret: process.env.NUXT_ASSISTANT_PROXY_HMAC_SECRET || '',
    assistantDevDirectLoopback: assistantLocalDevCommand
      && process.env.NUXT_ASSISTANT_DEV_DIRECT_LOOPBACK === 'true',
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api/v1',
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'http://localhost:3000',
      assistantUiEnabled: process.env.NUXT_PUBLIC_ASSISTANT_UI_ENABLED === 'true',
      assistantLocalDevMode: process.env.NUXT_PUBLIC_ASSISTANT_LOCAL_DEV_MODE === 'true',
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      title: '技术与思考',
      titleTemplate: '%s · Gavin',
      meta: [
        {
          name: 'description',
          content: 'Gavin 的技术文章、问题排查与项目复盘。',
        },
        // Keep these SSR-safe literals synchronized with --ee-canvas; the static hardening test enforces it.
        { name: 'theme-color', content: '#f3f5f9', media: '(prefers-color-scheme: light)' },
        { name: 'theme-color', content: '#07080c', media: '(prefers-color-scheme: dark)' },
      ],
    },
  },
  typescript: {
    typeCheck: process.env.NUXT_TYPECHECK !== '0',
    strict: true,
  },
})
