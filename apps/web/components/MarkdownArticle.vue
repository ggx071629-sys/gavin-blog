<template>
  <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
</template>

<script setup lang="ts">
import hljs from 'highlight.js/lib/core'
import type { LanguageFn } from 'highlight.js'
import MarkdownIt from 'markdown-it'
import anchor from 'markdown-it-anchor'
import container from 'markdown-it-container'
import footnote from 'markdown-it-footnote'
import tableOfContents from 'markdown-it-table-of-contents'
import taskLists from 'markdown-it-task-lists'
import type { WikiResolution } from '~/types/api'
import { normalizeStandaloneNotices, parseFenceInfo, slugifyMarkdownHeading } from '~/utils/markdown'
import { applyWikilinks } from '~/utils/wikilinks'

const props = defineProps<{ content: string, wikilinks?: WikiResolution[], copyableCode?: boolean }>()
const root = ref<HTMLElement | null>(null)
const colorMode = useColorMode()
const mermaidSources = new WeakMap<HTMLElement, string>()
const mermaidIdPrefix = useId().replace(/[^a-zA-Z0-9_-]/g, '')
let requestedRender = 0
let renderQueue = Promise.resolve()
const enhancerVersion = ref(0)

const languageLoaders: Record<string, () => Promise<{ default: LanguageFn }>> = {
  bash: () => import('highlight.js/lib/languages/bash'),
  css: () => import('highlight.js/lib/languages/css'),
  javascript: () => import('highlight.js/lib/languages/javascript'),
  json: () => import('highlight.js/lib/languages/json'),
  markdown: () => import('highlight.js/lib/languages/markdown'),
  powershell: () => import('highlight.js/lib/languages/powershell'),
  python: () => import('highlight.js/lib/languages/python'),
  sql: () => import('highlight.js/lib/languages/sql'),
  typescript: () => import('highlight.js/lib/languages/typescript'),
  xml: () => import('highlight.js/lib/languages/xml'),
  yaml: () => import('highlight.js/lib/languages/yaml'),
  ini: () => import('highlight.js/lib/languages/ini'),
}
const languageAliases: Record<string, string> = {
  html: 'xml',
  js: 'javascript',
  md: 'markdown',
  ps1: 'powershell',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  ts: 'typescript',
  vue: 'xml',
  yml: 'yaml',
  toml: 'ini',
}
const registeredLanguages = new Set<string>()
let mathEnabled = false

const escapeHtml = (value: string) => MarkdownIt().utils.escapeHtml(value)
const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight(code, language) {
    if (language && hljs.getLanguage(language)) {
      return hljs.highlight(code, { language }).value
    }
    return escapeHtml(code)
  },
})

markdown.use(anchor, {
  slugify: slugifyMarkdownHeading,
  permalink: anchor.permalink.linkInsideHeader({
    symbol: '#',
    placement: 'after',
    ariaHidden: true,
    renderAttrs: () => ({ tabindex: '-1' }),
  }),
})
markdown.use(footnote)
markdown.use(taskLists, { enabled: true, label: true })
markdown.use(tableOfContents, { includeLevel: [1, 2] })

for (const type of ['tip', 'warning', 'note']) {
  markdown.use(container, type, {
    render(tokens: Array<{ nesting: number }>, index: number) {
      return tokens[index]?.nesting === 1
        ? '<aside class="callout callout-' + type + '">'
        : '</aside>'
    },
  })
}

const defaultFence = markdown.renderer.rules.fence
markdown.renderer.rules.fence = (tokens, index, options, env, self) => {
  const token = tokens[index]
  if (token && token.info.trim() === 'mermaid') {
    return '<div class="mermaid" data-mermaid-block><pre class="mermaid-source"><code>'
      + escapeHtml(token.content)
      + '</code></pre></div>'
  }
  if (token && props.copyableCode) {
    const { language, filename } = parseFenceInfo(token.info)
    const highlighted = options.highlight
      ? options.highlight(token.content, language, '')
      : escapeHtml(token.content)
    const languageLabel = language ? escapeHtml(language.toUpperCase()) : 'CODE'
    const fileLabel = filename ? escapeHtml(filename) : ''
    const meta = fileLabel ? `${languageLabel} · ${fileLabel}` : languageLabel
    const languageClass = language ? ` language-${escapeHtml(language)}` : ''
    const lineCount = token.content.replace(/\n$/, '').split('\n').length
    const gutter = Array.from({ length: lineCount }, (_, line) => (
      `<span>${String(line + 1).padStart(2, '0')}</span>`
    )).join('')
    return `<div class="article-code" data-lines="${lineCount === 1 ? 'single' : 'multiple'}" data-copy-state="idle">
    <div class="article-code-bar">
      <span class="article-code-meta">${meta}</span>
      <button type="button" class="article-code-copy" data-code-copy>复制</button>
    </div>
    <div class="article-code-body">
      <div class="article-code-gutter" aria-hidden="true">${gutter}</div>
      <pre class="article-code-pre" tabindex="0"><code class="hljs${languageClass}">${highlighted}</code></pre>
    </div>
    <p class="article-code-foot" data-code-copy-status aria-live="polite"></p>
  </div>`
  }
  return defaultFence ? defaultFence(tokens, index, options, env, self) : ''
}

