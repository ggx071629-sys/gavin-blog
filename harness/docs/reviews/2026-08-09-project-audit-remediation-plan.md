---
id: review-2026-08-09-project-audit-remediation-plan
level: L2
summary: 已闭环的 2026-08-09 项目审计历史修复计划
load_when:
  - historical-audit
  - audit:2026-08-09
author: Codex
---

# 2026-08-09 项目审计修复总纲

> 历史记录：对应修复已经闭环，本文不得作为当前待办或命令清单；现行功能以产品模块表和 active specs 为准。

## 文档定位

本文把[全项目隐性缺陷审计](2026-08-09-project-audit.md)中的 20 项发现转换为可执行的修复路线。它是长期索引化的修复总纲，不是活跃 spec，不授权本轮修改业务代码。

真正实施时按本文建议逐批创建短生命周期 active spec；每份 spec 只承载一个可独立验收、回滚和关闭的行为边界。不得把 20 项缺陷合并为一个长期悬空的巨型 spec。

截至 2026-08-12，AUD-01～20 对应实现均已落地。批次 1～7 已通过短生命周期 spec 验证并压缩归档；批次 0 由提交 `651a3c8` 和 `apps/api/tests/test_environment_isolation.py` 固化环境隔离，但没有独立 task evidence manifest。本文以下批次章节保留为历史修复设计，不再代表待办状态；当前生产发布阻断项以[发布准备](../operations/release-readiness.md)为准。

## 目标与非目标

### 目标

- 先恢复可信的发布门禁，再修数据丢失和公开内容边界。
- 明确每项缺陷的修复归属、依赖、规格触发条件和验收证据。
- 将产品缺陷、生产阻断项、UI/A11y 和低频边界分开交付。
- 所有修复均通过隔离数据库、隔离媒体目录和确定性替身验证。
- 保证每个批次可单独回滚，不依赖未完成的后续批次才能保持系统可用。

### 非目标

- 本文不修改 Web、API、契约、数据库或部署代码。
- 不恢复已冻结的 GitHub crawler/discovery ingestion。
- 不以 Stitch 或 `web_prototype` 作为 UI 像素验收基线。
- 不调用真实 LLM、真实 GitHub，不下载本地检索大模型。
- 不在本轮创建 active spec；spec 仅在相应修复即将开始时建立。

## 总体顺序

| 顺序 | 修复批次 | 覆盖缺陷 | 目的 | 预计规格 |
| --- | --- | --- | --- | --- |
| 0 | 恢复可信门禁 | AUD-06 | 让后续红绿结果可复现 | `20260809-hermetic-release-gate` |
| 1 | 编辑保存安全 | AUD-01 | 先停止静默数据丢失 | `20260809-editor-save-safety` |
| 2 | 发布快照一致性 | AUD-02、AUD-03 | 修复工作副本与公开内容边界 | `20260809-publishing-snapshots` |
| 3 | 故障状态真实性 | AUD-04、AUD-12 | 区分空数据、未登录、404 与 5xx | `20260809-failure-state-contracts` |
| 4 | 运行时与安全边界 | AUD-05、AUD-07、AUD-10 | 修 Worker 配置、生产校验和浏览器纵深 | `20260809-runtime-security-boundaries` |
| 5 | 前端运行可靠性 | AUD-08、AUD-09、AUD-11、AUD-15 | 清理水合、轮询、部分成功和初始状态矛盾 | `20260809-frontend-runtime-reliability` |
| 6 | 移动可访问性与资产 | AUD-13、AUD-14、AUD-16 | 修抽屉、触控目标和字体依赖 | `20260809-mobile-accessibility-assets` |
| 7 | 边界与 SEO 清理 | AUD-17～AUD-20 | 完成低频正确性和 UI 细节 | `20260809-boundary-seo-cleanup` |

批次 0～4 是发布前置条件。批次 5～6 应在公开发布前完成；批次 7 可以独立交付，但不得用它替代前面批次。

## 规格拆分原则

### 必须创建 SDD spec

以下变更触发行为、API、数据、安全或跨栈风险，实施前必须创建 active spec：

- AUD-01：离页、flush、发布按钮与保存状态的行为契约。
- AUD-02/03：项目/书摘发布修订、数据库迁移、公开 API 和搜索同步。
- AUD-04/12：HTTP 错误映射、认证状态与页面错误展示契约。
- AUD-05/07/10：生产启动校验、Worker 配置和媒体安全边界。
- AUD-08/09/11/15：如批次会改变共享 composable、上传结果或 Profile API 契约。

