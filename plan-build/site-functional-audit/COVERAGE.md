# 本轮结果与统计

- 页面路由：32；31 个执行桌面/移动入口检查，1 个 AI 管理路由排除。恢复页仅检查外壳及返回登录，不执行邮件闭环。
- 功能案例组：74；通过 70，失败 4；这不是按钮数量或所有输入组合的穷举覆盖率。
- 确认缺陷4项，未复现观察1项；无阻塞案例。单次观察 O001 不因重试成功被删除。
- 原始截图、数据和工具输出位于 `.run/site-functional-audit/20260912-0035/`；下表任务编号定位 EXECUTION.md 对应条目。
- 排除：邮件验证码与依赖它的改密/恢复闭环（用户自行实测，本轮未复验）；公开/管理AI问答；AI简历摄入/同步/引用质量。排除不计通过。

| 案例 | 任务 | 结果 | 已执行范围 | 证据/记录 |
| --- | --- | --- | --- | --- |
| C001 | P2-01 | 通过 | 正确登录、返回原后台、刷新保持会话 | P2-01 |
| C002 | P2-01 | 通过 | 错误密码401与准确反馈 | P2-01 |
| C003 | P2-01 | 通过 | 退出后后台守卫拦截 | P2-01 |
| C004 | P2-02 | 通过 | 账号资料读取与会话刷新 | p2-other-sessions.png |
| C005 | P2-02 | 通过 | 其他会话批量退出、取消、目标浏览器失效 | p2-other-sessions.png |
| C006 | P2-02 | 通过 | 单会话与当前会话退出后实际失效 | P2-02 |
| C007 | P2-03 | 通过 | 栏目新增修改取消及刷新持久化 | p2-taxonomy.png |
| C008 | P2-03 | 通过 | 标签新增修改取消及刷新持久化 | p2-taxonomy.png |
| C009 | P2-03 | 通过 | 分类重复slug拒绝与删除取消/确认 | P2-03 |
| C010 | P2-03 | 通过 | 已关联栏目与标签禁止删除 | p2-taxonomy-linked.png |
| C011 | P2-04 | 通过 | 批量图片上传、变体显示 | p2-media-loaded.png |
| C012 | P2-04 | 通过 | 加载更多12到14与重复上传去重 | p2-media-loaded.png |
| C013 | P2-04 | 通过 | 媒体搜索、来源/状态筛选及空结果 | P2-04 |
| C014 | P2-04 | 通过 | URL/Markdown复制与外链登记 | p2-media-restored.png |
| C015 | P2-04 | 通过 | 媒体单项/批量选择取消、移除、恢复 | P2-04 |
| C016 | P2-04 | 通过 | 非法格式拒绝、上传失败重试 | p6-media-retry.png |
| C017 | P2-04 | 通过 | 浏览器文件drop与ClipboardEvent粘贴上传 | P2-04 |
| C018 | P3-01 | 通过 | 文章管理搜索筛选分页、条件清除、菜单 | p3-list-articles.png |
| C019 | P3-01 | 通过 | 读书管理搜索筛选分页、条件清除、菜单 | p3-list-books.png |
| C020 | P3-01 | 通过 | 项目管理搜索筛选分页、条件清除、菜单 | p3-list-projects.png |
| C021 | P3-02 | 通过 | 文章创建校验、字段、保存刷新、预览、发布 | p3-article-published.png |
| C022 | P3-02 | 通过 | 文章媒体插入与未完成引用阻止发布 | P3-02 |
| C023 | P3-03 | 通过 | 读书创建、元数据、保存刷新、预览、发布 | p3-book-public.png |
| C024 | P3-03 | 失败 | 媒体库使用URL选择读书封面 | I001 / issue-001-book-cover.png |
| C025 | P3-04 | 通过 | 项目创建、链接关联、保存刷新、预览、发布 | p3-project-public.png |
| C026 | P3-05 | 通过 | 文章独立访客发布快照隔离与再次发布 | p3-snapshot-articles.png |
| C027 | P3-05 | 通过 | 读书独立访客发布快照隔离与再次发布 | p3-snapshot-books.png |
| C028 | P3-05 | 通过 | 项目独立访客发布快照隔离与再次发布 | p3-snapshot-projects.png |
| C029 | P4-01 | 通过 | 关于自动保存刷新、预览、发布与草稿隔离 | p4-about-public.png |
| C030 | P4-01 | 通过 | 关于领域/标签/动态/主题/规格增删排序与领域上限 | P4-01 / P6-03 |
| C031 | P4-01 | 失败 | 关于自动保存期间新增标签临时输入保持 | I003 / issue-003-tag-draft.png |
| C032 | P4-02 | 通过 | 身份、头像、技能、渠道保存刷新公开 | p4-profile-public.png |
| C033 | P4-02 | 通过 | 城市/邮箱可见性开关与复制邮箱 | P4-02 |
| C034 | P4-02 | 通过 | 普通简历保存与浏览器打开隔离PDF | P4-02 / audit-resume.pdf |
| C035 | P4-03 | 通过 | 文章历史快照、差异、取消/确认回滚与公开恢复 | p4-article-history.png |
| C036 | P4-03 | 通过 | 关于历史快照、整页预览、差异与回滚公开恢复 | p4-about-rollback.png |
| C037 | P4-03 | 通过 | 文章历史分页20/2、关于加载更多20/25 | P6-04补核 |
| C038 | P4-04 | 通过 | 文章回收站移入与恢复、公开结果 | P4-04 |
| C039 | P4-04 | 通过 | 读书回收站移入与恢复404到200 | P4-04 |
| C040 | P4-04 | 通过 | 项目回收站移入与恢复404到200 | P4-04 |
| C041 | P4-04 | 通过 | 三类专属草稿永久删除、取消及数据库复核 | p4-trash-purged.png |
| C042 | P4-04 | 通过 | 回收站分页20/1、返回上一页 | P6-04补核 |
| C043 | P4-05 | 通过 | ZIP真实下载、三类型72条元数据正文检查 | export.zip |
| C044 | P4-05 | 通过 | 有效LF三类型导入仅创建草稿、重复slug拒绝 | p4-import.png |
| C045 | P4-05 | 失败 | UTF-8 CRLF Markdown导入 | I002 / issue-002-crlf.png |
| C046 | P5-01 | 通过 | 首页图谱选中/重置、分类及文章跳转 | p5-home.png |
| C047 | P5-02 | 通过 | 三类型公开列表、详情、导航与分页 | p5-articles.png / p5-books.png / p5-projects.png |
| C048 | P5-03 | 通过 | 栏目/标签筛选、归档上下页 | p5-archive.png |
| C049 | P5-03 | 通过 | 搜索多页、刷新保留词、空结果及清空 | P5-03 |
| C050 | P5-04 | 通过 | Markdown、GFM、代码复制、KaTeX、Mermaid | p5-reading.png |
| C051 | P5-04 | 通过 | 目录锚点滚动、开始阅读、文章地址复制 | P5-04 |
| C052 | P5-04 | 通过 | 站内引用、wikilink、反链与外部参考访问 | p5-backlinks.png |
| C053 | P5-04 | 通过 | 宽代码与宽表格局部滚动、整页不溢出 | p5-wide-reading.png |
| C054 | P5-05 | 通过 | 公开身份渠道、GitHub/个人网页/PDF实际打开 | P5-05 |
| C055 | P5-05 | 通过 | RSS/sitemap/robots访问及发布范围 | P5-05 |
| C056 | P6-01 | 通过 | 31个范围内路由桌面/移动入口核对（恢复页仅外壳） | mobile-admin-0..18.png / mobile-public-0..9.png / mobile-recover-shell.png |
| C057 | P6-01 | 通过 | 移动登录、正文/设置切换、创建发布 | mobile-published.png |
| C058 | P6-01 | 通过 | 移动搜索阅读与媒体选择 | mobile-search-reading.png / P6-02 |
| C059 | P6-02 | 通过 | 主题刷新保持、公共/后台菜单开关 | mobile-home.png |
| C060 | P6-02 | 通过 | Esc关闭焦点返回、发布弹窗Tab循环 | P6-02 |
| C061 | P6-02 | 通过 | Markdown工具栏标题/加粗/引用/链接 | P6-02 |
| C062 | P6-03 | 通过 | 三类型保存503输入保留、阻止发布、重试持久化 | p6-save-failed-articles.png / p6-save-failed-books.png / p6-save-failed-projects.png |
| C063 | P6-03 | 通过 | 三类型保存中离页等待真实请求 | P6-03 |
| C064 | P6-03 | 通过 | 三类型空Alt发布校验与恢复 | P6-03 |
| C065 | P6-03 | 通过 | 创建双击只生成一个POST | P6-03 |
| C066 | P6-03 | 通过 | 真实另页退出后编辑401、不假称保存 | p6-session-expired.png |
| C067 | P6-03 | 通过 | 三类管理列表、媒体、账号读取503重试 | P6-03 |
| C068 | P6-03 | 通过 | 注销503保留真实会话状态提示 | P6-03 |
| C069 | P6-03 | 通过 | 搜索503错误页重试保留关键词 | P6-03 |
| C070 | P6-03 | 失败 | 首次客户端列表加载503进入正确错误态 | I004 / issue-004-stale-home.png / issue-004-stale-about.png |
| C071 | P6-04 | 通过 | 空站与三类型不存在详情404区分 | empty-*.png / P5-02 |
| C072 | P6-04 | 通过 | 图谱taxonomy失败展示降级并重试恢复 | P6-04补核 |
| C073 | P6-04 | 通过 | 编辑器直接设备图片插入真实媒体路径 | P6-04补核 |
| C074 | P6-04 | 通过 | 找回密码页桌面/移动外壳及返回登录 | mobile-recover-shell.png |

## 原始页面与元素目录

目录中的“动态待核”是源码盘点时的历史提示，当前已执行范围以案例矩阵及执行记录为准；不为重复出现的同一控件复制通过数。
# 功能覆盖清单

运行：20260912-0035。源码登记仅证明入口存在；下方结论为本轮实际操作结果，原始源码元素目录保留用于追溯。

排除：/admin/assistant 与所有 Assistant 组件；邮件验证码发送/收取/校验及改密恢复闭环（用户已自行实测，本轮未复验）。普通简历保存、可见性、附件仍在 P4。

每路由的桌面业务与移动入口分别核验；P6 覆盖共享主题、菜单、弹窗键盘、失败恢复。

## R01 · `/about`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/about.vue`。
- 共用落点：`default`, `AboutPublicBody`, `SiteHeader`, `SiteFooter`, `SectionHeading`, `PageHeroArtwork`, `ProfileCard`, `GeometricMark`, `NavigationArrow`, `AboutChannelIcon`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/AboutPublicBody.vue:37` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ProfileCard.vue:25` — <h2 class="sys-panel-name"><NuxtLink v-if="variant === 'intro'" to="/about">{{ profile.name }}</NuxtLink><template v-else>{{ profile.name }}</template></h2>
  - `components/ProfileCard.vue:61` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:69` — <button
  - `components/ProfileCard.vue:76` — @click="copyEmail"
  - `components/ProfileCard.vue:92` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:107` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R02 · `/admin/about/preview`

- 阶段：P4 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/about/preview.vue`。
- 共用落点：`admin-core`, `NavigationArrow`, `AboutPublicBody`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `SectionHeading`, `PageHeroArtwork`, `ProfileCard`, `GeometricMark`, `AboutChannelIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/about/preview.vue:3` — <NuxtLink to="/admin/about" class="admin-back-link"><NavigationArrow direction="left" /> 返回编辑</NuxtLink>
  - `pages/admin/about/preview.vue:4` — <header class="admin-page-header"><div><p class="admin-page-title">关于页预览</p><p class="admin-page-description">核对已保存的工作副本与共用身份资料。</p></div><NuxtLink to="/admin/about/revisions" class="button-secondary">版本历史</NuxtLink></header>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/AboutPublicBody.vue:37` — <NuxtLink
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/ProfileCard.vue:25` — <h2 class="sys-panel-name"><NuxtLink v-if="variant === 'intro'" to="/about">{{ profile.name }}</NuxtLink><template v-else>{{ profile.name }}</template></h2>
  - `components/ProfileCard.vue:61` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:69` — <button
  - `components/ProfileCard.vue:76` — @click="copyEmail"
  - `components/ProfileCard.vue:92` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:107` — @click="interactive ? undefined : $event.preventDefault()"

## R03 · `/admin/about/revisions`

- 阶段：P4 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/about/revisions.vue`。
- 共用落点：`admin-core`, `AboutPublicBody`, `AdminDialog`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `SectionHeading`, `PageHeroArtwork`, `ProfileCard`, `GeometricMark`, `NavigationArrow`, `AboutChannelIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/about/revisions.vue:11` — <NuxtLink class="button-secondary" to="/admin/about">返回编辑器</NuxtLink>
  - `pages/admin/about/revisions.vue:18` — <button v-if="error" type="button" class="button-secondary" @click="reloadHistory">重新读取历史</button>
  - `pages/admin/about/revisions.vue:38` — <button type="button" class="button-secondary" data-testid="about-revision-view" :disabled="acting" @click="view(revision)">查看快照</button>
  - `pages/admin/about/revisions.vue:39` — <button type="button" class="button-secondary" data-testid="about-revision-compare" :disabled="acting || !page?.current_revision_id" @click="compare(revision)">与当前比较</button>
  - `pages/admin/about/revisions.vue:40` — <button
  - `pages/admin/about/revisions.vue:46` — @click="rollbackTarget = revision"
  - `pages/admin/about/revisions.vue:51` — <button v-if="revisions.length < total" class="button-secondary mt-4" type="button" :disabled="loading || acting" @click="loadMore">{{ loading ? '加载中…' : '加载更多版本' }}</button>
  - `pages/admin/about/revisions.vue:60` — <button type="button" class="button-secondary" @click="detail = null; showPreview = false">关闭</button>
  - `pages/admin/about/revisions.vue:66` — <button type="button" class="button-secondary mt-3" data-testid="about-revision-preview-toggle" @click="showPreview = !showPreview">
  - `pages/admin/about/revisions.vue:87` — <AdminDialog
  - `pages/admin/about/revisions.vue:100` — <button type="button" class="button-secondary" :disabled="acting" @click="rollbackTarget = null">取消</button>
  - `pages/admin/about/revisions.vue:101` — <button type="button" class="button-primary" data-testid="about-rollback-confirm" :disabled="acting" @click="rollback">
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/AboutPublicBody.vue:37` — <NuxtLink
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/ProfileCard.vue:25` — <h2 class="sys-panel-name"><NuxtLink v-if="variant === 'intro'" to="/about">{{ profile.name }}</NuxtLink><template v-else>{{ profile.name }}</template></h2>
  - `components/ProfileCard.vue:61` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:69` — <button
  - `components/ProfileCard.vue:76` — @click="copyEmail"
  - `components/ProfileCard.vue:92` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:107` — @click="interactive ? undefined : $event.preventDefault()"

