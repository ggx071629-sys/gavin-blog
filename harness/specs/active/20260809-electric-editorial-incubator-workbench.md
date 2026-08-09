---
id: spec-20260809-electric-editorial-incubator-workbench
level: L1
summary: 将知识孵化全链路迁移到 Electric Editorial 双主题高密度工作台并保留全部业务契约
load_when:
  - task:20260809-electric-editorial-incubator-workbench
author: Gavin
task_id: 20260809-electric-editorial-incubator-workbench
status: active
---

# Context

第三阶段已经在当前工作树中建立非孵化后台的 Electric Editorial 双主题令牌、admin-core 布局、侧边导航与基础界面模式；知识孵化的 12 个路由仍全部使用旧 admin 布局、slate／blue／rose 工具类和独立的 IncubatorShell。第三阶段 spec 目前仍为 active，且没有 application evidence，因此本 spec 只把已存在的 admin-core 代码视为实现基线，不把第三阶段描述成已经通过完整 VDD 收口；第四阶段也不代替或伪造第三阶段的验证结果。

web_prototype/ 共 17 个公开站点 Stitch 页面，没有后台、知识孵化、AI 审计、草稿生成或任务中心原型。第四阶段不能声称逐像素复刻孵化页面。视觉依据按优先级固定为：已落地的 Electric Editorial 双主题语义令牌与 admin-core 基础组件、现有知识孵化真实路由和行为、apps/web/README.md 记录的工作台契约、现有 E2E／单元测试。公开原型只提供品牌、颜色和排版语言，不提供后台页面布局事实。

设计方向是面向单一管理员的“证据优先编辑流水线”，继续使用第三阶段的 variance=3、motion=2、density=8。来源→审计→草稿→发布是唯一允许强化的视觉签名，因为它编码真实业务链；不得把页面改造成通用 AI 控制台、营销 Bento、虚构指标看板或装饰性流程图。概览负责判断下一步，资源池负责筛选和批处理，详情页负责证据、决策与可回溯操作，任务中心负责真实阶段和失败处理。

ui-ux-pro-max 的本地规则仅用于可验证的响应式与可访问性约束：移动端表格采用卡片重排或组件内受控横向滚动、整页不得横向溢出、触控目标至少 44×44px且相邻目标至少 8px、焦点可见、提交有 loading／success／error 反馈、危险操作必须确认、尊重 reduced motion。其营销布局、字体、配色、Pinia 等与现有项目不符的建议不采用。frontend-design 用于审查模板化风险和保持有意图的视觉层级；本阶段不加载或引入另一套重叠设计体系。

原型、路由与现有页面文件对应如下：

| 原型依据 | 路由 | 现有页面文件 | 现状与第四阶段处理 |
| --- | --- | --- | --- |
| 无孵化原型；由 admin-core 与真实摄入工作流派生 | /admin/incubator | apps/web/pages/admin/incubator/index.vue | 概览、混合摄入、attention、健康、任务、Token 和最近批次；迁移到新壳层并重组信息层级 |
| 无孵化原型；由高密度资源池模式派生 | /admin/incubator/inbox | apps/web/pages/admin/incubator/inbox/index.vue | 保留 URL 筛选、有界分页、跨刷新选择收敛和审计计划入口 |
| 无孵化原型；由证据详情工作台模式派生 | /admin/incubator/inbox/:id | apps/web/pages/admin/incubator/inbox/[id].vue | 保留安全原文／Markdown、修订、任务、检索预览、冲突及状态操作 |
| 无孵化原型；由外发审批模式派生 | /admin/incubator/audit-plans/:id | apps/web/pages/admin/incubator/audit-plans/[id].vue | 保留逐项规划、Token 摘要、外发确认、轮询与逐项结果 |
| 无孵化原型；由审计资源池模式派生 | /admin/incubator/audits | apps/web/pages/admin/incubator/audits/index.vue | 保留筛选、分页、选择收敛、批量确认和批量丢弃 |
| 无孵化原型；由人机审计证据台模式派生 | /admin/incubator/audits/:id | apps/web/pages/admin/incubator/audits/[id].vue | 保留 AI 原判、证据、旧文快照、调用、Token、人工改判、冲突裁决与重跑 |
| 无孵化原型；由草稿资源池模式派生 | /admin/incubator/drafts | apps/web/pages/admin/incubator/drafts/index.vue | 保留筛选、分页、选择收敛和批量发布计划 |
| 无孵化原型；由编辑／预览／版本模式派生 | /admin/incubator/drafts/:id | apps/web/pages/admin/incubator/drafts/[id].vue | 保留角色化编辑、自动保存、冲突、预览、版本、diff、Token、重生成和发布准备度 |
| 无孵化原型；由外发审批模式派生 | /admin/incubator/draft-plans/:id | apps/web/pages/admin/incubator/draft-plans/[id].vue | 保留外发范围、锚点、候选分类、Token 估算、确认与轮询 |
| 无孵化原型；由发布预检与执行模式派生 | /admin/incubator/publish-plans/:id | apps/web/pages/admin/incubator/publish-plans/[id].vue | 保留阻断／过期、逐项风险与差异、最终确认、原子结果和部分失败 |
| 无孵化原型；由任务观察池模式派生 | /admin/incubator/tasks | apps/web/pages/admin/incubator/tasks/index.vue | 保留全任务类型筛选、分页、真实阶段、失败信息和安全取消 |
| 无孵化原型；由任务诊断详情模式派生 | /admin/incubator/tasks/:id | apps/web/pages/admin/incubator/tasks/[id].vue | 保留归属、阶段、资源链接、错误、未知结果告警、轮询和安全取消 |