const shiftHeadingTag = (tag: string) => {
  const level = Number(tag.slice(1))
  return Number.isInteger(level) ? `h${Math.min(6, level + 1)}` : tag
}
const defaultHeadingOpen = markdown.renderer.rules.heading_open
const defaultHeadingClose = markdown.renderer.rules.heading_close
const defaultTableOpen = markdown.renderer.rules.table_open
const defaultTableClose = markdown.renderer.rules.table_close
markdown.renderer.rules.heading_open = (tokens, index, options, env, self) => {
  const token = tokens[index]
  if (token) token.tag = shiftHeadingTag(token.tag)
  return defaultHeadingOpen
    ? defaultHeadingOpen(tokens, index, options, env, self)
    : self.renderToken(tokens, index, options)
}
markdown.renderer.rules.heading_close = (tokens, index, options, env, self) => {
  const token = tokens[index]
  if (token) token.tag = shiftHeadingTag(token.tag)
  return defaultHeadingClose
    ? defaultHeadingClose(tokens, index, options, env, self)
    : self.renderToken(tokens, index, options)
}
markdown.renderer.rules.table_open = (tokens, index, options, env, self) => {
  const table = defaultTableOpen
    ? defaultTableOpen(tokens, index, options, env, self)
    : '<table>'
  return `<div class="article-table-scroll" data-table-scroll role="region" tabindex="0" aria-label="可横向滚动的表格">${table}`
}
markdown.renderer.rules.table_close = (tokens, index, options, env, self) => {
  const table = defaultTableClose
    ? defaultTableClose(tokens, index, options, env, self)
    : '</table>'
  return `${table}</div>`
}

const fenceLanguages = (content: string) => Array.from(content.matchAll(/^(?:```|~~~)\s*([^\s`~]+)/gm))
  .map(match => match[1]?.toLowerCase())
  .filter((value): value is string => Boolean(value) && value !== 'mermaid')

const containsMath = (content: string) => /\$\$[\s\S]+?\$\$|(^|[^\\])\$(?!\s)[^$\n]+?\$/m.test(content)
useHead(() => containsMath(props.content)
  ? { link: [{ key: 'katex-styles', rel: 'stylesheet', href: '/katex/katex.min.css' }] }
  : {})

const ensureEnhancers = async (content: string) => {
  const canonicalLanguages = new Set(fenceLanguages(content).map(language => languageAliases[language] || language))
  for (const language of canonicalLanguages) {
    if (registeredLanguages.has(language) || !languageLoaders[language]) continue
    const module = await languageLoaders[language]()
    hljs.registerLanguage(language, module.default)
    for (const [alias, canonical] of Object.entries(languageAliases)) {
      if (canonical === language) hljs.registerAliases(alias, { languageName: language })
    }
    registeredLanguages.add(language)
  }

  if (containsMath(content) && !mathEnabled) {
    const [{ default: katex }, { default: texmath }] = await Promise.all([
      import('katex'),
      import('markdown-it-texmath'),
    ])
    markdown.use(texmath, { engine: katex, delimiters: 'dollars' })
    mathEnabled = true
  }
}

await ensureEnhancers(props.content)

const rendered = computed(() => {
  // Reading enhancerVersion registers it as a reactive dependency so that
  // late-loaded Mermaid/KaTeX plugins trigger a re-render without re-parsing state.
  // eslint-disable-next-line @typescript-eslint/no-unused-expressions
  enhancerVersion.value
  return markdown.render(normalizeStandaloneNotices(applyWikilinks(props.content, props.wikilinks || [])))
})

const mermaidFallback = (source: string) => `
  <div class="mermaid-fallback">
    <p role="alert">图表无法渲染，已保留 Mermaid 源码。</p>
    <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
    <span class="sr-only" aria-live="polite" data-mermaid-copy-status></span>
    <pre><code>${escapeHtml(source)}</code></pre>
  </div>`

let mermaidLoader: Promise<(typeof import('mermaid'))['default']> | null = null

const loadMermaid = () => {
  mermaidLoader ??= (async () => {
    let lastError: unknown
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        return (await import('mermaid')).default
      }
      catch (error) {
        lastError = error
        await new Promise(resolve => setTimeout(resolve, 250 * (attempt + 1)))
      }
    }
    mermaidLoader = null
    throw lastError
  })()
  return mermaidLoader
}

const markMermaidState = (nodes: HTMLElement[], state: 'pending' | 'ready') => {
  for (const node of nodes) node.dataset.mermaidState = state
}

