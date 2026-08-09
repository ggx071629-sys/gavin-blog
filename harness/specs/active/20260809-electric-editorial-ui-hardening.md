---
id: spec-20260809-electric-editorial-ui-hardening
level: L1
summary: 硬化 Electric Editorial 语义设计系统并完成公开站、后台与知识孵化的全站最终验收
load_when:
  - task:20260809-electric-editorial-ui-hardening
author: Gavin
task_id: 20260809-electric-editorial-ui-hardening
status: active
---

# Context

前四阶段已经覆盖主项目的全部用户可见 UI：第一阶段建立 Electric Editorial 双主题基础与首页，第二阶段完成全部公开页面，第三阶段完成非孵化后台，第四阶段完成 12 个知识孵化路由。第四阶段的 application evidence 已存在并记录类型检查、58 个 Vitest、生产构建、8 个工作流 E2E、48 个孵化视觉视图、12 路由 axe、无横向溢出和首页 Lighthouse 100／100／100／100 通过；其 spec 当前仍为 active，等待原任务完成关闭。第三阶段代码已经落地，但仍缺少独立 application evidence。第五阶段不得把前序 active spec 冒充为已关闭，也不代替其生命周期收口。

当前没有新的 Stitch 页面需要实现。web_prototype/ 的 17 个页面仍只覆盖公开站；后台与知识孵化继续以已确认的派生设计为准。因此第五阶段不是第五轮改版，而是设计系统硬化与发布前全站收敛：保持公开博客的阅读和品牌表达、非孵化后台的信息密度、知识孵化的证据链工作台三种界面模式，同时消除跨阶段积累的样式兼容层和验证盲区。

仓库审计确认：

- apps/web/layouts/admin.vue 已有 0 个页面消费者；26 个受保护后台页面均使用 admin-core，登录和草稿预览使用各自既有模式。旧布局现为可误用的遗留实现。
- apps/web 中仍有约 787 处 slate／blue／rose／amber／emerald 等原始调色板颜色类，其中知识孵化页面及组件约占 635 处。
- 第四阶段为保持可回退，主要通过 .incubator-workbench [class*="..."] 和 .admin-modal [class*="..."] 等子串选择器，把旧调色板类覆盖为 Electric Editorial 令牌。该方案已通过视觉验收，但长期存在误匹配、specificity 竞争和新增状态绕过主题令牌的风险。
- --admin-warning-* 和 --admin-danger-* 在多个作用域重复定义；全局 field、editor-grid、save-state、status-chip 与 Markdown 样式仍混用原始调色板类。
- 浏览器 theme-color、Nuxt loading indicator 与部分组件颜色仍以独立字面值存在，可能与 --ee-* 双主题源发生漂移。

frontend-design 的审查结论是本阶段不新增新的视觉签名，也不把后台统一成模板化 SaaS 控制台。Electric Editorial 已经是识别性来源；第五阶段的设计动作是删除无事实含义的装饰和意外差异，使公开阅读层、内容运营层与证据工作台各自更清晰。ui-ux-pro-max 仅提供发布前硬门槛：正常文字 4.5:1、可见 focus、44×44px 触控目标和 8px 间距、明确 hover／active／disabled／loading／error／empty 状态、移动端无页面级横向滚动、局部宽内容受控滚动、错误可被辅助技术感知并给出恢复路径。不采用其与现有产品冲突的营销布局、新字体、状态库或新依赖建议。

第五阶段覆盖面如下：

| 界面模式 | 路由／文件范围 | 原型与当前状态 | 第五阶段动作 |
| --- | --- | --- | --- |
| 公开品牌与阅读 | 首页，以及文章、项目、读书列表／详情、归档、关于、搜索、404 共 11 个页面族 | 有 Stitch 浅／深色依据；前两阶段 application evidence 已通过 | 保持原型结构和视觉，不重新设计；回归令牌、主题、Markdown、SEO、响应式和可访问性 |
| 非孵化后台 | 登录、内容列表／新建／编辑／预览／修订、栏目标签、媒体、回收站迁移、个人名片等 16 个路由 | 无后台 Stitch；admin-core 派生设计已落地，独立 application evidence 尚未收口 | 将颜色、表面、状态、表单和反馈迁移到语义令牌／原语，补齐全矩阵与 evidence |
| 知识孵化 | /admin/incubator 下 12 个路由 | 无孵化 Stitch；第四阶段 application evidence 已通过 | 移除子串兼容覆盖和原始调色板依赖，保留证据链信息架构及全部行为 |
| 共享基础 | app.vue、nuxt.config.ts、main.css、default／admin-core 布局、导航、分页、对话框、编辑器、媒体和状态组件 | 共享令牌已存在但有重复定义和旧兼容层 | 建立单一语义来源、静态防回归规则，退役无消费者旧布局 |

