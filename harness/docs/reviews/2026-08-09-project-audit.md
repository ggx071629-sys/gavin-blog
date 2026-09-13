---
id: review-2026-08-09-project-audit
level: L2
summary: 2026-08-09 全项目审计历史快照
load_when:
  - historical-audit
  - audit:2026-08-09
author: Codex
---

# 2026-08-09 全项目隐性缺陷审计

> 历史记录：结论只适用于文中固定快照，不代表当前功能、缺陷或发布状态。

## 结论（审计时点）

项目的常规主流程和自动化基线明显高于普通个人项目：前端类型检查、67 个单元测试、生产构建、6 组视觉/可访问性/Lighthouse 检查以及 23 条 E2E 均通过；CSRF、会话 Cookie、发布修订、SQLite 外键/事务、URL 抓取默认 SSRF 防线也有明确实现。

但当前不能据此判定为“可放心发布”。本次确认 **20 项缺陷：P0 0、P1 7、P2 9、P3 4**。其中 3 项直接破坏发布/草稿数据边界，1 项会在后端故障时向用户和搜索引擎返回错误的成功/空内容，另有 Worker 配置漂移、发布门禁不确定性和浏览器安全响应头缺失。建议先建立一个短期修复批次处理全部 P1，再进入 UI 细修。