const renderMermaid = async (renderId: number) => {
  if (!import.meta.client || renderId !== requestedRender) return
  await nextTick()
  const nodes = Array.from(root.value?.querySelectorAll<HTMLElement>('[data-mermaid-block]') ?? [])
  if (!nodes.length || renderId !== requestedRender) return
  markMermaidState(nodes, 'pending')
  const theme = colorMode.value === 'dark' ? 'dark' : 'default'
  let mermaid: (typeof import('mermaid'))['default']
  try {
    mermaid = await loadMermaid()
    if (renderId !== requestedRender) return
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      suppressErrorRendering: true,
      theme,
    })
  }
  catch {
    if (renderId !== requestedRender) return
    for (const node of nodes) {
      const source = mermaidSources.get(node) ?? node.textContent ?? ''
      mermaidSources.set(node, source)
      node.classList.add('mermaid-error')
      node.dataset.mermaidTheme = theme
      node.innerHTML = mermaidFallback(source)
    }
    markMermaidState(nodes, 'ready')
    return
  }

  for (const [index, node] of nodes.entries()) {
    const source = mermaidSources.get(node)
      ?? node.querySelector('code')?.textContent
      ?? node.textContent
      ?? ''
    mermaidSources.set(node, source)
    try {
      const result = await mermaid.render(
        `${mermaidIdPrefix}-${renderId}-${index}`,
        source,
      )
      if (renderId !== requestedRender) return
      node.classList.remove('mermaid-error')
      node.innerHTML = result.svg
      node.dataset.mermaidTheme = theme
      result.bindFunctions?.(node)
    }
    catch {
      if (renderId !== requestedRender) return
      node.classList.add('mermaid-error')
      node.dataset.mermaidTheme = theme
      node.innerHTML = mermaidFallback(source)
    }
  }
  if (renderId === requestedRender) markMermaidState(nodes, 'ready')
}

const scheduleMermaidRender = () => {
  const renderId = ++requestedRender
  renderQueue = renderQueue
    .then(() => renderMermaid(renderId))
    .catch(() => undefined)
}

const copyMermaidSource = async (button: HTMLButtonElement) => {
  const fallback = button.closest<HTMLElement>('.mermaid-fallback')
  const source = fallback?.querySelector('code')?.textContent ?? ''
  const status = fallback?.querySelector<HTMLElement>('[data-mermaid-copy-status]')
  try {
    await navigator.clipboard.writeText(source)
    if (status) status.textContent = 'Mermaid 源码已复制。'
  }
  catch {
    if (status) status.textContent = '复制失败，请手动选择源码。'
  }
}

const copyTextToClipboard = async (source: string) => {
  if (navigator.clipboard?.writeText) {
    const copied = await Promise.race([
      navigator.clipboard.writeText(source).then(() => true),
      new Promise<boolean>(resolve => window.setTimeout(() => resolve(false), 800)),
    ])
    if (copied) return
  }

  const textarea = document.createElement('textarea')
  textarea.value = source
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  textarea.remove()
  if (!copied) throw new Error('clipboard unavailable')
}

const copyCodeBlock = async (button: HTMLButtonElement) => {
  const block = button.closest<HTMLElement>('.article-code')
  const source = block?.querySelector('pre code')?.textContent ?? ''
  const status = block?.querySelector<HTMLElement>('[data-code-copy-status]')
  if (block?.dataset.copyPending === 'true') return
  if (block) block.dataset.copyPending = 'true'
  button.textContent = '复制中'
  if (block) block.dataset.copyState = 'pending'
  if (status) status.textContent = '正在复制'
  try {
    await copyTextToClipboard(source)
    button.textContent = '已复制'
    if (block) block.dataset.copyState = 'copied'
    if (status) status.textContent = '已复制'
    window.setTimeout(() => {
      button.textContent = '复制'
      if (block) block.dataset.copyState = 'idle'
      if (status) status.textContent = ''
    }, 4000)
  }
  catch {
    button.textContent = '重试'
    if (block) block.dataset.copyState = 'error'
    if (status) status.textContent = '复制失败，请手动选择或重试'
  }
  finally {
    if (block) delete block.dataset.copyPending
  }
}

const bindCodeCopyButtons = () => {
  for (const button of Array.from(root.value?.querySelectorAll<HTMLButtonElement>('[data-code-copy]') ?? [])) {
    if (button.dataset.copyBound === 'true') continue
    button.dataset.copyBound = 'true'
    button.onclick = () => { void copyCodeBlock(button) }
  }
}

const handleArticleClick = async (event: MouseEvent) => {
  const target = event.target as (EventTarget & { closest?: (selector: string) => Element | null }) | null
  const closest = typeof target?.closest === 'function'
    ? target.closest.bind(target)
    : undefined
  const mermaidButton = closest?.('[data-mermaid-copy]') as HTMLButtonElement | null
  if (mermaidButton) {
    await copyMermaidSource(mermaidButton)
    return
  }
}

onMounted(() => {
  bindCodeCopyButtons()
  scheduleMermaidRender()
})
watch(rendered, async () => {
  await nextTick()
  bindCodeCopyButtons()
  scheduleMermaidRender()
})
watch(() => props.content, async (content) => {
  await ensureEnhancers(content)
  enhancerVersion.value += 1
})
watch(() => colorMode.value, scheduleMermaidRender)
</script>