# Goal

在不改变任何 API 契约、数据库、公开／后台 URL、认证规则、业务状态机和页面信息架构的前提下，完成主项目 Electric Editorial 设计系统的语义化硬化，移除无消费者旧后台壳层和宽泛颜色兼容选择器，使公开站、非孵化后台、知识孵化在浅色／深色、桌面／移动端中直接由可审计的语义令牌和基础原语驱动，并以一次全站最终验证证明 UI 已达到后续独立迁移前的可交付状态。

# Non-goals

- 不新增、删除或重命名任何公开 URL、后台 URL、查询参数、导航目标、API 字段、请求体、状态值或业务操作。
- 不修改 apps/api/、数据库模型、Alembic、packages/contracts/、认证中间件、Cookie／CSRF／Session、摄入／审计／草稿／发布／任务状态机。
- 不重新设计 Stitch 已确认的公开页面，不改变 Electric Editorial 视觉方向、字体角色、内容层级或公开页面品牌签名。
- 不把公开博客、非孵化后台和知识孵化强制做成同一种页面结构；共享的是令牌和无领域基础原语，不是信息架构。
- 不新增仪表盘、统计、搜索、筛选、批量操作、动画、插图、图标或后端未支持的交互。
- 不以减少颜色类数量为理由删除必要状态、弱化错误／警告、合并不同业务状态或改变按钮资格。
- 不建设完整 Storybook、独立设计系统站点、长期共享包、远程 UI 包、submodule 或符号链接。
- 不引入新的 UI 框架、CSS-in-JS、状态管理、图标库、字体、动画库、视觉测试 SaaS 或运行时依赖。
- 不关闭、重写或伪造前四阶段 spec／evidence；可复用同一次真实命令结果，但每个 task 的 evidence 必须准确归属。
- 不修改、移动或删除 my_blog_fork/；第五阶段完成后也不自动迁移，等待用户另行授权。
- 不修改、解冻、关闭或继续实现 20260807-github-discovery-ingestion 与 20260807-github-source-crawler。
- 不恢复或合并 codex/frozen-github-ingestion-checkpoint，不提交或推送。

# Acceptance criteria