## R04 · `/admin/about`

- 阶段：P4 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/about.vue`。
- 共用落点：`admin-core`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/about.vue:12` — <button type="button" class="button-secondary" data-testid="about-preview-open" @click="openPreview">预览草稿</button>
  - `pages/admin/about.vue:13` — <NuxtLink class="button-secondary" to="/admin/about/revisions">版本历史</NuxtLink>
  - `pages/admin/about.vue:14` — <NuxtLink class="button-secondary" to="/about" target="_blank">查看公开页</NuxtLink>
  - `pages/admin/about.vue:15` — <button
  - `pages/admin/about.vue:20` — @click="publish"
  - `pages/admin/about.vue:34` — <button type="button" class="font-semibold underline" data-testid="about-refresh" @click="reload">刷新页面</button>
  - `pages/admin/about.vue:51` — <NuxtLink class="button-secondary" to="/admin/profile">前往个人名片</NuxtLink>
  - `pages/admin/about.vue:59` — <textarea v-model="form.statement" data-testid="about-statement" rows="3" maxlength="500" />
  - `pages/admin/about.vue:69` — <button type="button" class="button-secondary" data-testid="about-capability-add" :disabled="form.capabilities.length >= ABOUT_CARD_LIMIT" @click="addCapability">
  - `pages/admin/about.vue:83` — <button type="button" class="button-secondary px-2" :disabled="index === 0" data-testid="about-capability-up" aria-label="上移条目" @click="moveItem(form.capabilities, index, -1)">上移</button>
  - `pages/admin/about.vue:84` — <button type="button" class="button-secondary px-2" :disabled="index === form.capabilities.length - 1" data-testid="about-capability-down" aria-label="下移条目" @click="moveItem(form.capabilities, index, 1)">下移</button>
  - `pages/admin/about.vue:85` — <button type="button" class="button-secondary px-2 text-ee-danger-ink" data-testid="about-capability-remove" @click="form.capabilities.splice(index, 1)">删除</button>
  - `pages/admin/about.vue:91` — <input v-model="capability.title" maxlength="80" data-testid="about-capability-title">
  - `pages/admin/about.vue:95` — <textarea v-model="capability.description" rows="2" maxlength="320" data-testid="about-capability-description" />
  - `pages/admin/about.vue:105` — <button type="button" class="text-ee-ink-faint hover:text-ee-danger-ink" aria-label="删除领域标签" data-testid="about-tag-remove" @click="capability.tags.splice(tagIndex, 1)">×</button>
  - `pages/admin/about.vue:108` — <input
  - `pages/admin/about.vue:116` — <button type="button" class="button-secondary" data-testid="about-tag-add" :disabled="!(tagDrafts[index] || '').trim() || capability.tags.length >= 6" @click="addTag(index)">添加</button>
  - `pages/admin/about.vue:129` — <button type="button" class="button-secondary" data-testid="about-now-add" :disabled="form.now.length >= ABOUT_CARD_LIMIT" @click="addNow">添加条目</button>
  - `pages/admin/about.vue:140` — <input v-model="item.label" maxlength="80" data-testid="about-now-label">
  - `pages/admin/about.vue:144` — <select v-model="item.status" data-testid="about-now-status">
  - `pages/admin/about.vue:152` — <select v-model="item.target" data-testid="about-now-target">
  - `pages/admin/about.vue:159` — <button type="button" class="button-secondary px-2" :disabled="index === 0" data-testid="about-now-up" aria-label="上移条目" @click="moveItem(form.now, index, -1)">上移</button>
  - `pages/admin/about.vue:160` — <button type="button" class="button-secondary px-2" :disabled="index === form.now.length - 1" data-testid="about-now-down" aria-label="下移条目" @click="moveItem(form.now, index, 1)">下移</button>
  - `pages/admin/about.vue:161` — <button type="button" class="button-secondary px-2 text-ee-danger-ink" data-testid="about-now-remove" @click="form.now.splice(index, 1)">删除</button>
  - `pages/admin/about.vue:177` — <button type="button" class="text-ee-ink-faint hover:text-ee-danger-ink" aria-label="删除写作主题" data-testid="about-topic-remove" @click="form.editorial_topics.splice(index, 1)">×</button>
  - `pages/admin/about.vue:180` — <input v-model="topicDraft" maxlength="40" placeholder="主题（Enter 添加）" aria-label="新增写作主题" data-testid="about-topic-input" @keydown.enter.prevent="addTopic">
  - `pages/admin/about.vue:181` — <button type="button" class="button-secondary" data-testid="about-topic-add" :disabled="!topicDraft.trim() || form.editorial_topics.length >= 8" @click="addTopic">添加</button>
  - `pages/admin/about.vue:192` — <button type="button" class="button-secondary" data-testid="about-stack-add" :disabled="form.site.stack.length >= 8" @click="form.site.stack.push({ label: '', value: '' })">
  - `pages/admin/about.vue:198` — <textarea v-model="form.site.description" rows="3" maxlength="320" data-testid="about-site-description" />
  - `pages/admin/about.vue:207` — <label class="field"><span>标签</span><input v-model="entry.label" maxlength="40" data-testid="about-stack-label"></label>
  - `pages/admin/about.vue:208` — <label class="field"><span>值</span><input v-model="entry.value" maxlength="80" data-testid="about-stack-value"></label>
  - `pages/admin/about.vue:209` — <button type="button" class="button-secondary px-2 text-ee-danger-ink" data-testid="about-stack-remove" @click="form.site.stack.splice(index, 1)">删除</button>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R05 · `/admin/account`

- 阶段：P2 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/account.vue`。
- 共用落点：`admin-core`, `AccountPasswordForm`, `AccountSessions`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/account.vue:13` — <button class="button-secondary" type="button" @click="load">重新读取</button>
  - `pages/admin/account.vue:24` — <div><h2 id="account-password-heading">修改密码</h2><p>使用当前密码和安全邮箱验证码确认身份。</p><NuxtLink to="/admin/recover" class="button-secondary mt-3">忘记密码</NuxtLink></div>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/AccountPasswordForm.vue:2` — <form class="space-y-5" @submit.prevent="prepareSubmit">
  - `components/AccountPasswordForm.vue:5` — <input v-model="currentPassword" type="password" autocomplete="current-password" maxlength="512" required :disabled="busy">
  - `components/AccountPasswordForm.vue:9` — <input v-model="newPassword" type="password" autocomplete="new-password" minlength="15" maxlength="128" required :disabled="busy" aria-describedby="password-policy">
  - `components/AccountPasswordForm.vue:14` — <input v-model="confirmation" type="password" autocomplete="new-password" minlength="15" maxlength="128" required :disabled="busy">
  - `components/AccountPasswordForm.vue:19` — <input v-model="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required :disabled="busy">
  - `components/AccountPasswordForm.vue:21` — <button type="button" class="button-secondary" :disabled="busy || cooldown > 0 || !mailAvailable" :aria-busy="sending" @click="sendCode">
  - `components/AccountPasswordForm.vue:29` — <button type="submit" class="button-primary" :disabled="busy || !challenge || !mailAvailable" :aria-busy="submitting">{{ submitting ? '正在更新…' : recovery ? '重设密码' : '修改密码' }}</button>
  - `components/AccountPasswordForm.vue:30` — <AdminDialog v-model="confirmOpen" labelledby="password-confirm-title" :close-disabled="submitting">
  - `components/AccountPasswordForm.vue:34` — <button type="button" class="button-secondary" :disabled="submitting" @click="confirmOpen = false">取消</button>
  - `components/AccountPasswordForm.vue:35` — <button type="button" class="button-primary" :disabled="submitting" @click="submit">确认更新密码</button>
  - `components/AccountSessions.vue:4` — <button class="button-secondary" type="button" :disabled="loading || revoking" @click="load">刷新会话</button>
  - `components/AccountSessions.vue:5` — <button class="button-secondary" type="button" :disabled="loading || revoking || !items.some(item => !item.is_current)" @click="pending = 'others'">退出其他会话</button>
  - `components/AccountSessions.vue:18` — <button type="button" class="button-secondary" :disabled="revoking" :aria-label="item.is_current ? '退出当前会话' : ˋ退出登录会话 ${index + 1}ˋ" @click="pending = item">{{ item.is_current ? '退出当前会话' : '退出此会话' }}</button>
  - `components/AccountSessions.vue:21` — <AdminDialog :model-value="pending !== null" labelledby="session-confirm-title" :close-disabled="revoking" @update:model-value="value => { if (!value) pending = null }">
  - `components/AccountSessions.vue:25` — <button type="button" class="button-secondary" :disabled="revoking" @click="pending = null">取消</button>
  - `components/AccountSessions.vue:26` — <button type="button" class="button-primary" :disabled="revoking" @click="revoke">{{ revoking ? '正在退出…' : '确认退出' }}</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R06 · `/admin/articles/[id]/edit`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/articles/[id]/edit.vue`。
- 共用落点：`admin-core`, `ArticleEditor`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `NavigationArrow`, `WritingWorkspace`, `MarkdownMediaField`, `MarkdownArticle`, `StudioPublishConfirmation`, `MediaUploader`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/ArticleEditor.vue:3` — <NuxtLink class="admin-back-link" to="/admin/articles"><NavigationArrow direction="left" /> 返回列表</NuxtLink>
  - `components/ArticleEditor.vue:20` — <NuxtLink
  - `components/ArticleEditor.vue:26` — <NuxtLink
  - `components/ArticleEditor.vue:34` — <button
  - `components/ArticleEditor.vue:39` — @click="publish"
  - `components/ArticleEditor.vue:57` — <button class="button-secondary" type="button" @click="retrySave">重试保存</button>
  - `components/ArticleEditor.vue:64` — <input v-model="form.title" data-testid="title" placeholder="为文章写一个标题" maxlength="180" required>
  - `components/ArticleEditor.vue:80` — <select v-model="form.category_id" data-testid="category">
  - `components/ArticleEditor.vue:91` — <input v-model="form.tag_ids" type="checkbox" :value="tag.id" :data-testid="ˋtag-${tag.slug}ˋ">
  - `components/ArticleEditor.vue:103` — <input
  - `components/ArticleEditor.vue:112` — <input v-model="form.summary" data-testid="summary" maxlength="320">
  - `components/ArticleEditor.vue:124` — <select v-model="item.kind" :data-testid="ˋreference-kind-${index}ˋ">
  - `components/ArticleEditor.vue:131` — <input v-model="item.display_title" maxlength="180" :data-testid="ˋreference-title-${index}ˋ">
  - `components/ArticleEditor.vue:133` — <button class="button-secondary self-end" type="button" :data-testid="ˋreference-remove-${index}ˋ" @click="form.references.splice(index, 1)">
  - `components/ArticleEditor.vue:139` — <input v-model="item.url" type="url" pattern="https?://.+" :data-testid="ˋreference-url-${index}ˋ" placeholder="https://">
  - `components/ArticleEditor.vue:144` — <select v-model="item.target_type" :data-testid="ˋreference-target-type-${index}ˋ">
  - `components/ArticleEditor.vue:152` — <select :value="item.target_id ?? ''" :data-testid="ˋreference-target-${index}ˋ" @change="assignInternalTarget(item, ($event.target as HTMLSelectElement).value)">
  - `components/ArticleEditor.vue:161` — <button class="button-secondary mt-3" type="button" data-testid="reference-add" :disabled="form.references.length >= 20" @click="addReference">
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/WritingWorkspace.vue:4` — <button type="button" :aria-pressed="panel === 'body'" :aria-controls="bodyId" @click="showPanel('body')">正文</button>
  - `components/WritingWorkspace.vue:5` — <button type="button" :aria-pressed="panel === 'settings'" :aria-controls="settingsId" @click="showPanel('settings')">设置</button>
  - `components/WritingWorkspace.vue:12` — <button type="button" :aria-pressed="mode === 'markdown'" :aria-controls="markdownId" @click="mode = 'markdown'">Markdown</button>
  - `components/WritingWorkspace.vue:13` — <button type="button" :aria-pressed="mode === 'preview'" :aria-controls="previewId" @click="mode = 'preview'">预览</button>
  - `components/MarkdownMediaField.vue:8` — <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/avif" multiple @change="selectFiles">
  - `components/MarkdownMediaField.vue:14` — <button type="button" @click="formatSelection('heading')">标题</button>
  - `components/MarkdownMediaField.vue:15` — <button type="button" @click="formatSelection('bold')">加粗</button>
  - `components/MarkdownMediaField.vue:16` — <button type="button" @click="formatSelection('quote')">引用</button>
  - `components/MarkdownMediaField.vue:17` — <button type="button" @click="formatSelection('link')">链接</button>
  - `components/MarkdownMediaField.vue:19` — <textarea
  - `components/MarkdownMediaField.vue:28` — @click="rememberSelection"
  - `components/MarkdownMediaField.vue:43` — <button class="admin-inline-action" type="button" @click="retry(task)">重试</button>
  - `components/MarkdownMediaField.vue:44` — <button class="admin-inline-action text-ee-danger-ink" type="button" @click="remove(task)">移除占位</button>
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/StudioPublishConfirmation.vue:2` — <AdminDialog :model-value="open" :labelledby="titleId" @update:model-value="settle(false)">
  - `components/StudioPublishConfirmation.vue:6` — <button type="button" class="button-secondary" @click="settle(false)">取消</button>
  - `components/StudioPublishConfirmation.vue:7` — <button type="button" class="button-primary" data-testid="confirm-publish" @click="settle(true)">确认发布</button>
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"

## R07 · `/admin/articles/[id]/preview`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/articles/[id]/preview.vue`。
- 共用落点：`admin-core`, `NavigationArrow`, `ReadingLayout`, `MarkdownArticle`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `ContentToc`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/articles/[id]/preview.vue:3` — <NuxtLink :to="'/admin/articles/' + article.id + '/edit'" class="admin-back-link"><NavigationArrow direction="left" /> 返回编辑</NuxtLink>
  - `pages/admin/articles/[id]/preview.vue:6` — <NuxtLink :to="'/admin/articles/' + article.id + '/revisions'" class="button-secondary">版本历史</NuxtLink>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/ContentToc.vue:12` — @click="navigateHeading"
  - `components/ContentToc.vue:35` — @click="navigateHeading"