### 可以直接进入小型维护任务

若没有进一步扩大范围，AUD-13、AUD-14、AUD-17、AUD-18、AUD-19、AUD-20 可以在对应批次下作为小型实现任务；仍须具备独立测试和 evidence。AUD-16 若改变 CSP、构建资产或部署缓存，则并入安全/资产 spec。

### Active spec 生命周期

1. 仅在该批次马上开始实现时创建。
2. 同时最多保持一个主要数据/跨栈 spec 和一个不冲突的小型 UI spec。
3. 验收未完成不得关闭；后续批次不得借用未关闭 spec 的模糊范围。
4. 通过 `python -m tools.harness close <task_id>` 关闭并保留 Git 历史。

## 批次 0：恢复可信发布门禁

### 范围

覆盖 AUD-06，不顺带修改真实 LLM 配置或业务行为。

### 目标状态

- 所有测试 Settings 显式 `_env_file=None`，不得读取开发 `.env`。
- 测试数据库、媒体目录、模型目录和第三方端点全部由 fixture 注入。
- 测试环境默认拒绝非本地网络；需要网络替身的测试只允许明确的环回端口。
- 同一提交在有/无本地 `.env` 的机器上得到相同结果。

### 必需验证

- 在临时目录放置包含不同 LLM base URL、数据库 URL 的 `.env`，全套 API 测试仍使用 fixture 值。
- `test_health_never_exposes_api_key` 在不清理用户环境的前提下通过。
- `npm run quality:release` 能完整进入 Web 阶段，而不是在 API fixture 阶段中止。

### 完成定义

- Release gate 全绿或只剩与本批次无关、已有单独缺陷编号的失败。
- evidence 记录命令、退出码和测试数量，不提交原始长日志。

## 批次 1：编辑保存安全

### 范围

覆盖 AUD-01；文章、项目、书摘和孵化草稿采用同一离页保存语义。

### 推荐决策

- `dispose()` 不得默认丢弃 dirty snapshot。
- 站内导航、预览和发布前调用显式 `flush()`；flush 失败时阻止动作并显示错误。
- 浏览器关闭/刷新无法可靠完成异步保存时，使用 dirty `beforeunload` 提醒，不声称已保存。
- 保存进行中禁用相互竞争的发布/预览动作，或让动作等待同一 single-flight Promise。
- 冲突响应保留本地内容，提供刷新远端、复制本地内容和重试选项。

### 必需验证

- 输入后 0ms、300ms、899ms 内点击预览，返回编辑后内容仍存在。
- 输入后立即点击侧栏、浏览器后退、切换详情页和卸载组件。
- flush 期间网络 500、超时、409 冲突均不静默丢内容。
- 文章、项目、书摘、孵化草稿使用参数化契约测试，避免四套行为再次漂移。

### 回滚边界

只改变客户端保存协调，不改变数据库 schema。若新离页协调产生死锁，可回滚该 composable 和调用点，不影响已保存数据。

## 批次 2：发布快照一致性

### 范围

覆盖 AUD-02、AUD-03，是本轮成本和迁移风险最高的批次。

### 推荐决策

- 项目与书摘采用与文章一致的 working copy + immutable published revision。
- 公开 API、搜索、sitemap、关联卡片只读取当前发布 revision。
- PATCH 只更新工作副本并增加 working version；publish 原子创建/切换发布 revision。
- publish 请求携带 expected working version，拒绝在 flush 后被另一标签页修改的竞态。
- 关联文章的 title、summary、slug、published_at、public path 必须来自同一个发布快照。

### 数据迁移策略

1. 增加项目/书摘 revision 表和 current published revision 指针。
2. 对现有 `published` 行生成 revision 1；草稿不生成公开 revision。
3. 迁移期间先双读校验，再切换公开读取；禁止长期双写。
4. 迁移后对公开路径、搜索文档和 revision 指针运行一致性检查。
5. 保留可逆 migration；回滚不得删除已生成 revision 数据。

### 必需验证

- 已发布项目/书摘自动保存后，公开 API、搜索和页面仍显示旧 revision。
- 点击“更新发布”后所有公开消费者同时切换到新 revision。
- 已发布文章存在工作副本时，项目关联区仍显示旧公开元数据。
- 两标签页并发保存/发布产生稳定 409，而不是最后写入者静默覆盖。
- 删除、恢复、slug 冲突和回滚均有 API + E2E。

### 完成定义

- AUD-02/03 的隔离复现脚本转为回归测试并通过。
- migration 在旧数据副本上前进、回滚、再次前进均成功。
- 公共契约 README 和 contracts 类型与实现一致。