缺失与冲突状态明确如下：

- Stitch 无任何后台或孵化图，因此不存在可用于孵化页面的浅色／深色像素基准；验收依据是派生设计规则和跨页面一致性，不能声称原型一比一。
- 当前 IncubatorShell 在每页独立请求 overview，旧 admin 布局与 admin-core 重复提供主导航；迁移后后台主导航仍只有一个“知识孵化”入口，工作台二级导航只在孵化上下文内出现。
- 现有部分详情页直接使用 setInterval，部分列表使用 useIncubatorPolling；视觉重构不得顺便改变轮询周期、暂停、终止条件或业务状态。
- 现有自定义确认层的焦点管理不完整。第四阶段允许在不改变请求与确认语义的前提下修复对话框可访问性；若无法完整实现焦点捕获、Esc、返回焦点和标签，则保留原生 confirm，不以视觉统一换取安全回归。

# Goal

在不改变 API 契约、数据库模型、公开／后台 URL、认证规则、知识孵化状态机、轮询语义、外发确认和发布原子性的前提下，将 12 个知识孵化路由迁移到 Electric Editorial 双主题高密度后台体系，形成移动可用、证据可扫描、操作可回溯并满足 WCAG AA 的完整孵化工作台。

# Non-goals

- 不修改 apps/api/、数据库、Alembic、packages/contracts/、认证中间件、Cookie／CSRF／Session 或任何请求／响应字段。
- 不改变 12 个现有后台 URL、查询参数名、分页上限、每页数量、默认隐藏 discarded 的规则、业务状态值、确认字段或跳转链。
- 不新增模型、提示词、第三方 LLM、爬虫、检索算法、摄入来源、批处理能力、统计口径或任何后端未支持的功能。
- 不把轮询改造成 WebSocket／SSE，不改变不短于 2 秒、页面隐藏暂停、终态停止及概览最多每 10 秒刷新的既有语义。
- 不虚构趋势图、成功率、节省时间、AI 评分、实时进度或不存在的指标；无细粒度进度时继续显示真实阶段文本，不显示伪造百分比。
- 不重新设计公开博客或非孵化后台页面；只允许为知识孵化复用或补强通用 admin-core 基础组件和语义令牌。
- 不允许 admin-core 通用布局、导航、令牌或基础组件导入知识孵化专属类型、API、状态、composable 或页面组件；依赖只能从孵化层指向通用后台层。
- 不引入新的 UI 框架、状态管理、图标库、字体、动画库或运行时依赖。
- 不修改、移动或删除 my_blog_fork/，不建立共享依赖、submodule、符号链接或远程 UI 包。
- 不修改、解冻、关闭或继续实现 20260807-github-discovery-ingestion 与 20260807-github-source-crawler。
- 不恢复或合并 codex/frozen-github-ingestion-checkpoint，不提交或推送。