## R08 · `/admin/articles/[id]/revisions`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/articles/[id]/revisions.vue`。
- 共用落点：`admin-core`, `NavigationArrow`, `MarkdownArticle`, `AdminDialog`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/articles/[id]/revisions.vue:3` — <NuxtLink class="admin-back-link" :to="ˋ/admin/articles/${articleId}/editˋ"><NavigationArrow direction="left" /> 返回编辑器</NuxtLink>
  - `pages/admin/articles/[id]/revisions.vue:14` — <NuxtLink class="button-secondary" :to="ˋ/admin/articles/${articleId}/previewˋ">
  - `pages/admin/articles/[id]/revisions.vue:26` — <button v-if="error" class="button-secondary" type="button" @click="load">重新读取历史</button>
  - `pages/admin/articles/[id]/revisions.vue:59` — <button
  - `pages/admin/articles/[id]/revisions.vue:63` — @click="compareTo(revision)"
  - `pages/admin/articles/[id]/revisions.vue:67` — <button
  - `pages/admin/articles/[id]/revisions.vue:73` — @click="openRollback(revision)"
  - `pages/admin/articles/[id]/revisions.vue:77` — <button
  - `pages/admin/articles/[id]/revisions.vue:82` — @click="viewRevision(revision)"
  - `pages/admin/articles/[id]/revisions.vue:91` — <button class="button-secondary" type="button" :disabled="offset <= 0" @click="changeOffset(offset - 20)">
  - `pages/admin/articles/[id]/revisions.vue:95` — <button class="button-secondary" type="button" :disabled="offset + 20 >= total" @click="changeOffset(offset + 20)">
  - `pages/admin/articles/[id]/revisions.vue:141` — <AdminDialog :model-value="Boolean(rollbackTarget)" labelledby="rollback-title" test-id="rollback-modal" :close-disabled="acting" @update:model-value="rollbackTarget = null">
  - `pages/admin/articles/[id]/revisions.vue:151` — <button class="button-secondary" type="button" :disabled="acting" @click="rollbackTarget = null">取消</button>
  - `pages/admin/articles/[id]/revisions.vue:152` — <button
  - `pages/admin/articles/[id]/revisions.vue:157` — @click="rollback"
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R09 · `/admin/articles`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/articles/index.vue`。
- 共用落点：`admin-core`, `StudioContentList`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `PaginationNav`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/StudioContentList.vue:5` — <NuxtLink class="button-primary" :to="ˋ${path}/newˋ"><StudioIcon name="plus" />{{ createLabel }}</NuxtLink>
  - `components/StudioContentList.vue:8` — <NuxtLink v-for="filter in filters" :key="filter.value" :to="{ path, query: { q: query.q || undefined, status: filter.value || undefined } }" :aria-current="query.status === filter.value ? 'page' : undefined">
  - `components/StudioContentList.vue:14` — <div><strong>本页 {{ unpublished.length }} 项有未发布修改</strong><p>草稿已保存，访客看到的仍是上次发布的版本。</p><NuxtLink :to="ˋ${path}/${unpublished[0]!.id}/editˋ">继续编辑</NuxtLink></div>
  - `components/StudioContentList.vue:18` — <form class="list-search" role="search" @submit.prevent="search">
  - `components/StudioContentList.vue:20` — <input :id="ˋ${kind}-searchˋ" v-model="term" type="search" maxlength="200" :placeholder="searchLabel">
  - `components/StudioContentList.vue:21` — <button type="submit" class="button-secondary" aria-label="搜索"><StudioIcon name="search" /></button>
  - `components/StudioContentList.vue:26` — <h2>列表读取失败</h2><p>搜索条件已保留，请重试。</p><button type="button" class="button-secondary" @click="refresh()">重新读取</button>
  - `components/StudioContentList.vue:34` — <h2><NuxtLink :to="ˋ${path}/${item.id}/editˋ">{{ titleOf(item) }}</NuxtLink></h2>
  - `components/StudioContentList.vue:38` — <a v-if="item.repository_url" :href="item.repository_url" target="_blank" rel="noopener noreferrer">仓库 <StudioIcon name="external-link" /></a>
  - `components/StudioContentList.vue:39` — <a v-if="item.website_url" :href="item.website_url" target="_blank" rel="noopener noreferrer">站点 <StudioIcon name="external-link" /></a>
  - `components/StudioContentList.vue:45` — <NuxtLink :to="ˋ${path}/${item.id}/editˋ" class="list-edit">编辑</NuxtLink>
  - `components/StudioContentList.vue:46` — <button type="button" class="list-more" :aria-label="ˋ${titleOf(item)}的更多操作ˋ" @click="selected = item"><StudioIcon name="dots" />更多</button>
  - `components/StudioContentList.vue:53` — <NuxtLink v-if="query.q || query.status || page > 1" class="button-secondary" :to="path">清除搜索与筛选</NuxtLink>
  - `components/StudioContentList.vue:54` — <NuxtLink v-else class="button-secondary" :to="ˋ${path}/newˋ">{{ createLabel }}</NuxtLink>
  - `components/StudioContentList.vue:58` — <AdminDialog :model-value="!!selected" labelledby="list-dialog-title" :close-disabled="deleting" @update:model-value="selected = null">
  - `components/StudioContentList.vue:61` — <button type="button" class="button-secondary" :disabled="deleting" @click="selected = null">关闭</button>
  - `components/StudioContentList.vue:62` — <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="ˋ${path}/${selected.id}/previewˋ">预览草稿</NuxtLink>
  - `components/StudioContentList.vue:63` — <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="ˋ${path}/${selected.id}/revisionsˋ">版本历史</NuxtLink>
  - `components/StudioContentList.vue:64` — <NuxtLink v-if="selected.public_path" class="button-secondary" :to="selected.public_path">查看已发布版本</NuxtLink>
  - `components/StudioContentList.vue:66` — <button type="button" class="admin-danger-button" :disabled="deleting" @click="trash">{{ deleting ? '正在移入回收站…' : '移入回收站' }}</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink

## R10 · `/admin/articles/new`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/articles/new.vue`。
- 共用落点：`admin-core`, `NavigationArrow`, `WritingWorkspace`, `MarkdownMediaField`, `MarkdownArticle`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `MediaUploader`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/articles/new.vue:3` — <NuxtLink to="/admin/articles" class="admin-back-link"><NavigationArrow direction="left" /> 返回文章</NuxtLink>
  - `pages/admin/articles/new.vue:8` — </div><button class="button-primary" type="submit" form="writing-create" data-testid="create-draft" :disabled="!hydrated || submitting">
  - `pages/admin/articles/new.vue:11` — <form id="writing-create" class="admin-form-panel" novalidate @submit.prevent.self="create">
  - `pages/admin/articles/new.vue:17` — <input
  - `pages/admin/articles/new.vue:40` — <select v-model="form.category_id" data-testid="new-category">
  - `pages/admin/articles/new.vue:51` — <input v-model="form.tag_ids" type="checkbox" :value="tag.id" :data-testid="ˋnew-tag-${tag.slug}ˋ">
  - `pages/admin/articles/new.vue:60` — <input
  - `pages/admin/articles/new.vue:79` — <textarea v-model="form.summary" rows="3" maxlength="320" />
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/WritingWorkspace.vue:4` — <button type="button" :aria-pressed="panel === 'body'" :aria-controls="bodyId" @click="showPanel('body')">正文</button>
  - `components/WritingWorkspace.vue:5` — <button type="button" :aria-pressed="panel === 'settings'" :aria-controls="settingsId" @click="showPanel('settings')">设置</button>
  - `components/WritingWorkspace.vue:12` — <button type="button" :aria-pressed="mode === 'markdown'" :aria-controls="markdownId" @click="mode = 'markdown'">Markdown</button>
  - `components/WritingWorkspace.vue:13` — <button type="button" :aria-pressed="mode === 'preview'" :aria-controls="previewId" @click="mode = 'preview'">预览</button>
  - `components/MarkdownMediaField.vue:8` — <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/avif" multiple @change="selectFiles">
  - `components/MarkdownMediaField.vue:14` — <button type="button" @click="formatSelection('heading')">标题</button>
  - `components/MarkdownMediaField.vue:15` — <button type="button" @click="formatSelection('bold')">加粗</button>
  - `components/MarkdownMediaField.vue:16` — <button type="button" @click="formatSelection('quote')">引用</button>
  - `components/MarkdownMediaField.vue:17` — <button type="button" @click="formatSelection('link')">链接</button>
  - `components/MarkdownMediaField.vue:19` — <textarea
  - `components/MarkdownMediaField.vue:28` — @click="rememberSelection"
  - `components/MarkdownMediaField.vue:43` — <button class="admin-inline-action" type="button" @click="retry(task)">重试</button>
  - `components/MarkdownMediaField.vue:44` — <button class="admin-inline-action text-ee-danger-ink" type="button" @click="remove(task)">移除占位</button>
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"

## R11 · `/admin/assistant`