## 批次 3：故障状态真实性

### 范围

覆盖 AUD-04、AUD-12；建立 Web 与 API 共享的失败分类。

### 推荐错误模型

| 状态 | 页面行为 | HTTP/路由行为 |
| --- | --- | --- |
| 成功且列表为空 | 显示空态和创建/探索引导 | 200 |
| 资源明确不存在 | 显示 404 页面 | 404 |
| 未登录/会话过期 | 返回登录页并保留 return URL | 401 后定向 |
| 无权限/CSRF 失败 | 明确权限或安全校验失败 | 403 |
| 频率限制 | 显示等待与重试信息 | 429 |
| API 超时/网络/5xx | 显示服务暂不可用与重试 | 保留 5xx/503 |
| 注销失败 | 不宣称会话已销毁 | 保留当前状态并提示 |

### 必需验证

- API down 时首页、五类公开列表页和后台列表不显示“没有内容”。
- 详情 API 的 500/timeout 不转换为 404；只有明确 API 404 才返回页面 404。
- 登录分别覆盖错误密码、429、CSRF、500、网络中断。
- session 检查 500 不重定向为未登录。
- logout 失败后 UI 不显示已退出；成功后服务端 session 确实失效。
- 对公开 SSR 响应状态增加集成测试，防止 soft 404 回归。

## 批次 4：运行时与安全边界

### 范围

覆盖 AUD-05、AUD-07、AUD-10。

### Worker 与配置

- 建立单一 `build_runtime_settings()`/入口工厂，API、Worker、迁移和诊断命令使用同一校验。
- 生产环境拒绝非空 `GAVIN_URL_FETCH_ALLOWLIST` 和 `retrieval_model_backend=double`。
- `run_worker.py` 显式传递模型 root/backend，并在启动任务循环前完成生产校验。
- 启动日志只记录非敏感配置摘要，不输出 API key、密码和完整数据库凭据。
- 增加真实 Worker CLI 启动测试，而不仅测试 `IncubatorWorker` 类。

### 浏览器安全响应头

- 先部署 CSP Report-Only 并收集仅包含规则/来源的紧凑报告。
- 收敛 Nuxt 所需 script/style/font/img/connect 源，再启用强制 CSP。
- 至少设置 `frame-ancestors 'none'`、`object-src 'none'`、`base-uri 'self'`、`form-action 'self'`、`X-Content-Type-Options: nosniff` 和明确 Referrer-Policy。
- HSTS 由 HTTPS 边缘层负责；本地 HTTP 测试不强行设置，但发布检查必须验证最终公网响应。
- 响应头必须覆盖正常 HTML、错误页和登录/后台页。

### 媒体解码

- 在任何 transpose/load 前读取并检查尺寸。
- 限制允许的图片 format；将 `DecompressionBombWarning` 转为请求级错误。
- 保留字节上限、像素上限和输出尺寸上限三道边界。
- 运行进程/容器内存限制作为纵深，不把 Pillow 默认阈值当作产品阈值。

### 必需验证

- 生产 Worker 在非默认模型目录读取与 API 相同的 manifest。
- 生产 allowlist/double 启动立即失败；test 环境替身仍可使用。
- 安全头快照测试覆盖 200、404、500 和后台 HTML。
- 构造超大尺寸、小压缩体积图片时，在完整像素解码前拒绝。

## 批次 5：前端运行可靠性

### 范围

覆盖 AUD-08、AUD-09、AUD-11、AUD-15。

### 水合与共享数据

- Profile 读取抽成唯一 composable，同一 AsyncData key 只使用同一 handler/options。
- 所有依赖 system color mode 的 SSR 分支使用 `<ColorScheme>`、unknown 占位或 CSS-only 图标。
- E2E 将 hydration mismatch、Vue error 和 `NUXT_E3004` 视为失败。

### 孵化轮询

- 所有详情页只使用统一 polling composable。
- 使用“请求完成后再 setTimeout”，避免 async interval 重叠。
- hidden tab 暂停、visible 恢复；终态停止；卸载 abort。
- 轮询下限 2 秒，失败指数退避并显示最后更新时间/重试状态。

### 多文件媒体上传

- 推荐保留逐文件事务，但 UI 返回逐项状态，不伪装为全有或全无。
- 前面成功、后面失败时立即 refresh 成功项，并为失败项提供重试。
- 重试使用内容指纹或明确重复提示，避免用户不知情地产生重复资产。

### Profile 初始规则

