// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      // Markdown/HTML bodies come from the admin-authored markdown-it pipeline
      // and are rendered as trusted content; CSP handling is tracked separately.
      'vue/no-v-html': 'off',
    },
  },
)