# Acceptance criteria

- 12 个知识孵化路由全部使用 admin-core，或使用建立在 admin-core 之上的无业务耦合孵化工作台组合；旧 admin 布局不再承载这些路由。主导航仅保留一个“知识孵化”入口，桌面侧栏与移动抽屉的当前项、跳到正文、焦点和退出行为保持正确。
- IncubatorShell 重构为孵化上下文壳层：保留概览／待处理／审计报告／孵化草稿／任务五入口、服务端 attention 数量、aria-current 与面包屑；窄屏下二级导航可扫描、可键盘到达且不挤压主内容。
- 详情页的 IncubatorChainNav 保留来源→审计计划／报告→草稿计划／草稿→发布计划→文章修订的真实上一步／下一步关系。链条状态必须来自真实数据，不显示尚不存在或不可到达的步骤，不能只靠颜色表达当前与完成状态。
- 概览页按“立即处理→摄入→池状态→系统健康与任务→最近批次”的操作优先级组织真实信息；混合 Markdown／TXT 与 URL 提交、限制说明、逐项结果、重复／不支持反馈、部分成功重试、attention、能力健康、索引重建、任务摘要、Token 消费和最近批次行为全部保留。
- 待处理池保留 status／source_type／q 的稳定 URL 查询、有界分页、刷新／前进／后退／复制链接一致性、选择随查询／换页／刷新收敛、仅 inbox 可选和审计计划入口。移动端筛选区按主要条件优先折叠，已应用条件始终可见且可清除。
- 待处理详情保留原始内容纯文本安全预览、标准化 Markdown、标题／正文修订、基础修订号乐观锁、409 冲突、修订历史、任务历史、全文／降级检索预览、丢弃、恢复、失败重试和永久删除确认。任何原始 HTML 不得注入 DOM。
- 审计计划保留逐项本地规划状态、来源数量、Token 估算、外发范围、明确的 external_transfer_confirmed 确认和逐项确认结果；计划未 ready 时不能提前确认，失败、过期和部分结果必须有文本语义。
- 审计池保留 status／role／confidence／source_type／degraded／日期／关键词筛选、URL 同步、有界分页、选择收敛、批量确认和批量丢弃。状态、置信、降级和冲突使用一致的状态语言并附文字／图标，不只使用色块。
- 审计详情把“结论与可执行操作”置于前部，把证据片段、候选旧文快照、模型调用、Token 明细与人工决定组织为可扫描区域；AI 原判和当前有效判定必须明确区分。人工改判、目标文章、确认、丢弃、冲突裁决、反馈重跑与创建草稿计划的资格和请求保持原样。
- 草稿池保留 role／status／日期／关键词筛选、URL 同步、有界分页、选择收敛和仅对就绪草稿创建批量发布计划的资格检查；已发布、发布失败、冲突来源与角色均有非颜色状态说明。
- 草稿计划保留外发范围、模型、签发锚点、分类候选、Token 估算、external_transfer_confirmed 确认和规划轮询；确认层具备 dialog 语义、可读标题、焦点进入／约束／返回、Esc 和明确取消。
- 草稿详情保留 supplement／rewrite／new_branch 三类真实编辑结构、AutosaveQueue、版本冲突、未保存／保存中／已保存／错误状态、角色预览、发布准备度、slug 冲突、版本激活、版本 diff、Token 账本、反馈重生成、丢弃和创建发布计划。发布相关操作前必须 flush 待保存内容或按既有失败语义阻断。
- 发布计划保留 blocked／stale／ready 等资格、逐项角色、风险、阻断码、差异、引用公开性、执行记录和最终 publish_confirmed 确认；逐项发布保持既有原子语义，成功、失败、部分失败及目标文章／修订链接全部可追溯。
- 任务列表保留 status／job_type／owner_type／日期筛选、URL 同步、有界分页、全部任务类型、真实阶段、错误码／错误消息和安全取消；任务详情保留归属、阶段、资源链接、LLM_OUTCOME_UNKNOWN 告警和终态。取消请求不能被视觉状态误报为已取消。
- 轮询继续遵守现有终态集合、周期和可见性策略；刷新导致的数量、状态和时间变化不得抢夺焦点、重置用户输入或造成屏幕阅读器播报风暴。仅对操作结果和关键终态变化使用克制的 aria-live。
- 浅色和深色是分别调校的界面：背景层、边框、阴影、文本层级、状态面和交互态都使用语义令牌。酸性绿不用于未达到 4.5:1 的小号文字；状态与正文达到 WCAG AA，焦点达到可见性要求。
- 桌面端维持高密度双栏／主从布局；390×844 下重排为单列，筛选、批量操作、长标题、原文、Markdown、diff、Token 和任务错误均不造成页面级横向溢出。表格或代码区域只允许组件内部受控滚动。
- 所有核心操作可键盘完成；视觉顺序与焦点顺序一致；输入具备可见标签和就近错误；触控目标至少 44×44px，相邻目标至少 8px；动画仅用于 1–2 个关键反馈并尊重 prefers-reduced-motion。
- 保留现有 data-testid 及 ingestion、retrieval、workbench、LLM audit、draft、publishing 高价值闭环。为修复脆弱选择器可新增稳定语义或 testid，但不得通过删除断言、跳过用例或降低规则来获得通过。
- 12 个路由执行 light/dark × 1440×1100/390×844 的四象限视觉与无溢出检查，共 48 个基础视图；另覆盖 loading、empty、partial success、failed、conflict、stale、running、cancellation requested、cancelled 等代表动态状态。截图与重型报告只留本地。
- 每个页面族至少一个固定数据代表状态执行 axe WCAG 2.0／2.1 A/AA，自动扫描零违规；对话框、批量操作栏、轮询终态、错误反馈和移动导航执行人工键盘／屏幕阅读器语义检查。
- Nuxt 类型检查、全部 Vitest、生产构建、适用 Playwright、质量门禁、git diff --check 和 Harness 验证通过；公开首页 Lighthouse 四项继续不低于 90，所有管理页维持 noindex,nofollow。
- 实现 diff 不得包含 my_blog_fork/、两个冻结 spec、apps/api/、packages/contracts/ 或数据库迁移；若发现完成 UI 必须改变这些边界，停止实现并单独升级 spec，不得在本阶段偷渡。