- 推荐允许 0 个核心技能，因为当前公开默认资料和 UI 已支持空列表。
- 若产品决定至少 1 个，则默认资料必须自带合法技能，初始化与更新 schema 保持一致。
- fresh database 的第一次“只改简介/头像”必须可保存。

### 必需验证

- 生产构建首页和主题切换无 console warning/error、水合不一致和可见闪动。
- 慢响应轮询始终只有一个 in-flight 请求；隐藏页请求数不增长。
- 三文件“成功/失败/成功”显示三个独立结果并保留成功项。
- fresh database Profile 修改任意非技能字段可成功保存。

## 批次 6：移动可访问性与字体资产

### 范围

覆盖 AUD-13、AUD-14、AUD-16。

### 抽屉

- 明确采用 modal drawer：`role=dialog`、`aria-modal=true`、可见标题、初始焦点、Tab/Shift+Tab 循环、Escape 关闭、关闭后焦点返回。
- 抽屉打开时主内容和移动 header 的非抽屉部分使用 `inert`；兼容性方案需同步处理辅助技术可见性。
- 路由切换、窗口跨 breakpoint 和组件卸载均释放 body lock/inert。

### 触控目标

- 技能上移、下移、删除的交互热区至少 32×32px，移动优先目标 44×44px；视觉图标可以保持小尺寸。
- 禁用按钮仍保留稳定布局和可理解标签。
- 检查所有相邻图标按钮，不只修本次已测的三个。

### 字体

- 将实际使用的 Inter、Hanken Grotesk、JetBrains Mono 字重子集自托管。
- 使用 woff2、明确 `font-display`、预加载首屏必要字重；删除 Google Fonts preconnect/runtime stylesheet。
- 断网和字体加载失败时布局不溢出，fallback metric 尽量接近。

### 必需验证

- 390×844、375×667、移动横屏下完成抽屉全键盘循环，背景不可聚焦。
- 200% zoom/text scaling 不遮挡关闭按钮和导航末项。
- 几何断言覆盖所有相邻小目标，至少满足 WCAG 2.2 2.5.8。
- 浏览器网络记录中不再出现 Google Fonts 请求。

## 批次 7：边界条件与 SEO

### AUD-17 日期上限

- 前端传次日 00:00:00Z，API 使用排他 `< created_before`。
- 验证 `23:59:59.000000`、`.000001`、`.999999` 和次日零点。

### AUD-18 分页上限

- 页码上限由 endpoint page size 和 API max offset 推导，不使用全局 5001。
- 验证 page size 12/20 的最大可访问 offset，以及越界 URL 的稳定规范化。

### AUD-19 Mermaid

- resolved theme 改变时只重绘 Mermaid 节点，不重新解析整篇 Markdown。
- 无效 Mermaid 显示局部错误和可复制源码，不产生未处理 Promise rejection。
- light/dark 切换截图验证文字、线条和背景对比度。

### AUD-20 SearchAction

- target placeholder 与 `query-input` 使用同一参数名。
- JSON-LD 进入 schema 单测；canonical URL、搜索参数和页面实现保持一致。

## 测试矩阵升级

| 维度 | 当前基线 | 修复后最低要求 |
| --- | --- | --- |
| 浏览器 | Chromium | Chromium + Firefox + WebKit 的核心公开/后台 smoke |
| Viewport | 1440、390 | 增加 375、移动横屏和窄桌面 |
| 可访问性 | axe/Lighthouse | 增加焦点循环、inert、触控几何、200% zoom |
| 数据保存 | 等待 autosave 后离页 | 增加 debounce 窗口内所有离页动作 |
| 故障注入 | 少量正常/冲突路径 | API down、5xx、timeout、慢响应、部分成功 |
| SSR | 页面可加载 | console error/warn 为零，状态码与内容语义一致 |
| 配置 | 类/fixture 测试 | 真实 API/Worker CLI 启动契约 |
| 发布 | 文章修订 | 文章、项目、书摘统一发布快照 |
| 安全 | CSRF/session/SSRF 默认路径 | 生产配置负测、安全响应头、媒体解码前拒绝 |

## 每个批次的统一完成定义

1. 对应 active spec 的行为、非目标和回滚边界已经确认。
2. 失败复现先转成自动测试，并证明修复前红、修复后绿。
3. 单元、契约、集成、E2E 和质量门禁按风险比例通过。
4. 新增测试不读取开发 `.env`、不访问真实外部服务、不写开发数据。
5. 没有新增 console warning/error、未处理 Promise 或后台任务泄漏。
6. contracts、Web/API README 和 release-readiness 与最终行为同步。
7. evidence 只提交紧凑 manifest，不提交重日志、截图或临时数据库。
8. `python -m tools.harness verify <task_id>` 通过后，才允许关闭 spec。

