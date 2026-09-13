export interface AdminNavItem {
  label: string
  href: string
}

export interface AdminNavGroup {
  label: string
  items: AdminNavItem[]
}

export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    label: '内容',
    items: [
      { label: '文章', href: '/admin/articles' },
      { label: '读书', href: '/admin/books' },
      { label: '项目', href: '/admin/projects' },
    ],
  },
  {
    label: '运营',
    items: [
      { label: '个人名片', href: '/admin/profile' },
      { label: '账号安全', href: '/admin/account' },
      { label: '关于页', href: '/admin/about' },
      { label: '栏目与标签', href: '/admin/taxonomy' },
      { label: '媒体', href: '/admin/media' },
      { label: '回收站与迁移', href: '/admin/content' },
      { label: '问答助手', href: '/admin/assistant' },
    ],
  },
]

export const isAdminNavItemActive = (path: string, href: string) =>
  path === href || path.startsWith(`${href}/`)