# Implementation slices

1. 壳层与概览：把 12 个路由切换到 admin-core，重构 IncubatorShell、二级导航、面包屑和 ChainNav，统一知识孵化语义样式，完成概览与摄入页。通过后台导航、摄入、attention、健康、轮询、双主题和移动端基线后再进入下一切片。
2. 来源与审计：重构待处理池／详情、审计计划、审计池／详情；保留 URL 状态、选择收敛、安全原文、外发确认、证据、人工改判、冲突和重跑闭环。完成 ingestion、retrieval、LLM audit E2E 后收口。
3. 草稿与发布：重构草稿池／详情、草稿计划和发布计划；保留自动保存与 flush、版本冲突、diff、重生成、发布预检、最终确认、逐项原子结果和修订链。完成 draft、publishing E2E 后收口。
4. 任务与全矩阵：重构任务列表／详情，统一真实阶段、取消和错误语义；执行 48 个基础视觉视图、代表动态状态、axe、键盘、无溢出、公开与非孵化后台回归，修完缺陷后才可标记 verified。

# Risks

- 第三阶段实现已存在但生命周期证据尚未收口。若 admin-core 在第四阶段过程中变化，必须同时回归其全部非孵化消费者；第四阶段 evidence 只能证明本任务范围，不能补写或冒充第三阶段 evidence。
- Stitch 缺失孵化原型，视觉判断存在主观漂移风险。所有新增层级必须能对应真实任务、状态或证据，不能以“更像 AI 后台”为理由引入模板化卡片、渐变、装饰编号或虚构可视化。
- 12 个页面包含摄入、选择、轮询、自动保存、冲突与外发／发布确认，直接抽取大型通用组件容易把业务状态上提到 admin-core。只抽取无领域知识的外观原语，领域组合保留在 incubator 范围。
- 当前页面同时存在统一 polling composable 与手写 setInterval。仅为视觉改版重写轮询可能改变隐藏页、终态或重复请求行为；除非有行为测试覆盖，不把轮询架构重构纳入本阶段。
- 概览和五入口壳层都请求 overview，迁移时可能产生重复请求或旧计数。允许在孵化专属层内部消除重复，但不得把孵化 API 放入通用后台布局。
- 大量状态色在浅色与深色中容易出现小字对比不足，尤其酸性绿、amber、rose 和 muted 文本。每种状态需按背景实测，不允许用“品牌色例外”绕过 AA。
- 筛选器、批量操作和长 diff 在移动端最容易造成页面溢出；不能通过缩小字体、44px 以下按钮或隐藏必要状态来过关。
- 轮询更新可能令视觉截图不稳定并造成 aria-live 噪声；视觉测试使用固定数据和可控时钟／状态，运行时播报只覆盖关键终态，不能关闭真实轮询来伪造稳定。
- 自定义外发、发布和重生成对话框涉及焦点捕获、Esc、返回焦点与异步禁用。缺一项即为可访问性缺陷；无法安全完成时保留原生确认。
- 当前工作树包含前几阶段的大量未提交修改。实施和回退必须按切片限定文件并保留用户改动，不得使用 reset、checkout 或清理命令覆盖现有成果。