- 建立明确的语义令牌分层：canvas／surface／surface-low／surface-high、ink／muted／faint、line／line-soft、primary／signal、focus，以及 info／success／warning／danger 各自的 background／border／ink。浅色和深色分别定义可读组合，不通过反转或 opacity 猜测状态色。
- --admin-warning-*、--admin-danger-* 等重复作用域变量收敛为单一语义来源；浏览器 theme-color、Nuxt loading indicator 和共享基础组件使用与当前主题体系一致的值，不再维护无说明的平行颜色常量。
- 全局 field、editor、surface、status、notice、button、action、dialog、empty、loading 和 code／diff 区域使用语义类或无领域基础组件表达意图。组件 API 不包含 slate、blue、rose 等视觉实现词，也不引入知识孵化专属类型。
- 删除 .incubator-workbench [class*="..."]、.admin-modal [class*="..."] 及其他依靠类名子串重映射颜色／圆角的兼容选择器；语义样式必须直接落在调用方或明确的基础原语上，不能用更高 specificity 的新补丁替代旧补丁。
- apps/web/pages/admin/**、后台专用组件和 Incubator 组件的模板不再使用 slate／gray／blue／purple／rose／red／amber／emerald／green 等原始调色板颜色工具类；布局、间距、尺寸和响应式工具类可以保留。对 Markdown 代码语法、用户内容渲染等确有隔离需要的例外必须位于专用样式作用域并写明原因。
- 新增可执行的静态防回归检查，至少阻止后台模板重新引入原始调色板颜色类、阻止 [class*="..."] 兼容选择器、阻止页面重新声明 layout: admin。检查不得误报普通内容文字或布局类。
- 在确认消费者仍为 0、Nuxt 构建和所有后台路由均正常后删除 apps/web/layouts/admin.vue；admin-core 保持唯一受保护后台主壳层。登录、草稿预览等既有例外模式保留，不为“唯一布局”强行套壳。
- 公开站继续严格保持 Stitch 已确认的浅／深色结构、排版、背景、边框、阴影和交互状态。共享令牌修改不得把阅读层变成后台密度，也不得使两套主题趋同为简单颜色翻转。
- 非孵化后台继续保持第三阶段高密度模式：列表、表单、编辑器、版本历史、媒体、危险操作和实时预览的信息层级不变；所有 hover、active、focus-visible、disabled、loading、success、warning、error、empty 和 conflict 状态可辨识且不只依赖颜色。
- 知识孵化继续保持第四阶段的来源→审计→草稿→发布证据链、五入口导航、筛选、批量操作、对话框、轮询、自动保存和任务状态；移除兼容 CSS 后 12 个路由与代表动态状态在视觉和行为上不回退。
- 酸性绿只用于满足对比要求的信号面、边缘或大号／高对比内容；正常小字在对应背景上至少 4.5:1，大号文字至少 3:1，UI 控件边界和焦点至少 3:1。错误、警告、成功、冲突和选中状态均附带文本、图标或结构语义。
- 所有交互具备明确 hover／active／focus-visible／disabled 状态；异步操作显示 loading 并防重复提交，完成和失败反馈可被辅助技术感知。错误放在相关字段或操作附近，并提供重试、修正或返回等真实恢复路径。
- 所有核心操作可键盘完成；跳到正文、桌面侧栏、移动抽屉、二级导航、分页、批量栏、编辑器、对话框和危险操作的焦点顺序、捕获、Esc 和返回焦点正确。触控目标至少 44×44px，相邻目标至少 8px，并尊重 prefers-reduced-motion。
- 390×844 下所有页面无 document 级横向溢出；不得使用全局 overflow-hidden 掩盖问题。Markdown 表格、代码、diff、原始内容和宽数据区只能在有键盘可达与可见边界的自身容器内受控滚动。
- 全站最终视觉矩阵覆盖 39 个页面族：1 个首页、10 个其他公开页面族、16 个非孵化后台路由、12 个知识孵化路由；每个执行 light/dark × 1440×1100/390×844，共 156 个基础视图。另覆盖 loading、empty、error、conflict、stale、partial success、running、cancel requested 和 destructive confirmation 等代表状态。
- 公开页面视觉验收继续对照对应 Stitch 原型；后台与知识孵化只按已声明的派生设计、真实字段和跨页一致性验收，不虚构不存在的原型。任何发现的不一致必须判断是实现错误、原型缺口还是明确例外，不能跳过。
- 39 个页面族的可达固定数据状态执行 axe WCAG 2.0／2.1 A/AA，自动扫描零违规；对动态对话框、移动菜单、轮询反馈、自动保存、错误恢复、局部滚动和状态非颜色依赖执行人工辅助技术检查。
- 保留全部既有 data-testid、E2E 闭环和可观察行为。若重构基础原语需要调整选择器，只能迁移到更稳定的语义／testid，不得删除断言、跳过用例、放宽 axe／Lighthouse 阈值或用截图更新掩盖真实回退。
- Nuxt 类型检查、全部 Vitest、生产构建、全部适用 Playwright E2E、全站质量测试、git diff --check 和 Harness 验证通过；生产首页 Lighthouse performance、accessibility、best-practices、SEO 均不低于 90。
- 生成第五阶段 application evidence，准确列出执行命令、测试数量、156 个基础视图、axe 范围、人工 Stitch／派生设计复核、Lighthouse 分数、边界检查和已知非阻断警告。截图、trace、Lighthouse 原始报告等重型产物只保存在本地。
- 最终 diff 不包含 my_blog_fork/、apps/api/、packages/contracts/、数据库迁移、两个冻结 spec 或冻结 checkpoint；主项目保持可独立运行，且未产生面向未来 fork 迁移的共享依赖。

# Implementation slices

1. 令牌与静态护栏：记录当前有效视觉基线，补齐双主题语义状态／焦点令牌，收敛重复变量和主题元数据，建立原始调色板、子串选择器和旧布局引用的静态检查。完成后现有页面外观和行为必须不变。
2. 通用基础与非孵化后台：语义化 field、surface、status、notice、button、dialog、editor、empty／loading 等无领域原语，逐页移除非孵化后台的原始颜色依赖；每个页面族迁移后立即运行对应单元、E2E、双主题和移动检查。
3. 知识孵化直接语义化：按概览／来源、审计、草稿／发布、任务四组迁移 12 个路由，保留所有真实状态与测试钩子；每组通过闭环后移除对应兼容覆盖，最后删除全部 [class*="..."] 样式补丁。
4. 遗留退役与共享回归：确认旧 admin 布局零消费者后删除它，清理重复或无调用样式；回归公开 Markdown、首页、主题、导航、登录、编辑器、分页、媒体和对话框，确保共享原语没有把三种界面模式同质化。
5. 全站最终验收：执行 156 个基础视觉视图、代表动态状态、全路由 axe、键盘／触控／局部滚动、全部业务 E2E、生产构建和 Lighthouse；修复实际缺陷后生成紧凑 evidence，不以更新基线代替判断。

# Risks

- 原始调色板类数量大，机械替换可能把视觉词替成无意义的“semantic-1／2”，或把业务状态错误合并。必须先按表面、文本、动作、反馈和状态意图分类，再迁移调用方。
- 当前子串选择器掩盖了模板中真实的浅／深色差异；移除时会暴露局部回退。必须按路由组移除并立即截图，不得一次删除全部覆盖后依赖人工记忆修补。
- 过度组件化会让公开阅读层、内容后台和孵化工作台共享不合适的布局，或把孵化类型／API 上提到通用层。只抽取无领域视觉原语，领域组合继续留在各自页面和组件中。
- status-chip 当前承载大量不同状态；单一颜色映射无法表达发布、冲突、过期、排队、失败和取消请求。语义 API 必须保留状态文本和业务资格，不能只生成通用绿色／黄色／红色。
- 旧 admin 布局虽无静态消费者，Nuxt 文件路由和动态布局名称可能造成遗漏。删除前后都需扫描 layout 引用、运行生产构建并访问全部后台入口；若发现运行时消费者则停止删除而不是建立别名。
- theme-color 和 loading indicator 不能直接假定 CSS 变量在所有浏览器上下文生效；实现必须验证 SSR head、首次加载和主题切换，不以去除字面值为唯一目标。
- 156 个基础视图与动态状态会显著增加运行时间和本地截图体积。允许按切片并行或分组执行，但最终 evidence 必须来自同一实现版本；重型产物不得提交。
- 动态后台页面需要隔离 fixture。若使用轮询中的实时数据直接截图会产生不稳定差异；应固定数据和时钟，但不能通过关闭真实轮询、跳过动画状态或伪造业务响应来获得稳定。
- 第三、第四阶段仍为 active，且当前工作树包含大量未提交跨阶段成果。第五阶段不能重写其 evidence、用 reset／checkout 清理文件或假设 Git 历史已保存可回退点；每个切片必须限定 diff 并保留用户修改。
- 全部 active spec 目前可能因未进入 Git 历史而不满足 deterministic close 前提。第五阶段只准备可验证结果；提交和关闭仍等待用户明确授权，不能擅自改变“不提交、不推送”的边界。

# Verification plan

- Static／unit：为语义令牌映射、状态变体、按钮／反馈状态、AdminDialog 焦点、主题切换、导航当前态和静态源代码护栏补充 Vitest；护栏扫描限定后台模板与兼容选择器，避免把正文内容或布局工具类误判为颜色依赖。
- Component behavior：保持 autosave、pagination、profile、content、incubator、polling、retrieval、audit、draft、publishing 等全部现有单元测试通过；对迁移后的共享原语检查 props／slots、禁用、loading、role／aria 和事件不变。
- E2E：运行登录、文章／项目／读书、栏目标签、媒体、回收站迁移、个人名片、公开体验、SEO、摄入、检索、工作台、审计、草稿、发布和任务取消的全部适用 Playwright；保留外发／发布对话框、乐观锁、自动保存 flush、冲突和部分失败断言。
- Visual：使用隔离固定数据生成 39 页面族 × light/dark × desktop/mobile 的 156 个本地全页截图，并为 loading／empty／error／conflict／stale／partial／running／cancel／dangerous confirmation 补充代表状态。公开页面逐项对照 Stitch，派生后台按语义层级、密度和跨页一致性人工复核。
- Accessibility：对 39 页面族固定状态运行 Playwright + axe WCAG 2.0／2.1 A/AA，要求零违规；人工检查键盘、跳链、焦点、对话框、移动抽屉、局部滚动、表单错误、轮询／自动保存播报、44px 触控、8px 间距、reduced motion 和状态非颜色依赖。
- Responsive：在 1440×1100、390×844 对全部页面断言 document.documentElement.scrollWidth <= clientWidth；记录 overflow offender 便于定位。不得用 body／根容器 overflow hidden 让断言假通过。
- Theme：在 SSR 首屏、hydration、系统默认、手动切换和刷新后检查主题保持；分别验证背景、表面、边框、阴影、正文、muted、状态、focus、browser theme-color 和 loading indicator，不以颜色反转作为深色实现。
- Performance／SEO：运行生产构建和现有站点质量入口；首页 Lighthouse 四项至少 90，公开 canonical、JSON-LD、RSS、sitemap、robots 不回退，后台继续 noindex,nofollow。
- Boundary：确认 git diff --name-only -- my_blog_fork apps/api packages/contracts harness/specs/active/20260807-github-discovery-ingestion.md harness/specs/active/20260807-github-source-crawler.md 为空，确认分支仍为 main、未恢复冻结 checkpoint、未添加共享 UI 依赖。
- Quality：从仓库标准入口运行 npm run quality:web，并补充全部适用 E2E、静态样式护栏、git diff --check。任何失败必须修复或明确记录为阻断，不得跳过、降级或把错误基线化。
- Evidence／Harness：生成 20260809-electric-editorial-ui-hardening.application.json；从 harness/ 运行 python -m tools.harness index 和 python -m tools.harness verify 20260809-electric-editorial-ui-hardening。只提交紧凑 evidence manifest；前序 task 的关闭与证据归档仍按各自生命周期独立处理。
