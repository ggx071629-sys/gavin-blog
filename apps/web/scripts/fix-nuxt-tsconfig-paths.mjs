import { readdir, readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const nuxtRoot = join(process.cwd(), '.nuxt')
const brokenWindowsPath = /^\.\/[A-Za-z]:\//
const files = []

try {
  await readdir(nuxtRoot)
} catch {
  throw new Error('Nuxt types are missing; run nuxt prepare before fixing tsconfig paths')
}

async function collect(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  for (const entry of entries) {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) {
      await collect(path)
      continue
    }
    if (entry.name.endsWith('.json') || entry.name === 'eslint.config.mjs') files.push(path)
  }
}

const rewrite = (value) => {
  if (typeof value === 'string') {
    return brokenWindowsPath.test(value) ? value.slice(2) : value
  }
  if (Array.isArray(value)) return value.map(rewrite)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, rewrite(item)]))
  }
  return value
}

await collect(nuxtRoot)
for (const file of files) {
  const original = await readFile(file, 'utf8')
  const updated = file.endsWith('.json')
    ? `${JSON.stringify(rewrite(JSON.parse(original)), null, 2)}\n`
    : original.replace(
        /((?:from\s+|import\s+)['"])(\.\/[A-Za-z]:\/[^'"]+)(['"])/g,
        (_, prefix, specifier, quote) =>
          `${prefix}${pathToFileURL(specifier.slice(2), { windows: true }).href}${quote}`,
      )
  if (updated !== original) await writeFile(file, updated)
}