- 阶段：排除；桌面：排除；移动入口：排除。
- 源码：`apps/web/pages/admin/assistant.vue`。
- 共用落点：`admin-core`, `StudioIcon`, `AdminDialog`, `AdminThemeToggle`, `AdminCoreNavigation`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/assistant.vue:5` — <div class="am-tools"><span v-if="snapshot">更新于 {{ time(snapshot.observed_at) }}</span><button :disabled="loading" @click="refresh"><StudioIcon name="refresh" />{{ loading ? '刷新中…' : '刷新状态' }}</button><NuxtLink :to="viewLink('maintenance')">高级维护</NuxtLink></div>
  - `pages/admin/assistant.vue:7` — <nav class="am-tabs" aria-label="助手管理视图"><NuxtLink :to="viewLink('overview')" :aria-current="view === 'overview' ? 'page' : undefined">概览</NuxtLink><NuxtLink :to="viewLink('test')" :aria-current="view === 'test' ? 'page' : undefined">试问</NuxtLink></nav>
  - `pages/admin/assistant.vue:16` — <div class="am-actions"><NuxtLink v-if="isOpen" class="button-primary" :to="viewLink('test')">试问助手</NuxtLink><button :class="isOpen ? 'am-link' : 'button-primary'" :disabled="mutating || (!isOpen && (stale || !canEnable))" @click="confirmAvailability">{{ isOpen ? '关闭对外问答' : '向访客开放' }}</button><NuxtLink v-if="!isOpen" class="am-link" :to="viewLink('test')">试问助手</NuxtLink></div>
  - `pages/admin/assistant.vue:19` — <div v-if="issues.length" class="am-issues"><div v-for="issue in issues" :key="issue.title" class="am-issue"><StudioIcon name="alert-circle-filled" /><div><h3>{{ issue.title }}</h3><p>{{ issue.body }}</p><button v-if="issue.action === 'budget'" class="am-link" @click="openBudget">修改预算 →</button><button v-else-if="issue.action === 'sync'" class="am-link" @click="showSync = true; filter = 'failed'">查看失败内容 →</button><NuxtLink v-else class="am-link" :to="viewLink('maintenance')">查看处理说明 →</NuxtLink></div></div></div>
  - `pages/admin/assistant.vue:25` — <div class="am-row-actions"><button class="am-link" aria-label="修改预算" :disabled="!budget || stale" @click="openBudget">修改预算 ↗</button><button class="am-link" :aria-expanded="showCosts" @click="showCosts = !showCosts">费用明细 {{ showCosts ? '−' : '+' }}</button></div>
  - `pages/admin/assistant.vue:27` — <section class="am-row am-knowledge" aria-labelledby="sync-heading"><div><h2 id="sync-heading">知识同步</h2><p>发布与更新后自动同步公开内容</p></div><div><h3>{{ syncSummary }}</h3><p>{{ snapshot.queue.latest_success_at ? ˋ最近完成 ${time(snapshot.queue.latest_success_at)}ˋ : '尚无成功同步记录' }}</p></div><div class="am-row-actions"><button class="am-link" :aria-expanded="showSync" @click="showSync = !showSync">查看内容 {{ showSync ? '−' : '↗' }}</button></div></section>
  - `pages/admin/assistant.vue:33` — <AdminDialog v-model="panelOpen" :labelledby="panelTitleId" :close-disabled="mutating" :width-class="['sync', 'maintenance'].includes(panel) ? 'am-dialog-wide' : ''">
  - `pages/admin/assistant.vue:35` — <div class="am-dialog-toolbar"><button aria-label="关闭弹窗" :disabled="mutating" @click="closePanel"><StudioIcon name="x" /></button></div>
  - `pages/admin/assistant.vue:41` — <div class="am-section-heading"><h2 id="sync-title" tabindex="-1">内容同步记录</h2><div class="am-filter"><label for="sync-filter">状态</label><select id="sync-filter" v-model="filter" @change="offset = 0"><option value="">全部</option><option value="pending">待同步</option><option value="leased">同步中</option><option value="failed">失败</option><option value="succeeded">已处理</option></select></div></div>
  - `pages/admin/assistant.vue:43` — <div v-for="task in tasks?.items" :key="task.id" class="am-task"><div><strong>{{ task.title }}</strong><p>{{ typeLabel[task.source_type] }} · {{ time(task.updated_at) }}</p><p v-if="task.message">{{ task.message }}</p></div><span>{{ syncLabel(task) }}</span><button v-if="canRetry(task)" class="am-link" :disabled="mutating" @click="retry(task)">重试此内容同步</button><NuxtLink v-else-if="task.status === 'failed'" class="am-link" :to="viewLink('maintenance')">查看诊断</NuxtLink><span v-else /></div>
  - `pages/admin/assistant.vue:44` — <p v-if="!tasks?.items.length" class="am-hint">当前筛选下暂无同步任务。</p><div class="am-pagination"><button :disabled="!offset || loading" @click="offset = Math.max(0, offset - 10)">上一页</button><span>{{ tasks?.total ? offset + 1 : 0 }}–{{ Math.min(offset + 10, tasks?.total || 0) }} / {{ tasks?.total || 0 }}</span><button :disabled="offset + 10 >= (tasks?.total || 0) || loading" @click="offset += 10">下一页</button></div>
  - `pages/admin/assistant.vue:48` — <div class="am-maintenance-row"><div><h3>后台试问</h3><p>{{ management?.trial_stopped ? '全部问答已被停止。运行条件验证通过后，可单独恢复后台试问。' : '普通对外关闭不影响试问；资格与维护保护仍然生效。' }}</p></div><button v-if="management?.trial_stopped" class="button-secondary" :disabled="mutating" @click="resumeTrial">恢复后台试问</button><NuxtLink v-else class="am-link" :to="viewLink('test')">前往试问</NuxtLink></div>
  - `pages/admin/assistant.vue:49` — <div class="am-maintenance-row"><div><h3>索引维护</h3><p>重建使用今日总预算，旧索引继续提供回答。切换后全部问答暂停，需要重新验证运行资格。</p><p v-if="snapshot.operation" class="assistant-operation">当前操作：{{ operationLabel(snapshot.operation.status) }}</p></div><div class="am-row-actions"><button class="button-secondary" :disabled="mutating || nonterminalOperation" @click="confirmRebuild">重建公开知识索引</button><button v-if="snapshot.operation?.status === 'ready_to_switch'" class="button-primary" :disabled="mutating" @click="confirmFinalize">切换到新索引</button></div></div>
  - `pages/admin/assistant.vue:50` — <div class="am-maintenance-row"><div><h3>紧急停止全部问答</h3><p>同时撤销访客和管理员执行，已发送的调用仍可能产生费用。</p></div><button class="am-danger" :disabled="mutating" @click="confirmEmergency">紧急停止全部问答</button></div>
  - `pages/admin/assistant.vue:55` — <form v-if="panel === 'budget'" class="am-budget-form" @submit.prevent="saveBudget"><h2 id="budget-title" tabindex="-1">修改每日预算</h2><p>北京时间每日 00:00 重置。设为 0 暂停新增付费调用。</p><label for="daily-budget">每日总预算（元）</label><input id="daily-budget" v-model="budgetInput" inputmode="decimal" autocomplete="off" autofocus><p>当前已用 {{ money(management?.usage_known && !stale ? budget?.settled_micro_cny : null) }}，预留 {{ money(management?.usage_known && !stale ? budget?.reserved_micro_cny : null) }}。部署允许上限 {{ money(budget?.ceiling_micro_cny) }}。</p><p>每日上限从 {{ money(budget?.cap_micro_cny) }} 调整为 {{ money(amountToMicro(budgetInput)) }}。</p><p v-if="budgetError" class="am-alert" role="alert">{{ budgetError }}</p><div class="am-actions"><button type="button" class="button-secondary" :disabled="mutating" @click="budgetOpen = false">取消</button><button class="button-primary" :disabled="mutating">{{ mutating ? '保存中…' : '保存预算' }}</button></div></form>
  - `pages/admin/assistant.vue:56` — <div v-if="panel === 'confirm'" class="am-budget-form"><h2 id="confirm-title" tabindex="-1">{{ confirmation.title }}</h2><p>{{ confirmation.body }}</p><div class="am-actions"><button class="button-secondary" :disabled="mutating" @click="confirmOpen = false">取消</button><button :class="confirmation.danger ? 'am-danger' : 'button-primary'" :disabled="mutating" @click="runConfirmed">{{ confirmation.title }}</button></div></div>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R12 · `/admin/books/[id]/edit`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/books/[id]/edit.vue`。
- 共用落点：`admin-core`, `BookNoteEditor`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `NavigationArrow`, `WritingWorkspace`, `MarkdownMediaField`, `MediaUploader`, `MarkdownArticle`, `StudioPublishConfirmation`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/BookNoteEditor.vue:3` — <NuxtLink class="admin-back-link" to="/admin/books"><NavigationArrow direction="left" /> 返回列表</NuxtLink>
  - `components/BookNoteEditor.vue:13` — <button type="button" class="button-primary" data-testid="publish-book" :disabled="publishing || saveState === 'conflict'" @click="publish">
  - `components/BookNoteEditor.vue:26` — <button class="button-secondary" type="button" @click="retrySave">重试保存</button>
  - `components/BookNoteEditor.vue:31` — <label class="field"><span>书名</span><input v-model="form.book_title" data-testid="book-title" placeholder="输入书名" maxlength="180" required></label>
  - `components/BookNoteEditor.vue:35` — <label class="field"><span>作者</span><input v-model="form.author" data-testid="book-author" maxlength="180" required></label>
  - `components/BookNoteEditor.vue:38` — <label class="field"><span>阅读状态</span><select v-model="form.reading_status" data-testid="book-reading-status"><option value="planned">想读</option><option value="reading">在读</option><option value="completed">读完</option><option value="paused">暂停</option></select></label>
  - `components/BookNoteEditor.vue:39` — <label class="field"><span>阅读日期</span><input v-model="form.reading_date" type="date"></label>
  - `components/BookNoteEditor.vue:40` — <label class="field"><span>评分</span><select v-model="form.rating"><option :value="null">未评分</option><option v-for="score in 5" :key="score" :value="score">{{ score }} / 5</option></select></label>
  - `components/BookNoteEditor.vue:44` — <label class="field"><span>封面 URL</span><input v-model="form.cover_url" type="url" pattern="https?://.+" placeholder="https://…"></label>
  - `components/BookNoteEditor.vue:50` — <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
  - `components/BookNoteEditor.vue:51` — <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="book-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" :disabled="current.status === 'published'"></label>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/WritingWorkspace.vue:4` — <button type="button" :aria-pressed="panel === 'body'" :aria-controls="bodyId" @click="showPanel('body')">正文</button>
  - `components/WritingWorkspace.vue:5` — <button type="button" :aria-pressed="panel === 'settings'" :aria-controls="settingsId" @click="showPanel('settings')">设置</button>
  - `components/WritingWorkspace.vue:12` — <button type="button" :aria-pressed="mode === 'markdown'" :aria-controls="markdownId" @click="mode = 'markdown'">Markdown</button>
  - `components/WritingWorkspace.vue:13` — <button type="button" :aria-pressed="mode === 'preview'" :aria-controls="previewId" @click="mode = 'preview'">预览</button>
  - `components/MarkdownMediaField.vue:8` — <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/avif" multiple @change="selectFiles">
  - `components/MarkdownMediaField.vue:14` — <button type="button" @click="formatSelection('heading')">标题</button>
  - `components/MarkdownMediaField.vue:15` — <button type="button" @click="formatSelection('bold')">加粗</button>
  - `components/MarkdownMediaField.vue:16` — <button type="button" @click="formatSelection('quote')">引用</button>
  - `components/MarkdownMediaField.vue:17` — <button type="button" @click="formatSelection('link')">链接</button>
  - `components/MarkdownMediaField.vue:19` — <textarea
  - `components/MarkdownMediaField.vue:28` — @click="rememberSelection"
  - `components/MarkdownMediaField.vue:43` — <button class="admin-inline-action" type="button" @click="retry(task)">重试</button>
  - `components/MarkdownMediaField.vue:44` — <button class="admin-inline-action text-ee-danger-ink" type="button" @click="remove(task)">移除占位</button>
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/StudioPublishConfirmation.vue:2` — <AdminDialog :model-value="open" :labelledby="titleId" @update:model-value="settle(false)">
  - `components/StudioPublishConfirmation.vue:6` — <button type="button" class="button-secondary" @click="settle(false)">取消</button>
  - `components/StudioPublishConfirmation.vue:7` — <button type="button" class="button-primary" data-testid="confirm-publish" @click="settle(true)">确认发布</button>

## R13 · `/admin/books`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/books/index.vue`。
- 共用落点：`admin-core`, `StudioContentList`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `PaginationNav`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/StudioContentList.vue:5` — <NuxtLink class="button-primary" :to="ˋ${path}/newˋ"><StudioIcon name="plus" />{{ createLabel }}</NuxtLink>
  - `components/StudioContentList.vue:8` — <NuxtLink v-for="filter in filters" :key="filter.value" :to="{ path, query: { q: query.q || undefined, status: filter.value || undefined } }" :aria-current="query.status === filter.value ? 'page' : undefined">
  - `components/StudioContentList.vue:14` — <div><strong>本页 {{ unpublished.length }} 项有未发布修改</strong><p>草稿已保存，访客看到的仍是上次发布的版本。</p><NuxtLink :to="ˋ${path}/${unpublished[0]!.id}/editˋ">继续编辑</NuxtLink></div>
  - `components/StudioContentList.vue:18` — <form class="list-search" role="search" @submit.prevent="search">
  - `components/StudioContentList.vue:20` — <input :id="ˋ${kind}-searchˋ" v-model="term" type="search" maxlength="200" :placeholder="searchLabel">
  - `components/StudioContentList.vue:21` — <button type="submit" class="button-secondary" aria-label="搜索"><StudioIcon name="search" /></button>
  - `components/StudioContentList.vue:26` — <h2>列表读取失败</h2><p>搜索条件已保留，请重试。</p><button type="button" class="button-secondary" @click="refresh()">重新读取</button>
  - `components/StudioContentList.vue:34` — <h2><NuxtLink :to="ˋ${path}/${item.id}/editˋ">{{ titleOf(item) }}</NuxtLink></h2>
  - `components/StudioContentList.vue:38` — <a v-if="item.repository_url" :href="item.repository_url" target="_blank" rel="noopener noreferrer">仓库 <StudioIcon name="external-link" /></a>
  - `components/StudioContentList.vue:39` — <a v-if="item.website_url" :href="item.website_url" target="_blank" rel="noopener noreferrer">站点 <StudioIcon name="external-link" /></a>
  - `components/StudioContentList.vue:45` — <NuxtLink :to="ˋ${path}/${item.id}/editˋ" class="list-edit">编辑</NuxtLink>
  - `components/StudioContentList.vue:46` — <button type="button" class="list-more" :aria-label="ˋ${titleOf(item)}的更多操作ˋ" @click="selected = item"><StudioIcon name="dots" />更多</button>
  - `components/StudioContentList.vue:53` — <NuxtLink v-if="query.q || query.status || page > 1" class="button-secondary" :to="path">清除搜索与筛选</NuxtLink>
  - `components/StudioContentList.vue:54` — <NuxtLink v-else class="button-secondary" :to="ˋ${path}/newˋ">{{ createLabel }}</NuxtLink>
  - `components/StudioContentList.vue:58` — <AdminDialog :model-value="!!selected" labelledby="list-dialog-title" :close-disabled="deleting" @update:model-value="selected = null">
  - `components/StudioContentList.vue:61` — <button type="button" class="button-secondary" :disabled="deleting" @click="selected = null">关闭</button>
  - `components/StudioContentList.vue:62` — <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="ˋ${path}/${selected.id}/previewˋ">预览草稿</NuxtLink>
  - `components/StudioContentList.vue:63` — <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="ˋ${path}/${selected.id}/revisionsˋ">版本历史</NuxtLink>
  - `components/StudioContentList.vue:64` — <NuxtLink v-if="selected.public_path" class="button-secondary" :to="selected.public_path">查看已发布版本</NuxtLink>
  - `components/StudioContentList.vue:66` — <button type="button" class="admin-danger-button" :disabled="deleting" @click="trash">{{ deleting ? '正在移入回收站…' : '移入回收站' }}</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink

## R14 · `/admin/books/new`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/books/new.vue`。
- 共用落点：`admin-core`, `NavigationArrow`, `WritingWorkspace`, `MarkdownMediaField`, `MediaUploader`, `MarkdownArticle`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/books/new.vue:3` — <NuxtLink to="/admin/books" class="admin-back-link"><NavigationArrow direction="left" /> 返回读书笔记</NuxtLink><header class="writing-create-header"><div><p class="admin-page-kicker">内容 / 读书 / 新建</p><h1 id="new-book-title" class="admin-page-title">新建读书笔记</h1><p class="admin-page-description">建立书籍元数据与笔记草稿，后续在编辑工作台自动保存。</p></div><button class="button-primary" type="submit" form="writing-create" data-testid="create-book" :disabled="!hydrated || submitting">{{ submitting ? '创建中…' : '创建笔记草稿' }}</button></header>
  - `pages/admin/books/new.vue:4` — <form id="writing-create" class="admin-form-panel" novalidate @submit.prevent.self="create">
  - `pages/admin/books/new.vue:7` — <template #title><label class="field"><span>书名</span><input v-model="form.book_title" data-testid="new-book-title" placeholder="输入书名" maxlength="180" required @input="syncSlug"></label></template>
  - `pages/admin/books/new.vue:10` — <label class="field"><span>作者</span><input v-model="form.author" data-testid="new-book-author" maxlength="180" required></label>
  - `pages/admin/books/new.vue:13` — <label class="field"><span>阅读状态</span><select v-model="form.reading_status" data-testid="new-book-reading-status"><option value="planned">想读</option><option value="reading">在读</option><option value="completed">读完</option><option value="paused">暂停</option></select></label>
  - `pages/admin/books/new.vue:14` — <label class="field"><span>阅读日期</span><input v-model="form.reading_date" type="date"></label>
  - `pages/admin/books/new.vue:15` — <label class="field"><span>评分</span><select v-model="form.rating"><option :value="null">未评分</option><option v-for="score in 5" :key="score" :value="score">{{ score }} / 5</option></select></label>
  - `pages/admin/books/new.vue:19` — <label class="field"><span>封面 URL</span><input v-model="form.cover_url" type="url" pattern="https?://.+" placeholder="https://…"></label>
  - `pages/admin/books/new.vue:25` — <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
  - `pages/admin/books/new.vue:26` — <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="new-book-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" @input="slugTouched = true"></label>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/WritingWorkspace.vue:4` — <button type="button" :aria-pressed="panel === 'body'" :aria-controls="bodyId" @click="showPanel('body')">正文</button>
  - `components/WritingWorkspace.vue:5` — <button type="button" :aria-pressed="panel === 'settings'" :aria-controls="settingsId" @click="showPanel('settings')">设置</button>
  - `components/WritingWorkspace.vue:12` — <button type="button" :aria-pressed="mode === 'markdown'" :aria-controls="markdownId" @click="mode = 'markdown'">Markdown</button>
  - `components/WritingWorkspace.vue:13` — <button type="button" :aria-pressed="mode === 'preview'" :aria-controls="previewId" @click="mode = 'preview'">预览</button>
  - `components/MarkdownMediaField.vue:8` — <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/avif" multiple @change="selectFiles">
  - `components/MarkdownMediaField.vue:14` — <button type="button" @click="formatSelection('heading')">标题</button>
  - `components/MarkdownMediaField.vue:15` — <button type="button" @click="formatSelection('bold')">加粗</button>
  - `components/MarkdownMediaField.vue:16` — <button type="button" @click="formatSelection('quote')">引用</button>
  - `components/MarkdownMediaField.vue:17` — <button type="button" @click="formatSelection('link')">链接</button>
  - `components/MarkdownMediaField.vue:19` — <textarea
  - `components/MarkdownMediaField.vue:28` — @click="rememberSelection"
  - `components/MarkdownMediaField.vue:43` — <button class="admin-inline-action" type="button" @click="retry(task)">重试</button>
  - `components/MarkdownMediaField.vue:44` — <button class="admin-inline-action text-ee-danger-ink" type="button" @click="remove(task)">移除占位</button>
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R15 · `/admin/content`