> 后续状态（2026-08-12）：本文是 2026-08-09 的历史审计快照，不是当前缺陷清单。AUD-01～20 已按短生命周期 spec 全部闭环，归档与 evidence 映射见[项目审计修复总纲](2026-08-09-project-audit-remediation-plan.md#进度登记)。这不代表项目已经 production-ready；当前生产发布阻断项以[发布准备](../operations/release-readiness.md)为准。

## 范围与判断口径

- 审计对象：当前仓库的 Web、API、共享契约、Harness、配置、测试和运行入口。
- 排除：`my_blog_fork`；GitHub 爬虫/发现摄入已冻结，未实现本身不记为缺陷；未调用真实 LLM、未下载大模型、未访问真实 GitHub。
- `web_prototype` 保留，但 Stitch 不作为 UI 验收基线；UI 以当前实现、真实浏览器行为、WCAG/WAI 和成熟产品通用模式判断。
- 动态操作全部使用临时 SQLite、临时媒体目录和本地替身；没有读取真实 `.env` 内容，也没有修改开发数据。
- P0：立即造成大范围不可逆损失/接管；P1：核心数据边界、公开内容正确性或发布阻断；P2：重要功能、可访问性、安全纵深或明显体验问题；P3：边界条件和优化项。
- 证据等级：`动态复现` > `测试/日志复现` > `静态高置信` > `风险项`。工时仅用 S/M/L/XL，不给不可靠的小时数。

## 优先级总览

| ID | 优先级 | 结论 | 证据 | 范围 | 成本 |
| --- | --- | --- | --- | --- | --- |
| AUD-01 | P1 | 编辑后快速离页会静默丢失待自动保存内容 | 动态复现 | 本地产品 | M |
| AUD-02 | P1 | 项目/书摘“更新发布”是假边界，自动保存已公开 | 动态复现 | 本地产品 | XL |
| AUD-03 | P1 | 项目关联区泄露文章未发布标题/摘要/slug | 动态复现 | 本地产品 | M |
| AUD-04 | P1 | API 故障被伪装成 200 空站或详情 404 | 动态+静态 | 产品/生产 | M |
| AUD-05 | P1 | Worker 忽略模型目录配置且未执行生产安全校验 | 静态高置信 | 生产阻断 | M |
| AUD-06 | P1 | 发布质量门禁受本机 `.env` 污染，不可复现 | 测试复现 | 发布阻断 | S |
| AUD-07 | P1 | 生产 HTML 缺少 CSP/防框架/nosniff 等安全头 | 动态复现 | 生产阻断 | M |
| AUD-08 | P2 | 生产 SSR 存在主题水合不一致，AsyncData key 冲突 | 动态+日志 | 产品 | M |
| AUD-09 | P2 | 孵化详情轮询绕过统一生命周期并可能重叠 | 静态高置信 | 产品/性能 | M |
| AUD-10 | P2 | 媒体像素上限在解码后才检查 | 静态高置信 | 安全/可靠性 | S-M |
| AUD-11 | P2 | 多文件上传可部分成功但 UI 只显示整体失败 | 静态高置信 | 产品/UX | M |
| AUD-12 | P2 | 登录、会话故障和退出失败被误报为其他状态 | 静态高置信 | 产品/UX | S-M |
| AUD-13 | P2 | 移动后台抽屉未建立模态语义，背景仍可聚焦 | 动态复现 | UI/A11y | M |
| AUD-14 | P2 | 技能排序/删除触控目标仅约 16–19 × 16px | 动态复现 | UI/A11y | S |
| AUD-15 | P2 | 默认 0 技能资料无法保存任何其他修改 | 动态复现 | 产品/UX | S |
| AUD-16 | P2 | 核心字体依赖运行时 Google Fonts | 静态高置信 | UI/性能/隐私 | M |
| AUD-17 | P3 | 日期上限漏掉当天最后一秒的微秒记录 | 静态高置信 | 边界条件 | S |
| AUD-18 | P3 | 前端页码上限与 12 条分页组合后提前截断数据 | 静态高置信 | 扩展性 | S |
| AUD-19 | P3 | Mermaid 不随主题切换重渲染，错误缺少降级 | 静态高置信 | UI | S-M |
| AUD-20 | P3 | 首页 SearchAction 参数名与 query-input 不一致 | 静态高置信 | SEO | S |

## P1：必须先修

### AUD-01 编辑后快速离页会丢失待自动保存内容

`AutosaveQueue.dispose()` 只清除 900ms debounce timer，没有 flush 或路由离开保护（`apps/web/utils/autosave.ts:67`）。文章、项目、书摘和孵化草稿都在卸载时直接 dispose（`ArticleEditor.vue:190`、`ProjectEditor.vue:103`、`BookNoteEditor.vue:97`、`drafts/[id].vue:705`）。

真实浏览器中创建隔离文章后，将正文改为“快速离页内容”并立即点“预览”；预览仍显示“已保存版本”，返回编辑后新正文彻底消失，页面没有确认或失败提示。现有 E2E 会先等待“已自动保存”再离页，因此恰好绕开真实用户路径。

建议：为所有编辑器统一引入 `flush-before-navigation`/离页确认协议；保存进行中阻止发布和预览切换；增加“输入后 0–899ms 内点击链接/后退/关闭组件”的单测与 E2E。该行为变更建议进入短规格。

### AUD-02 项目/书摘自动保存已绕过“更新发布”

项目和书摘 PATCH 直接修改已发布主表并同步搜索（`apps/api/app/routes/admin_projects.py:142`、`apps/api/app/routes/admin_books.py:108`），而 UI 仍显示“更新发布”（`ProjectEditor.vue:17`、`BookNoteEditor.vue:11`）。与文章使用发布修订隔离工作副本的语义不一致。

隔离 API 动态验证：已发布项目/书摘 PATCH 后、不调用 publish，公开 API 的标题立即变为 `AUTOSAVED project title` / `AUTOSAVED book title`，状态仍为 `published`。因此按钮承诺的是不存在的发布边界，误编辑会立即面向访客并进入搜索。

建议：项目和书摘采用与文章一致的 working copy + immutable published revision，或明确取消“更新发布”概念并要求每次编辑显式确认。前者涉及模型、迁移、API、搜索和 UI，需 SDD，成本 XL。

### AUD-03 项目关联文章泄露未发布元数据

公开文章正文正确读取发布修订，但项目关联序列化直接读取 `Article.title/slug/summary` 活动工作副本（`apps/api/app/routes/public_projects.py:13`），只用 `status == published` 过滤。

隔离 API 动态验证：文章公开详情仍显示 `Published article title` 且 `has_unpublished_changes=true`，同一文章在公开项目的关联列表已显示 `UNPUBLISHED article title`。这会泄露未审核标题、摘要和可能尚未稳定的 URL。

建议：关联卡片全部从当前发布修订构造，路径日期和 slug 也必须来自同一发布快照；加入“已发布文章存在工作副本”契约测试。

### AUD-04 后端故障被伪装成空站或 404

首页、文章、项目、书摘、归档等页面只读取 `useAsyncData().data`，忽略 `error/status`。隔离 API 停止后，`/`、`/articles`、`/projects`、`/books`、`/archive` 均返回 **HTTP 200** 并展示“还没有/正在路上”空态。详情页则把任何请求错误统一转换为 404（`notes/.../[slug].vue:67`、`projects/[slug].vue:73`、`books/.../[slug].vue:47`）。后台列表也存在同类“故障=无数据”误导。

事实是服务不可用，UI 却告诉用户内容不存在；对搜索引擎还可能形成 soft 404 或让有效 URL 被错误判定为 404。Google 官方说明，空错误页的 2xx 可能被识别为 soft 404，而 5xx 会触发暂时降低抓取速率：[HTTP 状态码对抓取的影响](https://developers.google.com/crawling/docs/troubleshooting/http-status-codes)。

建议：统一 `loading/empty/error` 三态；SSR 保留上游 5xx/503，只有明确的 API 404 才映射页面 404；对公开页和后台页加入 API down E2E。

### AUD-05 Worker 配置与生产安全边界漂移

文档声明 `GAVIN_URL_FETCH_ALLOWLIST` 仅供本地测试且生产必须为空，模型根目录由 `GAVIN_RETRIEVAL_MODEL_ROOT` 配置、生产只允许 `onnx`（`apps/api/.env.example:10`）。实际情况：

- `Settings.validate_runtime()` 没有拒绝生产环境的非空抓取 allowlist 或 `double` 检索后端（`apps/api/app/config.py:59`）。allowlist 恰好允许环回地址，误配会重新打开访问本机服务的路径。
- API 启动会校验配置，但 `scripts/run_worker.py` 直接 `Settings()`，没有调用 `validate_runtime()`。
- Worker 启动没有把 `retrieval_model_root` 和 `retrieval_model_backend` 传给 `IncubatorWorker`（`scripts/run_worker.py:75`）；Worker 因而回退到 `./data/models` 和 `onnx`（`app/incubator/worker.py:627`），而 API 健康检查使用配置值。自定义模型目录部署会出现“API 看一个目录、Worker 用另一个目录”。
- E2E 启动器显式传入两项配置，所以测试不会暴露生产入口遗漏（`scripts/run_e2e.py:259`）。

OWASP 将 localhost、链路本地和私网列为 SSRF 必须阻断范围，并建议严格 allowlist：[SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)。建议用单一工厂构造 API/Worker 运行配置，所有入口调用同一生产校验，并对真实 `run_worker` 入口做启动契约测试。

### AUD-06 发布质量门禁受本机环境污染

`npm run quality:release` 得到 API 241 passed / 1 failed：`test_health_never_exposes_api_key` 期望空 `base_url`，却读到了本机 `.env` 中配置的地址。通用测试 fixture 构造 `Settings(...)` 时未设置 `_env_file=None`（`apps/api/tests/conftest.py`），而 Settings 默认读取 `.env`。

在子进程显式清空该非敏感变量后，失败用例立即通过，证明是测试隔离问题，不是该断言发现产品泄密。风险是：不同开发机/CI 得到不同门禁结果，更严重时测试可能误连真实数据库或第三方端点。

建议：所有测试 Settings 强制 `_env_file=None`，测试进程设置 `GAVIN_ENVIRONMENT=test` 并禁止非本地网络；新增“存在任意开发 `.env` 仍应全绿”的回归检查。

### AUD-07 生产 HTML 未设置浏览器安全响应头

对刚构建的生产 Nuxt 服务实测，以下响应头全部为空：`Content-Security-Policy`、`X-Frame-Options`、`Strict-Transport-Security`、`X-Content-Type-Options`、`Referrer-Policy`、`Permissions-Policy`。当前没有部署层契约说明由反向代理补齐。

这不是“已经确认可利用的 XSS”，但管理后台可被框架嵌入，缺少 `frame-ancestors`/X-Frame-Options 会失去点击劫持纵深；缺少 CSP 和 nosniff 也让未来模板/依赖缺陷没有浏览器侧隔离。OWASP 建议用 CSP `frame-ancestors` 防框架嵌入、设置 `nosniff` 和明确 Referrer-Policy：[HTTP Security Response Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)。

建议：先以 `Content-Security-Policy-Report-Only` 观察，再收紧为 nonce/hash CSP；至少加入 `frame-ancestors 'none'`、`object-src 'none'`、`base-uri 'self'`、`form-action 'self'`、`nosniff` 和明确 Referrer-Policy。HSTS 由最终 HTTPS 边缘层负责，但必须纳入发布验证清单。

## P2：重要缺陷

### AUD-08 SSR 水合不一致与 AsyncData key 冲突

生产浏览器首页稳定记录 `Hydration completed but contains mismatches.`；完整 E2E 日志进一步定位 `SiteHeader` 子节点/`circle` 不一致。`SiteHeader.vue:29` 在 SSR 模板中直接按 `colorMode.value` 切换不同 SVG，而服务器无法知道客户端 system theme。Nuxt Color Mode 官方明确要求用 `unknown` 占位或 `<ColorScheme>` 避免闪动：[Color Mode Caveats](https://color-mode.nuxtjs.org/advanced/caveats)。

同时首页和默认 layout 都使用 `public-profile` key，但各自创建不同 handler（`pages/index.vue:56`、`layouts/default.vue:31`），运行时出现 `NUXT_E3004 incompatible handler`。Nuxt 要求同 key 的 handler 和关键 options 保持一致：[useAsyncData shared state](https://nuxt.com/docs/4.x/api/composables/use-async-data#shared-state-and-option-consistency)。

影响包括首屏闪动、客户端丢弃/修补 SSR DOM、状态共享歧义和难以复现的交互。建议抽出单一 profile composable；主题图标使用 SSR 安全占位或 CSS-only 方案；把 hydration warning 设为 E2E 失败条件。

### AUD-09 孵化轮询绕过项目自己的生命周期边界

Web 边界要求非终态刷新不快于 2 秒、隐藏页暂停、终态停止。虽然存在 `useIncubatorPolling`，审计计划页仍以 1500ms 直接 `setInterval`（`audit-plans/[id].vue:231`），草稿计划、审计详情、发布计划也各自直接轮询。它们不监听 `visibilitychange`，异步请求慢于 interval 时还可能重叠；共享 composable 本身也缺少 in-flight guard（`useIncubatorPolling.ts:29`）。

建议统一为完成后 `setTimeout` 调度、隐藏页暂停、AbortSignal 取消、单飞和指数退避；加慢响应、切后台和组件卸载测试。

### AUD-10 媒体像素上限检查发生在完整解码之后

上传代码先 `ImageOps.exif_transpose`、`source.load()`，随后才用 `width * height` 检查应用配置上限（`apps/api/app/routes/media.py:86`、`:89`）。这意味着自定义 40MP 上限无法阻止更大图片先占用内存/CPU。

Pillow 官方说明 `Image.open` 是惰性的，真正像素读取发生在处理或 `load()`；并建议把 `DecompressionBombWarning` 视为错误：[Pillow Image.open](https://pillow.readthedocs.io/en/stable/reference/Image.html)、[Pillow Security](https://pillow.readthedocs.io/en/stable/handbook/security.html)。建议在任何 transpose/load 前检查尺寸，限制 formats，并在上传作用域把 Pillow warning 转为异常；仍需容器内存上限作为纵深。

### AUD-11 多文件媒体上传隐藏部分成功

`MediaUploader` 支持 multiple，但顺序 `for` 上传（`apps/web/components/MediaUploader.vue:96`）。第 2 个文件失败时，第 1 个已提交且不可回滚，循环抛错后父页面不 refresh，只显示整体“上传失败”。用户会误以为全部失败，再次上传产生重复媒体。

建议返回逐项结果并立即展示成功项/失败项；或提供服务端批量事务契约。至少加入“成功、失败、成功”三文件集成测试。

### AUD-12 认证故障被误报，退出可能是假成功

- 管理中间件把 `/auth/session` 的所有失败都重定向登录（`apps/web/middleware/admin.ts:3`），API 500/网络中断被当成未登录。
- 登录页除 429 外所有错误都显示“用户名或密码不正确”（`pages/admin/login.vue:97`），CSRF、代理、500 也被误导。
- logout 在 `finally` 中无条件跳登录（`layouts/admin-core.vue:114`）；若服务端注销失败，Cookie 仍有效，但界面呈现已退出。

建议按 401/403、429、5xx、network 分型；注销失败时清晰提示并避免宣称会话已销毁；加入 API down/CSRF 失败测试。

### AUD-13 移动后台抽屉背景仍可访问

抽屉打开后会锁 body 并把焦点移入第一个链接，但容器没有 `role=dialog`/`aria-modal`，主内容没有 `inert` 或 `aria-hidden`，也没有 Tab focus trap（`apps/web/layouts/admin-core.vue:50`、`:103`）。真实 390×844 浏览器中，抽屉打开时背景“新建草稿”仍为 `tabIndex=0`。

WAI 模态模式要求打开时焦点进入容器、Tab/Shift+Tab 在内部循环、背景不可交互：[Dialog Modal Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)。如果产品不想把它定义为 modal，就不能同时使用遮罩和滚动锁制造模态预期；建议复用已有 `AdminDialog` 的焦点基础设施或原生 `<dialog>`。

### AUD-14 技能排序/删除按钮触控目标过小

真实 390×844 浏览器测量：上移/下移约 `18.6×16px`，删除约 `16.1×16px`，三个按钮相邻（源样式 `pages/admin/profile.vue:94`）。自动 axe/Lighthouse 均未发现该问题。

WCAG 2.2 AA 2.5.8 要求目标至少可容纳 24×24 CSS px，或满足严格的间距例外；相邻小目标不满足：[Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)。建议交互热区至少 32–44px、视觉图标仍可小，并在移动矩阵加入几何断言。

### AUD-15 默认资料与保存规则互相矛盾

后端默认资料持久化 `skills_json="[]"`（`apps/api/app/profile_service.py:17`），UI 也正常显示 `0 / 6`；但任何保存都先要求至少 1 个技能（`pages/admin/profile.vue:310`）。动态验证中，不改技能、只尝试保存默认资料，得到“至少需要 1 个核心技能”。这意味着用户只想改头像/简介也被迫新增技能。

建议二选一：默认资料包含至少一个合法技能；或 schema/UI 都允许 0 个。初始化默认值必须满足自己的更新 schema，并加 fresh-database 首次保存 E2E。

### AUD-16 核心字体依赖运行时 Google Fonts

Nuxt head 在每个页面连接 `fonts.googleapis.com`/`fonts.gstatic.com` 并拉取三套字体（`apps/web/nuxt.config.ts:98`）。在网络受限、离线、企业策略或中国大陆访问不稳定时会回退系统字体，带来首屏阻塞/字体跳变和品牌布局漂移，同时把访客请求暴露给第三方。

建议把实际使用的字重子集自托管并预加载；若保留外链，明确 CSP `font-src/style-src`、超时/回退策略和隐私说明。

## P3：边界与优化

### AUD-17 日期上限漏掉最后一秒的微秒记录

孵化列表把 `created_to` 拼成 `T23:59:59Z`（如 `audits/index.vue:203`）。数据库时间支持微秒，因此 `23:59:59.000001–23:59:59.999999` 会被排除。建议传“次日 00:00:00Z”并在 API 使用 `< next_day`。

### AUD-18 页码上限过早截断 12 条分页

`MAX_PAGE=5001`（`apps/web/utils/pagination.ts:4`）显然按 20 条/页和 API offset 100,000 推导；公开列表实际 12 条/页时最多只能访问约 60,000 条，后半数据永远无法通过 UI 翻到。建议按 endpoint page size 动态计算，或统一 cursor pagination。

### AUD-19 Mermaid 主题不会跟随站点主题切换

`MarkdownArticle` 只在渲染内容时读取当前 dark class 初始化 Mermaid（`apps/web/components/MarkdownArticle.vue:69`），不监听 color mode；切换主题后图仍保持旧配色，解析 Promise 的失败也没有就地降级。建议监听 resolved theme 重绘，并把无效图表降级为可复制源码和局部错误提示。

### AUD-20 SearchAction 参数名不一致

首页 JSON-LD 的 target URL 使用 `?q={search_term_string}`，但 `query-input` 声明 `required name=query`（`apps/web/pages/index.vue:72`）。结构化数据消费者无法把声明变量正确代入。建议统一为同一变量名，并把 JSON-LD schema 加入单测。

## 自动化结果与其盲区

### 实际结果

- `python -m tools.harness index`：索引原本已是 current。
- `npm run quality:release`：API lint 通过；API 241/242 通过，1 项因本机 `.env` 污染失败，随后在显式空环境下单项通过；原命令因此未继续执行后续阶段。
- `npm run quality:web`：typecheck 通过，18 个 Vitest 文件/67 tests 通过，生产构建通过，Playwright quality 6/6 通过；Lighthouse performance/accessibility/best-practices/SEO 均 100。
- `npm run test:e2e`：23/23 通过；但日志包含 `NUXT_E3004`、`SiteHeader` hydration mismatch，说明“测试通过”不等于“控制台无错误”。
- 隔离 API 验证：确认项目/书摘提前公开、项目关联泄露文章工作副本；文章公开正文仍正确保持发布修订。
- 真实浏览器：确认快速离页丢数据、SSR hydration error、抽屉背景可聚焦、16–19px 触控目标、默认资料无法保存。
- API down：五个公开页返回 200 空态；生产响应头六项均缺失。

### 现有盲区

- 视觉矩阵只有 1440×1100 与 390×844、Chromium；没有 375px、横屏、200% zoom/text scaling、reduced-motion、Firefox/WebKit。
- axe/Lighthouse 无法可靠发现小触控目标、模态焦点逃逸、错误状态语义和业务发布边界。
- E2E 主动等待“已自动保存”，未覆盖立即预览/返回/切页/关闭。
- 没有“API 故障/慢响应/超时/部分成功”故障注入测试。
- 没有将 console warning/error 作为失败条件。
- 未执行向外部 registry 发送依赖清单的在线 CVE 审计，因此 npm/Python 依赖的最新漏洞状态仍是明确未覆盖项；应在受控 CI 中执行并保存紧凑 evidence。

## 修复批次建议

1. **数据与发布边界**：AUD-01/02/03。为项目、书摘和文章建立一致的工作副本/发布快照语义，同时补并发版本契约。
2. **故障真实性与可发布性**：AUD-04/05/06。统一错误三态，修 Worker 配置工厂，彻底隔离测试环境。
3. **生产安全基线**：AUD-07/10，再处理登录限流的持久化/多实例策略。安全头先 Report-Only，再收紧。
4. **运行时稳定性**：AUD-08/09/11/12/15。把 console error、API down、慢轮询和部分成功纳入质量门禁。
5. **移动与细节**：AUD-13/14/16–20。先修可访问性，再处理字体、日期、分页、Mermaid 和 JSON-LD。

P1 批次建议创建 SDD；特别是 AUD-02 会改变数据模型和公开契约。其余可按风险合并为 2–3 个短规格，避免 20 个零散补丁互相制造新不一致。

## 明确不计为缺陷的事项

- GitHub source crawler 与 discovery ingestion 已有冻结决策；本轮不把“尚未实现”重复记为 bug。仅当已有 UI/文档声称可用或现有路径依赖它们时才应重新开项。
- `web_prototype`/Stitch 的存在不是缺陷，也未用其像素结果验证当前 UI。
- 两张未跟踪头像图片不构成功能缺陷；当前代码未以其 Git 状态作为运行依赖。
- 尚未确定部署平台、域名、备份和 CI，属于既有 release-readiness 阻断项，不与上述产品缺陷重复计数。

## 外部依据

- [WCAG 2.2 — Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)
- [WAI-ARIA APG — Dialog (Modal) Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [OWASP — HTTP Security Response Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)
- [OWASP — SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Google — HTTP 状态码如何影响抓取](https://developers.google.com/crawling/docs/troubleshooting/http-status-codes)
- [Nuxt — useAsyncData shared state and option consistency](https://nuxt.com/docs/4.x/api/composables/use-async-data#shared-state-and-option-consistency)
- [Nuxt Color Mode — Caveats](https://color-mode.nuxtjs.org/advanced/caveats)
- [Pillow — Image reference / decompression bomb](https://pillow.readthedocs.io/en/stable/reference/Image.html)
- [Pillow — Security handbook](https://pillow.readthedocs.io/en/stable/handbook/security.html)