## 跨批次风险与依赖

- AUD-01 必须在 AUD-02 的发布 UI 接入前完成，否则新 revision 仍可能发布旧 snapshot。
- AUD-06 必须最先完成，否则后续“全绿”缺少环境可复现性。
- AUD-04 的错误模型会影响 AUD-12 登录态和 AUD-11 上传反馈，必须先定共享分类。
- AUD-07 CSP 强制模式依赖 AUD-16 字体自托管；可先 Report-Only，字体完成后再强制。
- AUD-08 Profile composable 与 AUD-15 默认规则应同批交付，避免共享缓存放大无效初态。
- 项目/书摘 revision migration 必须在真实数据副本演练，不能只用 fresh test DB。

## 决策清单

以下默认建议应在相应 spec intake 时由人确认；若不同意，必须记录替代方案及其风险：

| 决策 | 默认建议 | 不采用的主要代价 |
| --- | --- | --- |
| 项目/书摘是否有发布快照 | 有，与文章一致 | “更新发布”继续成为虚假承诺，公开编辑不可控 |
| 离页时如何处理 pending save | flush，失败则阻止离页 | 继续存在静默丢数据或误报已保存 |
| Profile 是否允许 0 技能 | 允许 | 必须给默认资料提供稳定、非空技能 |
| 多文件上传语义 | 逐项事务 + 逐项结果 | 服务端原子批量需要更大 API/存储改造 |
| 安全头由谁负责 | 应用给安全默认，边缘层验证/补充 | 仅依赖未确定部署平台，发布前无法本地验证 |
| CSP 上线方式 | Report-Only → 强制 | 直接强制容易造成字体、图片或 hydration 资源故障 |

## 进度登记

| 批次 | 状态 | 归档 spec／实现 | 验证 evidence | 备注 |
| --- | --- | --- | --- | --- |
| 0 可信门禁 | 已实现 | `651a3c8` | `apps/api/tests/test_environment_isolation.py` | 有专门回归测试；无独立 task evidence manifest |
| 1 编辑保存 | 已闭环 | [20260809-editor-save-safety](../../specs/archive/20260809-editor-save-safety.md) | [evidence](../../verification/evidence/20260809-editor-save-safety.json) | 覆盖 AUD-01 |
| 2 发布快照 | 已闭环 | [20260809-publishing-snapshots](../../specs/archive/20260809-publishing-snapshots.md) | [evidence](../../verification/evidence/20260809-publishing-snapshots.json) | 覆盖 AUD-02、AUD-03 |
| 3 故障状态 | 已闭环 | [20260809-failure-state-contracts](../../specs/archive/20260809-failure-state-contracts.md) | [evidence](../../verification/evidence/20260809-failure-state-contracts.json) | 覆盖 AUD-04、AUD-12 |
| 4 运行安全 | 已闭环 | [20260809-runtime-security-boundaries](../../specs/archive/20260809-runtime-security-boundaries.md) | [evidence](../../verification/evidence/20260809-runtime-security-boundaries.json) | 覆盖 AUD-05、AUD-07、AUD-10；强制 CSP 与公网 HSTS 仍属于发布决策 |
| 5 前端可靠性 | 已闭环 | [20260809-frontend-runtime-reliability](../../specs/archive/20260809-frontend-runtime-reliability.md) | [evidence](../../verification/evidence/20260809-frontend-runtime-reliability.json) | 覆盖 AUD-08、AUD-09、AUD-11、AUD-15 |
| 6 移动与资产 | 已闭环 | [20260809-mobile-accessibility-assets](../../specs/archive/20260809-mobile-accessibility-assets.md) | [evidence](../../verification/evidence/20260809-mobile-accessibility-assets.json) | 覆盖 AUD-13、AUD-14、AUD-16 |
| 7 边界与 SEO | 已闭环 | [20260809-boundary-seo-cleanup](../../specs/archive/20260809-boundary-seo-cleanup.md) | [evidence](../../verification/evidence/20260809-boundary-seo-cleanup.json) | 覆盖 AUD-17～AUD-20 |

本表登记历史事实状态，不表示项目已经 production-ready。Telemetry 不得自动修改优先级、创建 spec 或宣称完成；后续生产发布工作仍需人工确认并通过项目既有规格、验证和关闭流程。