- 阶段：P4 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/content.vue`。
- 共用落点：`admin-core`, `PaginationNav`, `NavigationArrow`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/content.vue:14` — <div class="flex flex-wrap gap-3"><button class="button-secondary" type="button" :disabled="trashBusy" @click="restore(item)">恢复</button><button class="button-secondary text-ee-danger-ink hover:bg-ee-danger-bg" type="button" :disabled="trashBusy" @click="purge(item)">永久删除</button></div>
  - `pages/admin/content.vue:26` — <input data-testid="import-markdown" type="file" accept=".md,text/markdown" multiple :disabled="importing" @change="importMarkdown">
  - `pages/admin/content.vue:31` — <NuxtLink class="admin-inline-action" :to="editPath(item)">{{ item.filename }} <NavigationArrow /> 编辑草稿</NuxtLink>
  - `pages/admin/content.vue:39` — <button class="button-secondary mt-4" data-testid="export-markdown" type="button" :disabled="exporting" @click="exportMarkdown">{{ exporting ? '正在导出…' : '导出 Markdown ZIP' }}</button>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R16 · `/admin/login`

- 阶段：P2 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/login.vue`。
- 共用落点：`AdminThemeToggle`, `StudioIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/login.vue:20` — <form class="admin-login-form" data-testid="admin-login-form" @submit.prevent="submit">
  - `pages/admin/login.vue:23` — <input
  - `pages/admin/login.vue:35` — <input
  - `pages/admin/login.vue:46` — <button
  - `pages/admin/login.vue:58` — <NuxtLink to="/admin/recover" class="admin-login-back">忘记密码</NuxtLink>
  - `pages/admin/login.vue:59` — <NuxtLink to="/" class="admin-login-back">返回 Gavin</NuxtLink>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"

## R17 · `/admin/media`

- 阶段：P2 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/media.vue`。
- 共用落点：`admin-core`, `MediaUploader`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/media.vue:6` — </div><a href="#media-add" class="button-primary">添加图片</a></header>
  - `pages/admin/media.vue:12` — <label v-if="copyError" class="field mt-3"><span>可手动选择并复制</span><textarea :value="copyValue" readonly rows="3" @focus="($event.target as HTMLTextAreaElement).select()" /></label>
  - `pages/admin/media.vue:13` — <NuxtLink class="admin-inline-action mt-2" to="/admin/articles">返回文章管理</NuxtLink>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R18 · `/admin/profile`

- 阶段：P4 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/profile.vue`。
- 共用落点：`admin-core`, `MediaUploader`, `StudioIcon`, `ResumeSyncStatus`, `ProfileCard`, `AdminThemeToggle`, `AdminCoreNavigation`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/profile.vue:9` — <a href="#profile-preview" class="button-secondary">查看名片</a>
  - `pages/admin/profile.vue:11` — <button
  - `pages/admin/profile.vue:16` — @click="save"
  - `pages/admin/profile.vue:30` — <button type="button" class="font-semibold underline" data-testid="profile-refresh" @click="reload">刷新页面</button>
  - `pages/admin/profile.vue:41` — <nav aria-label="名片分区" class="profile-sections"><a href="#profile-basics">基本资料</a><a href="#profile-skills">技能与联系</a></nav>
  - `pages/admin/profile.vue:49` — <input v-model="form.name" data-testid="profile-name" maxlength="80">
  - `pages/admin/profile.vue:53` — <input v-model="form.title" data-testid="profile-title" maxlength="120">
  - `pages/admin/profile.vue:57` — <textarea v-model="form.bio" data-testid="profile-bio" rows="3" maxlength="240" />
  - `pages/admin/profile.vue:74` — <input
  - `pages/admin/profile.vue:82` — <button
  - `pages/admin/profile.vue:87` — @click="form.avatar_url = null; avatarPreviewFailed = false"
  - `pages/admin/profile.vue:104` — <button
  - `pages/admin/profile.vue:110` — @click="moveSkill(index, -1)"
  - `pages/admin/profile.vue:112` — <button
  - `pages/admin/profile.vue:118` — @click="moveSkill(index, 1)"
  - `pages/admin/profile.vue:121` — <button
  - `pages/admin/profile.vue:126` — @click="removeSkill(index)"
  - `pages/admin/profile.vue:131` — <input
  - `pages/admin/profile.vue:139` — <button
  - `pages/admin/profile.vue:144` — @click="addSkill"
  - `pages/admin/profile.vue:154` — <input v-model="form.city" data-testid="profile-city" maxlength="80" placeholder="只填城市级信息">
  - `pages/admin/profile.vue:158` — <input v-model="form.github_url" data-testid="profile-github" type="url" placeholder="https://github.com/…">
  - `pages/admin/profile.vue:162` — <input v-model="form.website_url" data-testid="profile-website" type="url" placeholder="https://…">
  - `pages/admin/profile.vue:166` — <input v-model="form.email" data-testid="profile-email" type="email" placeholder="gavin@example.com">
  - `pages/admin/profile.vue:170` — <input v-model="form.resume_url" data-testid="profile-resume" type="url" placeholder="https://…/resume.pdf">
  - `pages/admin/profile.vue:178` — <input v-model="form.city_visible" type="checkbox" data-testid="profile-city-visible">
  - `pages/admin/profile.vue:182` — <input v-model="form.email_visible" type="checkbox" data-testid="profile-email-visible">
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"
  - `components/ResumeSyncStatus.vue:23` — <button type="button" class="button-secondary" :disabled="disabled" data-testid="resume-refresh" @click="refreshResume">
  - `components/ResumeSyncStatus.vue:26` — <button v-if="loadError" type="button" class="button-secondary" @click="load">重试读取状态</button>
  - `components/ProfileCard.vue:25` — <h2 class="sys-panel-name"><NuxtLink v-if="variant === 'intro'" to="/about">{{ profile.name }}</NuxtLink><template v-else>{{ profile.name }}</template></h2>
  - `components/ProfileCard.vue:61` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:69` — <button
  - `components/ProfileCard.vue:76` — @click="copyEmail"
  - `components/ProfileCard.vue:92` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:107` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R19 · `/admin/projects/[id]/edit`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/projects/[id]/edit.vue`。
