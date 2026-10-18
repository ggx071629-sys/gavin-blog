import { createServer } from 'node:http'

const port = Number(process.env.FAILURE_API_PORT || 8200)
function send(response, status, body) {
  response.writeHead(status, { 'content-type': 'application/json; charset=utf-8' })
  response.end(JSON.stringify(body))
}

const server = createServer((request, response) => {
  const url = new URL(request.url || '/', `http://127.0.0.1:${port}`)
  if (url.pathname === '/health') return send(response, 200, { status: 'ok' })
  const split = request.headers.cookie?.match(/failure-split=([^;]+)/)?.[1]
  if (url.pathname === '/api/v1/taxonomy') {
    if (split === 'list-ok-taxonomy-down') {
      return send(response, 503, { detail: 'taxonomy unavailable' })
    }
    return send(response, 200, { categories: [], tags: [], total_article_count: 0 })
  }
  if (url.pathname === '/api/v1/articles' && split === 'list-ok-taxonomy-down') {
    return send(response, 200, [{
      id: 1,
      title: 'PENPOT-ARTICLES-LIST',
      slug: 'penpot-articles-list',
      summary: 'List survives taxonomy failure.',
      content: '# List\n\nSeed.',
      published_at: '2026-08-15T00:00:00Z',
      updated_at: '2026-08-15T00:00:00Z',
      public_path: '/notes/2026/08/penpot-articles-list',
      category: null,
      tags: [],
      references: [],
      wikilinks: [],
    }])
  }

  const sessionMode = request.headers.cookie?.match(/failure-session=([^;]+)/)?.[1]
  if (url.pathname === '/api/v1/auth/session') {
    if (sessionMode === 'ok') return send(response, 200, { username: 'gavin' })
    if (sessionMode === 'unauthorized') return send(response, 401, { detail: 'not authenticated' })
    return send(response, 500, { detail: 'session backend failed' })
  }
  if (url.pathname === '/api/v1/auth/logout') {
    return send(response, 500, { detail: 'logout backend failed' })
  }
  if (url.pathname === '/api/v1/admin/articles') return send(response, 200, [])
  if (url.pathname === '/api/v1/admin/projects') return send(response, 200, [])

  if (url.pathname === '/api/v1/projects' && url.searchParams.get('offset') === '12') {
    return send(response, 200, [])
  }
  if (url.pathname === '/api/v1/projects' && url.searchParams.get('offset') === '24') {
    request.socket.destroy()
    return
  }
  if (/\/(missing)$/.test(url.pathname)) return send(response, 404, { detail: 'not found' })
  if (/\/(broken)$/.test(url.pathname)) return send(response, 500, { detail: 'upstream failed' })

  return send(response, 503, { detail: 'fixture upstream unavailable' })
})

server.listen(port, '127.0.0.1')

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.close(() => process.exit(0)))
}