# Verification plan

- TDD／unit：保持 incubator、incubator-polling、retrieval、llm-audit、drafts、publishing 和 admin 单元测试通过；为壳层当前态、attention、链条导航、状态语义、对话框焦点、筛选展开与移动操作补充针对性 Vitest。
- E2E：运行 apps/web/tests/e2e/incubator.spec.ts、workbench.spec.ts、retrieval-loop.spec.ts、llm-audit-loop.spec.ts、draft-loop.spec.ts、publishing-loop.spec.ts；新增或扩充任务详情／取消、冲突、部分发布失败和外发对话框键盘行为，保留所有既有断言。
- Visual：以固定隔离数据访问 12 个路由，生成 light/dark × 1440×1100/390×844 本地截图；逐项检查布局、层级、状态、焦点、组件内部滚动和整页溢出，并对 loading／empty／partial／failed／conflict／stale／running／cancel 代表态补充截图。因无 Stitch 孵化原型，只按已声明派生规则验收，不声称像素级原型对比。
- Accessibility：Playwright + axe 对概览、三个池、来源／审计／草稿详情、三种计划、任务列表／详情代表状态执行 WCAG 2.0／2.1 A/AA，要求零违规；人工验证跳到正文、侧栏／抽屉、二级导航、面包屑、链条导航、批量栏、焦点返回、对话框、状态非颜色依赖、44px 触控和 reduced motion。
- Responsive：在 1440×1100 与 390×844 检查全部路由 document.documentElement.scrollWidth <= clientWidth；原文、Markdown、代码、diff 和必要表格仅允许自身容器受控滚动，筛选和批量操作在窄屏保持可读与可达。
- Behavior：验证 URL 查询刷新／前进／后退／复制、分页边界、选择收敛、默认隐藏 discarded、乐观锁、AutosaveQueue flush、外发确认、发布确认、原子结果、取消请求、轮询间隔／隐藏暂停／终态停止及 overview 更新时间全部不变。
- Regression：运行非孵化后台导航／登录／编辑代表闭环和公开站点质量测试，确认共享令牌或基础组件没有破坏第三阶段代码基线；公开首页 Lighthouse performance、accessibility、best-practices、SEO 继续至少 90。
- Isolation：运行 git diff --name-only -- my_blog_fork apps/api packages/contracts harness/specs/active/20260807-github-discovery-ingestion.md harness/specs/active/20260807-github-source-crawler.md，确认实现阶段无越界修改；确认当前分支仍为 main 且未恢复冻结 checkpoint。
- Quality：从仓库标准入口运行 npm run quality:web，并补充生产构建、适用 Playwright、git diff --check。不得跳过失败用例、降低 axe／Lighthouse 阈值或删除断言。
- Harness：从 harness/ 运行 python -m tools.harness index 和 python -m tools.harness verify 20260809-electric-editorial-incubator-workbench；实现验证后仅提交紧凑 application／Harness evidence manifest，不提交截图、trace、Lighthouse 原始报告或其他重型产物。