- 共用落点：`admin-core`, `ProjectEditor`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `NavigationArrow`, `WritingWorkspace`, `MarkdownMediaField`, `MarkdownArticle`, `StudioPublishConfirmation`, `MediaUploader`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/ProjectEditor.vue:3` — <NuxtLink class="admin-back-link" to="/admin/projects"><NavigationArrow direction="left" /> 返回列表</NuxtLink>
  - `components/ProjectEditor.vue:13` — <button
  - `components/ProjectEditor.vue:18` — @click="publish"
  - `components/ProjectEditor.vue:32` — <button class="button-secondary" type="button" @click="retrySave">重试保存</button>
  - `components/ProjectEditor.vue:37` — <label class="field"><span>项目名称</span><input v-model="form.title" data-testid="project-title" placeholder="输入项目名称" maxlength="180" required></label>
  - `components/ProjectEditor.vue:44` — <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="project-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" :disabled="current.status === 'published'"></label>
  - `components/ProjectEditor.vue:45` — <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
  - `components/ProjectEditor.vue:49` — <label class="field"><span>仓库 URL</span><input v-model="form.repository_url" type="url" pattern="https?://.+" placeholder="https://github.com/…"></label>
  - `components/ProjectEditor.vue:50` — <label class="field"><span>站点 URL</span><input v-model="form.website_url" type="url" pattern="https?://.+" placeholder="https://…"></label>
  - `components/ProjectEditor.vue:56` — <input v-model="form.article_ids" type="checkbox" :value="article.id">
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/WritingWorkspace.vue:4` — <button type="button" :aria-pressed="panel === 'body'" :aria-controls="bodyId" @click="showPanel('body')">正文</button>
  - `components/WritingWorkspace.vue:5` — <button type="button" :aria-pressed="panel === 'settings'" :aria-controls="settingsId" @click="showPanel('settings')">设置</button>
  - `components/WritingWorkspace.vue:12` — <button type="button" :aria-pressed="mode === 'markdown'" :aria-controls="markdownId" @click="mode = 'markdown'">Markdown</button>
  - `components/WritingWorkspace.vue:13` — <button type="button" :aria-pressed="mode === 'preview'" :aria-controls="previewId" @click="mode = 'preview'">预览</button>
  - `components/MarkdownMediaField.vue:8` — <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/avif" multiple @change="selectFiles">
  - `components/MarkdownMediaField.vue:14` — <button type="button" @click="formatSelection('heading')">标题</button>
  - `components/MarkdownMediaField.vue:15` — <button type="button" @click="formatSelection('bold')">加粗</button>
  - `components/MarkdownMediaField.vue:16` — <button type="button" @click="formatSelection('quote')">引用</button>
  - `components/MarkdownMediaField.vue:17` — <button type="button" @click="formatSelection('link')">链接</button>
  - `components/MarkdownMediaField.vue:19` — <textarea
  - `components/MarkdownMediaField.vue:28` — @click="rememberSelection"
  - `components/MarkdownMediaField.vue:43` — <button class="admin-inline-action" type="button" @click="retry(task)">重试</button>
  - `components/MarkdownMediaField.vue:44` — <button class="admin-inline-action text-ee-danger-ink" type="button" @click="remove(task)">移除占位</button>
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/StudioPublishConfirmation.vue:2` — <AdminDialog :model-value="open" :labelledby="titleId" @update:model-value="settle(false)">
  - `components/StudioPublishConfirmation.vue:6` — <button type="button" class="button-secondary" @click="settle(false)">取消</button>
  - `components/StudioPublishConfirmation.vue:7` — <button type="button" class="button-primary" data-testid="confirm-publish" @click="settle(true)">确认发布</button>
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"

## R20 · `/admin/projects`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/projects/index.vue`。
- 共用落点：`admin-core`, `StudioContentList`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `PaginationNav`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/StudioContentList.vue:5` — <NuxtLink class="button-primary" :to="ˋ${path}/newˋ"><StudioIcon name="plus" />{{ createLabel }}</NuxtLink>
  - `components/StudioContentList.vue:8` — <NuxtLink v-for="filter in filters" :key="filter.value" :to="{ path, query: { q: query.q || undefined, status: filter.value || undefined } }" :aria-current="query.status === filter.value ? 'page' : undefined">
  - `components/StudioContentList.vue:14` — <div><strong>本页 {{ unpublished.length }} 项有未发布修改</strong><p>草稿已保存，访客看到的仍是上次发布的版本。</p><NuxtLink :to="ˋ${path}/${unpublished[0]!.id}/editˋ">继续编辑</NuxtLink></div>
  - `components/StudioContentList.vue:18` — <form class="list-search" role="search" @submit.prevent="search">
  - `components/StudioContentList.vue:20` — <input :id="ˋ${kind}-searchˋ" v-model="term" type="search" maxlength="200" :placeholder="searchLabel">
  - `components/StudioContentList.vue:21` — <button type="submit" class="button-secondary" aria-label="搜索"><StudioIcon name="search" /></button>
  - `components/StudioContentList.vue:26` — <h2>列表读取失败</h2><p>搜索条件已保留，请重试。</p><button type="button" class="button-secondary" @click="refresh()">重新读取</button>
  - `components/StudioContentList.vue:34` — <h2><NuxtLink :to="ˋ${path}/${item.id}/editˋ">{{ titleOf(item) }}</NuxtLink></h2>
  - `components/StudioContentList.vue:38` — <a v-if="item.repository_url" :href="item.repository_url" target="_blank" rel="noopener noreferrer">仓库 <StudioIcon name="external-link" /></a>
  - `components/StudioContentList.vue:39` — <a v-if="item.website_url" :href="item.website_url" target="_blank" rel="noopener noreferrer">站点 <StudioIcon name="external-link" /></a>
  - `components/StudioContentList.vue:45` — <NuxtLink :to="ˋ${path}/${item.id}/editˋ" class="list-edit">编辑</NuxtLink>
  - `components/StudioContentList.vue:46` — <button type="button" class="list-more" :aria-label="ˋ${titleOf(item)}的更多操作ˋ" @click="selected = item"><StudioIcon name="dots" />更多</button>
  - `components/StudioContentList.vue:53` — <NuxtLink v-if="query.q || query.status || page > 1" class="button-secondary" :to="path">清除搜索与筛选</NuxtLink>
  - `components/StudioContentList.vue:54` — <NuxtLink v-else class="button-secondary" :to="ˋ${path}/newˋ">{{ createLabel }}</NuxtLink>
  - `components/StudioContentList.vue:58` — <AdminDialog :model-value="!!selected" labelledby="list-dialog-title" :close-disabled="deleting" @update:model-value="selected = null">
  - `components/StudioContentList.vue:61` — <button type="button" class="button-secondary" :disabled="deleting" @click="selected = null">关闭</button>
  - `components/StudioContentList.vue:62` — <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="ˋ${path}/${selected.id}/previewˋ">预览草稿</NuxtLink>
  - `components/StudioContentList.vue:63` — <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="ˋ${path}/${selected.id}/revisionsˋ">版本历史</NuxtLink>
  - `components/StudioContentList.vue:64` — <NuxtLink v-if="selected.public_path" class="button-secondary" :to="selected.public_path">查看已发布版本</NuxtLink>
  - `components/StudioContentList.vue:66` — <button type="button" class="admin-danger-button" :disabled="deleting" @click="trash">{{ deleting ? '正在移入回收站…' : '移入回收站' }}</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink

## R21 · `/admin/projects/new`

- 阶段：P3 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/projects/new.vue`。
- 共用落点：`admin-core`, `NavigationArrow`, `WritingWorkspace`, `MarkdownMediaField`, `MarkdownArticle`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`, `MediaUploader`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/projects/new.vue:3` — <NuxtLink to="/admin/projects" class="admin-back-link"><NavigationArrow direction="left" /> 返回项目</NuxtLink>
  - `pages/admin/projects/new.vue:4` — <header class="writing-create-header"><div><p class="admin-page-kicker">内容 / 项目 / 新建</p><h1 id="new-project-title" class="admin-page-title">新建项目</h1><p class="admin-page-description">记录项目边界、链接、关联文章与 Markdown 正文。</p></div><button class="button-primary" type="submit" form="writing-create" data-testid="create-project" :disabled="!hydrated || submitting">{{ submitting ? '创建中…' : '创建项目草稿' }}</button></header>
  - `pages/admin/projects/new.vue:5` — <form id="writing-create" class="admin-form-panel" novalidate @submit.prevent.self="create">
  - `pages/admin/projects/new.vue:9` — <label class="field"><span>项目名称</span><input v-model="form.title" data-testid="new-project-title" placeholder="输入项目名称" maxlength="180" required @input="syncSlug"></label>
  - `pages/admin/projects/new.vue:14` — <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="new-project-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" @input="slugTouched = true"></label>
  - `pages/admin/projects/new.vue:15` — <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
  - `pages/admin/projects/new.vue:17` — <section class="studio-settings-group" aria-label="项目地址"><h3>项目地址</h3><label class="field"><span>仓库 URL</span><input v-model="form.repository_url" type="url" pattern="https?://.+"></label><label class="field"><span>站点 URL</span><input v-model="form.website_url" type="url" pattern="https?://.+"></label></section>
  - `pages/admin/projects/new.vue:18` — <fieldset class="field studio-settings-group"><legend>关联文章</legend><div class="admin-choice-group admin-choice-group-grid"><label v-for="article in articles || []" :key="article.id" class="admin-choice"><input v-model="form.article_ids" type="checkbox" :value="article.id" :data-testid="ˋproject-article-${article.slug}ˋ"><span>{{ article.title }}</span></label><span v-if="!articles?.length" class="admin-empty-note">尚无文章。</span></div></fieldset>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/WritingWorkspace.vue:4` — <button type="button" :aria-pressed="panel === 'body'" :aria-controls="bodyId" @click="showPanel('body')">正文</button>
  - `components/WritingWorkspace.vue:5` — <button type="button" :aria-pressed="panel === 'settings'" :aria-controls="settingsId" @click="showPanel('settings')">设置</button>
  - `components/WritingWorkspace.vue:12` — <button type="button" :aria-pressed="mode === 'markdown'" :aria-controls="markdownId" @click="mode = 'markdown'">Markdown</button>
  - `components/WritingWorkspace.vue:13` — <button type="button" :aria-pressed="mode === 'preview'" :aria-controls="previewId" @click="mode = 'preview'">预览</button>
  - `components/MarkdownMediaField.vue:8` — <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/avif" multiple @change="selectFiles">
  - `components/MarkdownMediaField.vue:14` — <button type="button" @click="formatSelection('heading')">标题</button>
  - `components/MarkdownMediaField.vue:15` — <button type="button" @click="formatSelection('bold')">加粗</button>
  - `components/MarkdownMediaField.vue:16` — <button type="button" @click="formatSelection('quote')">引用</button>
  - `components/MarkdownMediaField.vue:17` — <button type="button" @click="formatSelection('link')">链接</button>
  - `components/MarkdownMediaField.vue:19` — <textarea
  - `components/MarkdownMediaField.vue:28` — @click="rememberSelection"
  - `components/MarkdownMediaField.vue:43` — <button class="admin-inline-action" type="button" @click="retry(task)">重试</button>
  - `components/MarkdownMediaField.vue:44` — <button class="admin-inline-action text-ee-danger-ink" type="button" @click="remove(task)">移除占位</button>
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink
  - `components/MediaUploader.vue:4` — <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
  - `components/MediaUploader.vue:10` — <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
  - `components/MediaUploader.vue:11` — <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
  - `components/MediaUploader.vue:12` — <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
  - `components/MediaUploader.vue:13` — <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
  - `components/MediaUploader.vue:14` — <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
  - `components/MediaUploader.vue:19` — <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
  - `components/MediaUploader.vue:20` — <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
  - `components/MediaUploader.vue:24` — <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
  - `components/MediaUploader.vue:27` — <input
  - `components/MediaUploader.vue:39` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
  - `components/MediaUploader.vue:40` — <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
  - `components/MediaUploader.vue:41` — <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
  - `components/MediaUploader.vue:42` — <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
  - `components/MediaUploader.vue:49` — <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
  - `components/MediaUploader.vue:62` — <input
  - `components/MediaUploader.vue:85` — <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
  - `components/MediaUploader.vue:86` — <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
  - `components/MediaUploader.vue:87` — <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
  - `components/MediaUploader.vue:110` — <button
  - `components/MediaUploader.vue:116` — @click="retryFailed"

## R22 · `/admin/recover`

- 阶段：P2 / P6；桌面/移动外壳与返回登录已核验；验证码与重设密码闭环排除。
- 源码：`apps/web/pages/admin/recover.vue`。
- 共用落点：`AdminThemeToggle`, `AccountPasswordForm`, `StudioIcon`, `AdminDialog`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/recover.vue:10` — <NuxtLink to="/admin/login" class="admin-login-back">返回登录</NuxtLink>
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AccountPasswordForm.vue:2` — <form class="space-y-5" @submit.prevent="prepareSubmit">
  - `components/AccountPasswordForm.vue:5` — <input v-model="currentPassword" type="password" autocomplete="current-password" maxlength="512" required :disabled="busy">
  - `components/AccountPasswordForm.vue:9` — <input v-model="newPassword" type="password" autocomplete="new-password" minlength="15" maxlength="128" required :disabled="busy" aria-describedby="password-policy">
  - `components/AccountPasswordForm.vue:14` — <input v-model="confirmation" type="password" autocomplete="new-password" minlength="15" maxlength="128" required :disabled="busy">
  - `components/AccountPasswordForm.vue:19` — <input v-model="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required :disabled="busy">
  - `components/AccountPasswordForm.vue:21` — <button type="button" class="button-secondary" :disabled="busy || cooldown > 0 || !mailAvailable" :aria-busy="sending" @click="sendCode">
  - `components/AccountPasswordForm.vue:29` — <button type="submit" class="button-primary" :disabled="busy || !challenge || !mailAvailable" :aria-busy="submitting">{{ submitting ? '正在更新…' : recovery ? '重设密码' : '修改密码' }}</button>
  - `components/AccountPasswordForm.vue:30` — <AdminDialog v-model="confirmOpen" labelledby="password-confirm-title" :close-disabled="submitting">
  - `components/AccountPasswordForm.vue:34` — <button type="button" class="button-secondary" :disabled="submitting" @click="confirmOpen = false">取消</button>
  - `components/AccountPasswordForm.vue:35` — <button type="button" class="button-primary" :disabled="submitting" @click="submit">确认更新密码</button>

## R23 · `/admin/taxonomy`

- 阶段：P2 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/admin/taxonomy.vue`。
- 共用落点：`admin-core`, `TaxonomyManager`, `AdminThemeToggle`, `AdminCoreNavigation`, `StudioIcon`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/admin/taxonomy.vue:9` — <nav aria-label="分类分区" class="taxonomy-sections"><a href="#taxonomy-categories">栏目</a><a href="#taxonomy-tags">标签</a></nav>
  - `layouts/admin-core.vue:3` — <a class="skip-link" href="#admin-main">跳到主要内容</a>
  - `layouts/admin-core.vue:6` — <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:11` — <button
  - `layouts/admin-core.vue:19` — @click="toggleMenu"
  - `layouts/admin-core.vue:33` — <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
  - `layouts/admin-core.vue:42` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:44` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `layouts/admin-core.vue:54` — @click.self="closeMenu(true)"
  - `layouts/admin-core.vue:66` — <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
  - `layouts/admin-core.vue:74` — <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
  - `layouts/admin-core.vue:76` — <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
  - `components/TaxonomyManager.vue:18` — <button type="button" class="admin-inline-action" :disabled="submitting" @click="edit(item)">编辑</button>
  - `components/TaxonomyManager.vue:19` — <button type="button" class="admin-inline-action text-ee-danger-ink" :disabled="submitting" @click="remove(item)">删除</button>
  - `components/TaxonomyManager.vue:24` — <form class="taxonomy-manager__form space-y-4" @submit.prevent="submit">
  - `components/TaxonomyManager.vue:28` — <input ref="nameInput" v-model="form.name" :data-testid="ˋ${kind}-nameˋ" maxlength="80" required @input="syncSlug">
  - `components/TaxonomyManager.vue:32` — <input v-model="form.slug" :data-testid="ˋ${kind}-slugˋ" maxlength="80" required @input="slugTouched = true">
  - `components/TaxonomyManager.vue:36` — <input v-model="form.description" maxlength="240">
  - `components/TaxonomyManager.vue:40` — <button v-if="editingId" type="button" class="button-secondary" @click="reset">取消编辑</button>
  - `components/TaxonomyManager.vue:41` — <button class="button-primary" :data-testid="ˋ${kind}-submitˋ" :disabled="submitting">
  - `components/AdminThemeToggle.vue:2` — <button
  - `components/AdminThemeToggle.vue:9` — @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  - `components/AdminCoreNavigation.vue:5` — <NuxtLink

## R24 · `/archive`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/archive.vue`。
- 共用落点：`default`, `SectionHeading`, `PageHeroArtwork`, `PaginationNav`, `SiteHeader`, `SiteFooter`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/archive.vue:34` — <NuxtLink :to="article.public_path" data-focus-card class="archive-row">
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R25 · `/articles`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/articles/index.vue`。
- 共用落点：`default`, `PublicPageHero`, `ArticleCard`, `PaginationNav`, `SiteHeader`, `SiteFooter`, `SectionHeading`, `PageHeroArtwork`, `BlueprintWatermark`, `NavigationArrow`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/articles/index.vue:16` — <NuxtLink
  - `pages/articles/index.vue:23` — <NuxtLink
  - `pages/articles/index.vue:35` — <NuxtLink
  - `pages/articles/index.vue:45` — <NuxtLink to="/search" class="filter-search articles-search-link">
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/ArticleCard.vue:18` — <h2 class="article-list-title ee-heading"><NuxtLink :to="article.public_path">{{ article.title }}</NuxtLink></h2>
  - `components/ArticleCard.vue:22` — <NuxtLink :to="article.public_path" class="article-list-arrow" :aria-label="ˋ阅读：${article.title}ˋ"><NavigationArrow /></NuxtLink>
  - `components/ArticleCard.vue:41` — <NuxtLink
  - `components/ArticleCard.vue:48` — <NuxtLink
  - `components/ArticleCard.vue:60` — <NuxtLink :to="article.public_path" class="transition-colors group-hover:text-[var(--ee-primary-strong)]">
  - `components/ArticleCard.vue:68` — <NuxtLink :to="article.public_path" class="ee-label flex items-center gap-1.5 text-[var(--ee-ink)] group-hover:text-[var(--ee-primary-strong)]">
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R26 · `/books/[year]/[month]/[slug]`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/books/[year]/[month]/[slug].vue`。
- 共用落点：`default`, `ReadingLayout`, `MarkdownArticle`, `BacklinkList`, `NavigationArrow`, `SiteHeader`, `SiteFooter`, `ContentToc`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/books/[year]/[month]/[slug].vue:7` — <nav class="detail-breadcrumb" aria-label="面包屑"><NuxtLink to="/books">读书</NuxtLink><span aria-hidden="true"> / </span><span>笔记</span></nav>
  - `pages/books/[year]/[month]/[slug].vue:22` — <NuxtLink to="/books" class="back-link"><NavigationArrow direction="left" /> 返回阅读索引</NuxtLink>
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/BacklinkList.vue:6` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ContentToc.vue:12` — @click="navigateHeading"
  - `components/ContentToc.vue:35` — @click="navigateHeading"
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R27 · `/books`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/books/index.vue`。
- 共用落点：`default`, `PublicPageHero`, `NavigationArrow`, `BookCard`, `PaginationNav`, `SiteHeader`, `SiteFooter`, `SectionHeading`, `PageHeroArtwork`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/books/index.vue:19` — <NuxtLink :to="currentReading.public_path" class="blueprint-button blueprint-button-primary books-current-cta">阅读书摘笔记 <NavigationArrow /></NuxtLink>
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/BookCard.vue:3` — <NuxtLink :to="note.public_path" class="book-ledger-link">
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R28 · `/`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/index.vue`。
- 共用落点：`default`, `SectionHeading`, `HomeNotebookHero`, `HomeAtlas`, `ProfileCard`, `NavigationArrow`, `BlueprintWatermark`, `SiteHeader`, `SiteFooter`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/index.vue:24` — <SectionHeading label="最近更新" tag="h2" title-id="recent-heading" variant="section"><NuxtLink to="/archive" class="site-section-link">查看归档 <NavigationArrow /></NuxtLink></SectionHeading>
  - `pages/index.vue:36` — <h3><NuxtLink :to="article.public_path">{{ article.title }}</NuxtLink></h3>
  - `pages/index.vue:38` — <div class="home-note-footer"><div class="home-note-specs"><span v-for="tag in article.tags?.slice(0, 1)" :key="tag.id" class="blueprint-spec">{{ tag.name }}</span><span v-if="article.readingMinutes" class="blueprint-spec">{{ article.readingMinutes }} min</span></div><NuxtLink :to="article.public_path" :aria-label="ˋ阅读全文：${article.title}ˋ" class="blueprint-arrow"><NavigationArrow /></NuxtLink></div>
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/HomeNotebookHero.vue:7` — <NuxtLink to="/articles" class="blueprint-button blueprint-button-primary">浏览文章 <NavigationArrow /></NuxtLink>
  - `components/HomeNotebookHero.vue:8` — <NuxtLink to="/projects" class="notebook-project-link">查看项目 <NavigationArrow direction="up-right" /></NuxtLink>
  - `components/HomeNotebookHero.vue:28` — <NuxtLink to="/articles">开发笔记 <NavigationArrow /></NuxtLink>
  - `components/HomeNotebookHero.vue:29` — <NuxtLink to="/projects">项目实践 <NavigationArrow /></NuxtLink>
  - `components/HomeNotebookHero.vue:30` — <NuxtLink to="/books">阅读随记 <NavigationArrow /></NuxtLink>
  - `components/HomeAtlas.vue:12` — <button data-focus-card class="knowledge-root" type="button" aria-label="我的笔记，查看全部知识路线" @pointerenter="rootHovered = $event.pointerType === 'mouse'" @pointerleave="rootHovered = false" @focus="rootFocused = true" @blur="rootFocused = false" @click="reset">
  - `components/HomeAtlas.vue:23` — <button type="button" data-focus-card class="knowledge-node" :aria-pressed="selected === topic.category.id" data-testid="atlas-node" @click="selected = selected === topic.category.id ? null : topic.category.id">
  - `components/HomeAtlas.vue:26` — <NuxtLink class="knowledge-category" :to="{ path: '/articles', query: { category: topic.category.slug } }" :aria-label="ˋ浏览${topic.category.name}栏目ˋ">浏览领域 <NavigationArrow direction="up-right" /></NuxtLink>
  - `components/HomeAtlas.vue:29` — <NuxtLink v-if="topic.article" :to="topic.article.public_path" data-focus-card class="knowledge-article" data-testid="atlas-article">
  - `components/HomeAtlas.vue:34` — <div v-else data-focus-card class="knowledge-missing" :data-testid="ˋatlas-${topic.state}ˋ"><p>{{ topic.state === 'error' ? '这条路线的笔记暂不可用' : '这条路线等待新的笔记' }}</p><button v-if="topic.state === 'error'" type="button" :disabled="pending" @click="$emit('retry')">{{ pending ? '读取中…' : '重试读取' }}</button></div>
  - `components/HomeAtlas.vue:40` — <NuxtLink v-if="content.articles[0]" :to="content.articles[0].public_path" class="atlas-fallback-article">{{ content.articles[0].title }} <NavigationArrow direction="up-right" /></NuxtLink>
  - `components/HomeAtlas.vue:41` — <button v-if="content.taxonomyFailed" type="button" :disabled="pending" @click="$emit('retry')">{{ pending ? '读取中…' : '重试读取' }}</button>
  - `components/HomeAtlas.vue:45` — <button v-if="selected !== null" type="button" @click="reset">查看全部路线</button>
  - `components/HomeAtlas.vue:46` — <NuxtLink v-else-if="content.categoryCount && content.categoryCount > 3" to="/articles" data-testid="atlas-all-categories">更多领域 <NavigationArrow direction="up-right" /></NuxtLink>
  - `components/ProfileCard.vue:25` — <h2 class="sys-panel-name"><NuxtLink v-if="variant === 'intro'" to="/about">{{ profile.name }}</NuxtLink><template v-else>{{ profile.name }}</template></h2>
  - `components/ProfileCard.vue:61` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:69` — <button
  - `components/ProfileCard.vue:76` — @click="copyEmail"
  - `components/ProfileCard.vue:92` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/ProfileCard.vue:107` — @click="interactive ? undefined : $event.preventDefault()"
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R29 · `/notes/[year]/[month]/[slug]`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/notes/[year]/[month]/[slug].vue`。
- 共用落点：`default`, `NavigationArrow`, `ReadingLayout`, `MarkdownArticle`, `BacklinkList`, `SiteHeader`, `SiteFooter`, `ContentToc`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/notes/[year]/[month]/[slug].vue:11` — <NuxtLink to="/articles"><NavigationArrow direction="left" /> BACK TO ARTICLES <span class="sr-only">返回文章列表</span></NuxtLink>
  - `pages/notes/[year]/[month]/[slug].vue:16` — <NuxtLink
  - `pages/notes/[year]/[month]/[slug].vue:35` — <NuxtLink v-for="tag in article.tags" :key="ˋhero-${tag.id}ˋ" :to="{ path: '/articles', query: { tag: tag.slug } }">{{ tag.name }}</NuxtLink>
  - `pages/notes/[year]/[month]/[slug].vue:39` — <a class="article-hero-primary" href="#article-body" data-testid="article-start-reading" @click.prevent="startReading">
  - `pages/notes/[year]/[month]/[slug].vue:42` — <button
  - `pages/notes/[year]/[month]/[slug].vue:47` — @click="copyArticleUrl"
  - `pages/notes/[year]/[month]/[slug].vue:78` — <NuxtLink
  - `pages/notes/[year]/[month]/[slug].vue:108` — <NuxtLink v-if="articleContext.previous" :to="articleContext.previous.public_path" data-focus-card class="article-context-link">
  - `pages/notes/[year]/[month]/[slug].vue:113` — <NuxtLink v-if="articleContext.next" :to="articleContext.next.public_path" data-focus-card class="article-context-link text-right">
  - `pages/notes/[year]/[month]/[slug].vue:129` — <NuxtLink
  - `pages/notes/[year]/[month]/[slug].vue:143` — <NuxtLink to="/articles" class="back-link"><NavigationArrow direction="left" /> 返回文章列表</NuxtLink>
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/BacklinkList.vue:6` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ContentToc.vue:12` — @click="navigateHeading"
  - `components/ContentToc.vue:35` — @click="navigateHeading"
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R30 · `/projects/[slug]`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/projects/[slug].vue`。
- 共用落点：`default`, `NavigationArrow`, `ReadingLayout`, `MarkdownArticle`, `BacklinkList`, `SiteHeader`, `SiteFooter`, `ContentToc`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/projects/[slug].vue:5` — <nav class="detail-breadcrumb" aria-label="面包屑"><NuxtLink to="/projects">项目</NuxtLink><span aria-hidden="true"> / </span><span>项目详情</span></nav>
  - `pages/projects/[slug].vue:11` — <a v-if="project.repository_url" :href="project.repository_url" target="_blank" rel="noreferrer">代码仓库 <NavigationArrow direction="up-right" /></a>
  - `pages/projects/[slug].vue:12` — <a v-if="project.website_url" :href="project.website_url" target="_blank" rel="noreferrer">访问站点 <NavigationArrow direction="up-right" /></a>
  - `pages/projects/[slug].vue:21` — <NuxtLink
  - `pages/projects/[slug].vue:34` — <NuxtLink to="/projects" class="back-link"><NavigationArrow direction="left" /> 返回项目列表</NuxtLink>
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/MarkdownArticle.vue:2` — <article ref="root" class="prose-gavin" @click="handleArticleClick" v-html="rendered" />
  - `components/MarkdownArticle.vue:117` — <button type="button" class="article-code-copy" data-code-copy>复制</button>
  - `components/MarkdownArticle.vue:208` — <button type="button" data-mermaid-copy>复制 Mermaid 源码</button>
  - `components/BacklinkList.vue:6` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ContentToc.vue:12` — @click="navigateHeading"
  - `components/ContentToc.vue:35` — @click="navigateHeading"
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R31 · `/projects`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/projects/index.vue`。
- 共用落点：`default`, `PublicPageHero`, `BlueprintWatermark`, `NavigationArrow`, `ProjectCard`, `PaginationNav`, `SiteHeader`, `SiteFooter`, `SectionHeading`, `PageHeroArtwork`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/projects/index.vue:26` — <NuxtLink :to="lead.public_path" class="hover:text-[var(--ee-primary)] transition-colors">{{ lead.title }}</NuxtLink>
  - `pages/projects/index.vue:31` — <NuxtLink :to="lead.public_path" class="projects-lead-cta">
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/ProjectCard.vue:4` — <NuxtLink :to="project.public_path" class="project-ledger-link flex flex-col justify-between h-full space-y-4 relative z-10">
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## R32 · `/search`

- 阶段：P5 / P6；桌面入口：已核验；移动入口：已核验；功能结果见顶部案例矩阵（不可据入口可见认定全部通过）。
- 源码：`apps/web/pages/search.vue`。
- 共用落点：`default`, `SectionHeading`, `PageHeroArtwork`, `PaginationNav`, `SiteHeader`, `SiteFooter`, `SiteNavIcon`, `ThemeToggle`。
- 元素与条件入口（含共用组件，源码行号定位；动态分支待核）：
  - `pages/search.vue:13` — <form
  - `pages/search.vue:23` — <input
  - `pages/search.vue:33` — <button class="button-primary shrink-0" data-testid="search-submit" type="submit" :disabled="!hydrated || !input.trim()">搜索</button>
  - `pages/search.vue:41` — <NuxtLink to="/" class="ee-label inline-flex min-h-11 items-center gap-2 hover:text-[var(--ee-primary-strong)]">
  - `pages/search.vue:52` — <button type="button" class="search-clear" @click="clearQuery">清空查询</button>
  - `pages/search.vue:79` — <h2><NuxtLink :to="result.public_path">{{ result.title }}</NuxtLink></h2>
  - `layouts/default.vue:3` — <a href="#main-content" class="skip-link">跳到正文</a>
  - `components/PaginationNav.vue:8` — <NuxtLink
  - `components/PaginationNav.vue:18` — <NuxtLink
  - `components/SiteHeader.vue:4` — <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
  - `components/SiteHeader.vue:11` — <NuxtLink
  - `components/SiteHeader.vue:23` — <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:31` — <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
  - `components/SiteHeader.vue:37` — <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
  - `components/SiteHeader.vue:44` — <button
  - `components/SiteHeader.vue:51` — @click="toggleMenu"
  - `components/SiteHeader.vue:68` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:78` — @click.self="closeMenuAndRestoreFocus"
  - `components/SiteHeader.vue:83` — <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
  - `components/SiteHeader.vue:95` — <NuxtLink
  - `components/SiteHeader.vue:103` — @click="closeMenuOnCurrentRoute(item.to)"
  - `components/SiteHeader.vue:111` — <NuxtLink
  - `components/SiteHeader.vue:115` — @click="closeMenuOnCurrentRoute('/admin/articles')"
  - `components/SiteFooter.vue:7` — <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
  - `components/SiteFooter.vue:14` — <a href="/rss.xml">
  - `components/SiteFooter.vue:21` — <NuxtLink to="/about">
  - `components/ThemeToggle.vue:2` — <button
  - `components/ThemeToggle.vue:10` — @click="toggleTheme"

## 非页面出口与流程

| 用例 | 范围 | 阶段 | 状态 |
| --- | --- | --- | --- |
| F01 | RSS、sitemap、robots 与公开内容范围 | P5 | 见案例矩阵 |
| F02 | 写作保存、重进、发布快照、再次发布（三类型独立） | P3 | 见案例矩阵 |
| F03 | 关于发布、文章/关于版本差异与回滚、回收站三类型 | P4 | 见案例矩阵 |
| F04 | 实际 Markdown 文件导入与 ZIP 导出内容核对 | P4 | 见案例矩阵 |
| F05 | 空站、多页、404、上游失败与重试 | P5/P6 | 见案例矩阵 |
| F06 | 连续点击、保存中离页、请求失败、会话失效 | P6 | 见案例矩阵 |
| F07 | 移动登录、编辑发布、搜索阅读与逐页入口 | P6 | 见案例矩阵 |

### P2-01 结果索引

通过：正确登录进入后台并刷新保持；退出后直访项目跳转 login?returnTo=/admin/projects，重新登录返回项目。错误密码在 ready 状态输入，实际 401 且提示用户名或密码不正确。首次快速输入曾返回 422，未复现为错误密码缺陷；P6 保留加载边界验证。失败请求与退出失败在 P6 专项覆盖。证据：浏览器执行结果及 p2-other-sessions.png；未存密码。

### P2-02 结果索引

通过：账号信息显示隔离登录名与未配置邮箱，邮件闭环排除；刷新会话可读。取消批量退出保留 2 个其他会话；确认批量退出后其他浏览器刷新跳登录，当前会话刷新仍有效。新建独立浏览器会话，单个退出后该浏览器刷新跳登录。退出当前会话显示 reason=session-revoked，直访后台再被拦截。证据 p2-other-sessions.png；本轮新建浏览器上下文已关闭。

### P3-01 结果索引

三类型分别验证：管理首页 20 条，点击下一页并等待目标数据后为样本 03/02/01 共 3 条；草稿筛选为 23/22 共 2 条，已发布计数 21。无匹配搜索、刷新保留关键词、清除筛选、更多菜单开关均通过；已发布菜单有正确公开路径，文章另含预览/历史。新建与编辑入口已接续 P3-02～04。证据 p3-list-articles/books/projects.png。首次异步过早采样作废，以后续等待数据的结果为准。列表失败态在 P6。

### P2-03 结果索引

栏目与标签独立完成新增、编辑、取消编辑、重复 slug 409、删除取消/确认及刷新持久化。文章 24 引用分类后再删除，两项均保留并给出无法删除提示，证据 p2-taxonomy-linked.png。一次标签提交 pending 已单列 O001，未消除该观察；其余正常路径通过。

### P3-05 结果索引

独立无登录浏览器逐一核对三类型 24：后台标题改为第二版并自动保存，刷新后台保留；访客仍见原标题；再次确认发布后访客刷新才显示第二版，路径保持不变。截图 p3-snapshot-articles/books/projects.png。前置草稿只存在管理端，公开列表阶段继续查公开范围。

### P3-02 结果索引

文章浏览器创建/必填校验/栏目标签/自动保存刷新/独立与内嵌预览/发布取消确认已执行。媒体库插入 Markdown 成功；未完成参考资料阻止发布，补齐站内目标 1 与标题后发布，公开显示引用审查文章一。快照隔离和再次发布见 P3-05。发布 Alt/失败/离页场景接续 P6，不以本任务完成覆盖它们。

### P3-03 结果索引

读书创建、字段、自动保存刷新、预览、发布与快照已执行。媒体封面选择失败 I001：相对 URL 被 URL 校验拒绝；手填完整本地地址后保存发布恢复，不能算选择路径通过。证据 issue-001-book-cover.png 和 p3-book-public.png；该缺陷不阻碍审查任务结束。

### P3-04 结果索引

项目 24 经浏览器创建，空名称校验、正文、slug、摘要、仓库与站点 URL、关联文章 24 完成操作；摘要自动保存刷新保持，内嵌预览正确。确认发布后详情含正文、仓库、站点和 1 篇关联文章。独立访客快照验证见 P3-05。证据 p3-project-public.png。

### P4-01 结果索引

关于页引言与能力修改后自动保存、刷新重读；预览字段核对可见引言，发布后公开能力与网站说明正确。领域/标签、近期动态的添加排序删除、写作主题及规格增删均执行，最终公开保持四领域三动态。公开模板不直接呈现引言与写作主题，按既有边界不判展示缺陷。一次新增标签临时输入在保存后消失待 P6 定位。证据 p4-about-public.png。

### P4-03 结果索引

文章 24 三条历史快照可读取，差异显示标题/正文变化，回滚取消后再确认生成发布 #4，公开恢复首版标题。关于页历史快照、整页预览、差异可读，取消后确认回滚原版，公开能力恢复后端工程且审查网站说明消失。证据 p4-article-history.png、p4-about-rollback.png。首次读取处于加载中未计证据，后续等待内容重核。

### P4-05 结果索引

真实页面导出 gavin-markdown.zip 下载成功，ZIP 有 72 条并含三类型元数据/正文；基于导出构造三类型有效 LF 文件，导入生成文章/读书/项目 25 草稿，重复 slug 再导入被拒绝。同内容仅换行不同：CRLF 返回 422 front matter is required，LF 返回 200，确认为 I002。证据 export.zip、p4-import.png、issue-002-crlf.png。实际入口仅 Markdown 文件导入，ZIP 为导出，S01 已核实。

### P4-04 结果索引

三类型已发布样本 20 分别经管理列表移入回收站、公开不可用、UI 恢复后公开恢复；读书/项目明确 404→200，文章恢复标题已核。三类型专属导入草稿 25 再移入回收站，永久删除取消保留、确认后删除，刷新回收站为空；只读隔离数据库核对三表 id25 均不存在。用户追加明确授权删除。证据 p4-trash-three-types.png、p4-trash-purged.png。不删除其他审查依赖。

### P5-03 结果索引

访客真实操作三内容列表与归档上一页/下一页；管理计数已独立核对。文章栏目及标签点击保留对应 query 并可达内容；搜索关键词审查有多页，点击第二页、刷新保持关键词；无匹配显示空状态，清空回到初始。初次等待用了错误文案未计通过，后续改为实际 search-empty 入口重核。公开归档按发布内容显示，草稿不出现。

### P5-01 结果索引

独立访客打开首页，图谱选中栏目后显示路线提示，可重置全部路线，并从图谱文章链接进入实际文章详情。首页浏览文章/项目/阅读、最近更新、归档、个人资料等目标清单已与公开路由核对，入口可访问；导航共享交互在 P6 逐页移动补核。证据 p5-home.png 与页面实际跳转。

### P5-02 结果索引

独立访客三类列表和详情可读真实发布版本，详情正文及项目关联文章/链接、书籍封面与评分/阅读状态按前序发布结果核对。列表分页可切换；三类型不存在详情均返回真实 404。空站阶段已有各类型空状态截图，不将其与上游错误混同。证据 p5-articles/books/projects.png、p3-public 与快照截图。

### P2-04 结果索引

媒体上传、选择、搜索/来源/状态筛选、加载更多 12→14、去重、复制 URL/Markdown、单项/批量移除取消与恢复均已验证，刷新媒体仍存在。真实浏览器分发带文件的 drop 与 ClipboardEvent paste，经真实上传接口成功；这是浏览器事件模拟，不是操作系统拖放设备实测。503 上传失败后重试成功，截图 p6-media-retry.png。非法格式有失败反馈，空 Alt 注册实际允许，正文发布校验另在 P6。外链故意不存在不记本站缺陷。

### P4-02 结果索引

个人资料名称/定位/简介/城市/邮箱/网站/GitHub/头像/技能可保存并刷新保持；技能增删排序及头像移除再设置已操作。首页/关于展示身份，关闭城市与邮箱后公开隐藏，重开邮箱可复制并出现邮箱已复制反馈。简历 URL 保存后公开链接在浏览器新页打开隔离 PDF；附件服务 18201，session41670，仅本轮目录。AI worker关闭，未执行同步。资料成功不是 AI 质量证据。截图 p4-profile-public.png。

### P5-04 结果索引

阅读正文 GFM 粗体、任务列表、引用块、代码、表格可见；复制代码出现已复制；KaTeX 1 个、Mermaid 开始→完成图实际渲染。目录代码链接解析到对应编码 ID，平滑滚动结束 y约630，非即时采样误判。站内参考链接进入文章1，文章1出现回链；wikilink 路径正确，外部参考实际新页打开 Example Domain。宽代码/15列表格 desktop 与 390移动均有局部 scrollWidth>clientWidth，整页不横向溢出。证据 p5-reading.png、p5-backlinks.png、p5-wide-reading.png。

### P5-05 结果索引

公开资料与可见性、渠道、邮箱复制、普通简历附件已由 P4 实测，独立访客可读；RSS/sitemap/robots 均200，发布路径存在且草稿22/23未泄露。外部参考 https://example.com/ 实际在新页打开 Example Domain，GitHub/个人网页目标与保存值一致；未声称控制外部服务可用性。

### P6-01 结果索引

Chromium 390×844 视口模拟：19 个后台业务路由、10 个公开路由及登录均实际打开；逐页 H1/可见入口与截图登记 mobile-admin-0..18、mobile-public-0..9，无整页横向溢出。独立移动浏览器登录后新建 Mobile audit，正文/设置切换、创建发布可达；移动搜索后进入发布详情成功。媒体选择桌面与对应移动布局可见，主要流程未被遮挡；不称真机测试。

### P6-02 结果索引

公共菜单与后台菜单开关、Esc关闭；公共焦点返回触发按钮。主题切换后刷新仍dark。发布弹窗Tab在确认发布/取消之间循环，Esc关闭；前序发布、回滚、删除、会话弹窗取消确认已实测。Markdown工具栏标题输出 ##、加粗 **、引用 >、链接 [text](https://) 正确。移动媒体选择可插入Markdown并保存。

### P6-03 结果索引

补核完成：三类保存503保留输入并阻止发布，解除后重试刷新保持；保存中离页等待请求完成；三类空Alt报告行列并阻止发布；双击创建仅1个POST。真实另页退出使编辑PATCH401，输入留页显示保存失败。列表、媒体、账号读取失败重试恢复，注销503不假称退出，搜索503错误页重试保留词。关于10领域上限禁用、新增动态条目与草稿公开隔离通过。I003临时输入丢失、I004初次列表失败留旧页单列失败；不是全通过。资料空名称拒绝，恢复后保存成功。

### P6-04 结果索引

逐页与案例组对账完成。补核文章历史分页20/2、关于加载更多20/25、回收站分页20/1及返回；数据预置仅用于制造分页，结论来自浏览器操作。首页taxonomy读取失败显示降级提示并可重试恢复；编辑器直接设备图片插入真实媒体路径后保存，恢复原正文。找回密码页桌面/390移动外壳及返回登录通过，邮件闭环仍排除。范围内31路由外壳已核验，另1个AI路由排除；74案例组70通过4失败，不代表每个源码控件或所有输入组合穷举。所有受控拦截已撤销，临时访客上下文已关闭。

### P7-01 结果索引

已对账32页面路由、31范围内桌面/移动外壳与74功能案例组：70通过、4失败，无阻塞案例。源码元素目录仅作入口追溯，重复共享控件不重复计数，也不声称所有输入组合穷举。恢复页外壳已补核；邮件闭环、AI前后台及简历AI摄入明确排除，不计通过。

### P7-02 结果索引

复核I001～I004截图均实际存在；I002同内容换行对照、I003真实请求延迟前后值、I004两个独立导航场景支持可复现结论。缺陷按高1中3排序，没有把替代路径通过当原问题修复。O001单次pending仍属观察，根因未确认。S01按真实Markdown导入与ZIP导出纠正计划前提。

### P7-03 结果索引

覆盖清单、执行记录、按影响排序的问题报告已整理。报告区分审查任务与案例组、实测事实与推测，保留4项未修复缺陷及1项观察。环境仅本地开发版Chromium，桌面1440×1000与移动390×844视口；不代表真机、多浏览器、生产部署或发布资格。

### P7-04 结果索引

三份交付已完成，七阶段31项任务结果均归档到各阶段独立目录；入口导航切换为完成状态及报告链接。原始附件留在忽略目录，服务已关闭且端口无监听；保留隔离数据用于复现。最终交付只说明本轮实测范围与缺陷，不宣称全部产品功能通过。
