---
id: spec-20260804-incubator-workbench
level: L1
summary: 整合知识孵化导航、三池筛选、全局任务进度、健康状态与端到端质量门禁
load_when:
  - task:20260804-incubator-workbench
author: Gavin
task_id: 20260804-incubator-workbench
status: active
---

# Context

[知识孵化工作台需求设计](../../docs/product/knowledge-incubator.md) 规划的摄入、检索与索引、LLM 审计、孵化草稿和发布闭环五个纵向阶段已经实现、验证并压缩归档，当前没有其他 active spec。本规格启动第 6 段也是首期最后一段“工作台整合”。

现有 `/admin/incubator` 同时承担摄入表单和逐步追加的健康面板；待处理、审计和草稿三个池分别实现了筛选、分页、选择及轮询，但 URL 参数、默认隐藏规则、选择清理和状态反馈并不完全一致。管理主导航同时暴露“知识孵化”和“孵化草稿”，缺少工作台内部的稳定层级与当前页提示。

后端已经用同一 `incubator_jobs` 表承载摄入、文章索引、审计规划、LLM 审计、连接测试、草稿规划／生成和发布规划，但管理 API 只有按 ID 查询／取消，响应仍假设 `event_id` 必填，无法统一展示非摄入任务。Worker 健康、检索健康、LLM 配置和阶段计数已经可查询，但尚未形成带新鲜度、能力影响和修复入口的统一可操作视图。

本阶段命中跨端契约、用户可见行为、高增长查询和质量门槛风险，因此必须使用 SDD。它只整合既有能力，不重新设计前五段业务规则。

# Goal

管理员进入“知识孵化”后，可以通过一致的工作台导航在概览、待处理池、审计池、草稿池和任务中心之间定位；概览能回答“现在有什么需要处理、哪些能力可用、后台在做什么、最近是否失败”，三个池共享可复制的筛选／分页／选择语义，任务中心覆盖全部异步任务并提供安全取消。统一轮询在任务终态或页面不可见时停止。最终以确定性本地替身跑通从摄入到发布及工作台观测的代表性 E2E，并保持既有安全、可访问性和质量门禁。

# Non-goals

- 不新增摄入类型、审计角色、草稿角色、发布方式、状态转换、批量资格、模型协议或内容业务规则。
- 不实现 GitHub／Obsidian／PDF／Word／OCR 摄入、定时抓取、主动发现、存量文章体检、语义去重或超长资料自动分段。
- 不实现多用户、审批流、角色权限、通知中心、邮件／桌面通知、定时任务、自动重试编排或自动发布。
- 不提供跨页面持久批量选择；选择仅属于当前池、当前筛选和当前页。
- 不提供通用“重试任务”按钮。失败恢复继续使用来源、报告、草稿、索引或计划详情中的领域动作，避免绕过 LLM 未知结果和外发确认规则。
- 不引入 WebSocket、Server-Sent Events、Redis、Celery、独立消息队列、外部可观测平台或新的后台进程。
- 不让健康状态、Token 汇总或 telemetry 自动改变任务行为；它们只观察和引导管理员操作。
- 不修改公开站点信息架构或 SEO；除既有文章发布结果和参考资料外，不新增公共 API 或页面。

# Acceptance criteria

## 1. 工作台信息架构与统一壳层

- 管理主导航只保留一个“知识孵化”入口，不再把“孵化草稿”作为同级全局入口。所有孵化页面复用一个工作台壳层，提供“概览、待处理、审计报告、孵化草稿、任务”五个稳定入口。
- 工作台路由固定为 `/admin/incubator`、`/admin/incubator/inbox`、`/admin/incubator/audits`、`/admin/incubator/drafts` 和 `/admin/incubator/tasks`；现有 plan／detail 路由继续有效，并在壳层中保持所属栏目高亮和可返回的面包屑。
- 桌面、窄屏和键盘操作均可到达全部入口。当前栏目使用文本与 `aria-current` 表达，不能只靠颜色；壳层不引入横向页面溢出。
- 五个入口旁可显示服务端 attention count：待处理资料、待审阅／冲突报告、ready／publish_failed 草稿、queued／running 任务和最近失败任务。计数为导航提示，不在客户端重新推导业务资格。
- 详情页在来源 → 审计 → 草稿 → 发布计划 → 文章修订链中提供明确的上一步／下一步链接；链接只使用持久 ID，不依赖浏览器内存状态。

## 2. 聚合概览与待处理提示

- `GET /api/v1/admin/incubator/overview` 返回单一、版本明确的工作台快照：`generated_at`、三个池的状态计数、任务计数、最近失败数、最近批次摘要、近 1 日／7 日 Token 汇总、能力健康和最多 10 条 attention item。
- 概览计数来自当前数据库状态并明确默认范围。资料／审计／草稿计数按全部非永久删除记录分组，丢弃与终态单独返回；任务计数按全部当前 queued／running 与最近 7 日 terminal 任务分组，不把历史总量伪装为待办。
- attention item 只覆盖可操作异常或待办：失败／取消摄入、待审阅／冲突／stale 审计、ready／publish_failed／stale 草稿、失败任务、Worker 离线、索引 stale、LLM 未配置或最近连接测试失败。每项包含稳定 code、严重度、数量、中文摘要和受控目标类型／筛选参数。
- Web 端用目标类型白名单生成站内链接，禁止 API 返回任意可执行 URL。点击概览卡片进入对应池的已编码筛选 URL，不丢失状态语义。
- `/admin/incubator` 保留现有文件／URL 摄入表单，同时把“池状态、健康、任务、Token、最近批次”重组为可快速扫描的区域。最近批次只返回批次摘要，不在 overview 嵌入最多 50 个 event；批次详情继续按已有 endpoint 获取。
- 聚合查询不得逐项加载详情或产生按记录 N+1；至少以真实 SQLite 种入每池 100 条、任务 1,000 条的测试证明响应有界。普通列表仍默认 20、最多 100，overview 的 recent／attention 数量均有硬上限。

## 3. 三个池的共享筛选、分页与选择语义

- 待处理、审计和草稿池共享浏览器基础查询键：`status`、`sourceType`、`q`、`createdFrom`、`createdTo`、`page`。Web 映射到 API 的 `source_type`、`created_from`、`created_to`；无效、多值、超长或非法日期参数被规范化或由 API 以 `INVALID_FILTER` 拒绝。
- 审计池保留 `role`、`confidenceLevel`、`degraded`；草稿池保留 `role`、`targetArticleId`、`fromConflict`。领域筛选同样写入 URL，刷新、前进、后退和复制链接必须恢复相同结果。
- 三个池默认隐藏 `discarded`，显式选择该状态时可以查看；不得因默认值差异造成审计池泄露已丢弃记录。默认排序分别沿用实体的确定性时间字段，并始终追加 `id DESC` 打破并列。
- 共享分页固定每页显示 20 条、请求 21 条判断下一页，offset 最大 100000。应用筛选、重置筛选或改变领域筛选时回到第 1 页；浏览器 back／forward 不产生额外历史循环。
- 基础筛选 UI 使用共享组件或共享 composable，标签、日期、清除按钮、加载／空状态和错误呈现一致；领域筛选可通过 slot／配置扩展，不复制三套 URL 解析逻辑。
- 批量选择只覆盖当前页可见且具备对应资格的记录；改变 page、任一筛选、路由或数据刷新导致记录离开当前结果时清空或收敛选择。界面明确显示已选数量和不可选原因。
- 待处理池的审计规划、审计池的批量确认／丢弃、草稿池的有限批量发布继续调用各自既有后端资格校验；共享选择组件不得通过隐藏或禁用逻辑替代服务端校验。

## 4. 全局任务查询契约

- `GET /api/v1/admin/incubator/jobs` 新增有界任务列表，支持 `status`、`job_type`、`owner_type`、`created_from`、`created_to`、`limit`、`offset`；默认 20、最多 100、offset 最大 100000，按 `created_at DESC, id DESC` 稳定排序。
- 列表和现有 `GET /jobs/{job_id}` 使用通用响应，不再要求 `event_id` 非空。每个任务返回 job ID／type／status／progress／attempts／cancellation requested／安全错误／时间，以及解析后的 `owner_type`、`owner_id`、`owner_label` 和可选 `resource_type`／`resource_id`。
- owner 解析覆盖当前全部八种数据库归属：event、article revision、audit plan item、audit version、connection test、draft plan item、draft version、publish plan item；数据库 `ck_incubator_jobs_single_owner` 继续保证恰有一个 owner。未知或被逻辑隐藏的关联显示稳定占位，不导致整个列表 500。
- `job_type` 使用当前有界集合：`file_ingest`、`url_ingest`、`article_index`、`audit_plan_item`、`llm_audit`、`llm_connection_test`、`draft_plan`、`draft_generate`、`publish_plan`。API 拒绝未知筛选值；Web 对每个类型提供中文标签。
- Alembic 为高增长任务列表增加满足实际查询的复合索引，至少覆盖 `(status, created_at, id)` 与 `(job_type, created_at, id)`；迁移可从当前 head 升级、降级再升级，不重写历史任务。
- `POST /jobs/{job_id}/cancel` 沿用现有语义并返回通用任务响应：queued 立即 cancelled，running 只登记 cancellation request，terminal 为幂等无变化。响应增加 `cancellable` 和可选 `cancellation_warning_code`；LLM 已发送时提示可能已计费，最终发布事务没有 job 且不可取消。
- 任务 API 不返回 API Key、请求／响应正文、完整提示、原始 HTML、资料正文或模型向量。错误消息使用现有净化规则；日志只关联 job ID 和稳定 error code。

## 5. 任务中心与领域跳转

- `/admin/incubator/tasks` 显示全部任务类型、状态、进度、尝试次数、归属、排队／运行耗时、完成时间和错误摘要，支持与 API 一致的 URL 筛选和有界分页。
- `/admin/incubator/tasks/{id}` 使用现有单项 API 提供稳定详情页；从 owner／resource 元数据跳转到来源、文章版本、审计、草稿或计划详情。Web 使用资源类型白名单映射路由，不拼接后端任意路径。
- queued／running 任务显示取消操作；running LLM 任务在确认中明确“不能保证停止计费，只阻止后续业务步骤”。取消成功后状态和关联详情同步刷新。
- failed 任务显示领域恢复入口和错误说明，但不提供通用重试。`LLM_OUTCOME_UNKNOWN` 必须引导到相应审计／草稿详情进行人工处理，不能创建隐式重发。
- 进度条同时提供可读百分比和状态文本。没有细粒度进度的任务使用阶段文本，不能把未知进度显示成 0% 完成。
- 列表空、加载失败、任务被删除／隐藏、Worker 离线和权限过期均有明确状态；401 继续由现有管理员中间件处理，不在页面保存认证令牌。

## 6. 能力健康与就绪判定

- overview 统一返回 `overall_state = ready|degraded|blocked` 和五个 component：Worker、检索模型、文章索引、LLM 审计模型、LLM 生成模型。每项包含 state、稳定 code、中文 message、`observed_at`、影响的 capability 和安全 action type。
- `ready` 表示对应能力可立即执行；`degraded` 表示部分能力仍可用但存在明确限制；`blocked` 表示对应能力不能启动。总体状态在全部 component ready 时为 ready，Worker 离线时为 blocked，其他任一非 ready 且仍有基础能力可用时为 degraded。
- Worker 健康显示最后心跳、TTL、queued／running 数、最老 queued age 和当前 running job 摘要。只观察当前单 Worker 架构，不自动扩并发或领取任务。
- 检索 component 复用现有 manifest 校验和 index health；索引 stale 必须区分模型不可用与等待索引。重建按钮继续要求 CSRF，全量重建保留二次确认并显示已登记／复用任务数量。
- LLM component 的页面加载只读取本地配置和最近连接测试，不自动访问供应商。审计模型与生成模型分别判定；API Key 永不返回。连接测试仍需管理员显式触发，并通过任务中心观察进度／结果。
- 健康 action type 只允许 `open_tasks`、`open_inbox`、`open_audits`、`open_drafts`、`rebuild_missing_indexes`、`run_connection_test` 或 `none`。Web 对需要写操作的 action 再显示确认并执行原有受 CSRF 保护 endpoint。
- 未提供真实 API Key 时 LLM 审计／生成保持 `blocked/not_configured`，页面仍允许摄入和查看历史；测试环境只有显式配置本地 OpenAI-compatible double 时才显示 ready，绝不伪造真实供应商成功。

## 7. Token 与运行摘要

- overview 的 Token 区域复用现有 ledger，显示近 1 日、近 7 日总量，并按 `connection_test`、`initial_audit`、`rerun_audit`、`initial_generation`、`regeneration` 和 retry 关系分组；实际值与估算值分别汇总，不把低精度估算展示为精确消费。
- “查看明细”进入受保护的 `/admin/incubator/tasks` 对应 LLM 类型筛选或现有 token 查询视图；本阶段不增加费用换算、预算或消费阻断。
- 最近失败摘要按稳定 error code 聚合并链接任务筛选；前端统一使用 `incubatorErrorLabel`，未知 code 显示安全 code 本身而不是丢失信息。

## 8. 统一刷新、轮询与恢复

- 提供共享的孵化轮询 composable：仅当页面存在 queued／running／planning／generating／publishing 等非终态对象时以不短于 2 秒间隔刷新；全部终态后立即停止。
- 页面进入后台或不可见时停止计时器，重新可见时立即刷新一次并按最新状态决定是否恢复；组件卸载、路由变化和认证失效时清理全部 timer。不得因重复调用启动多个并行轮询器。
- overview 在可见时最多每 10 秒刷新健康与计数；用户触发摄入、取消、重建、连接测试或批量操作成功后立即刷新。短暂网络错误保留最后成功快照并显示“数据可能已过期”，使用有界退避，不把能力状态误判为失败。
- 每个聚合响应携带 `generated_at`，Web 显示最后更新时间。客户端不得把来自不同时间的局部请求拼接成看似原子的健康结论。
- 轮询只做 GET；任何重试、取消、确认、外发、重生成、重建或发布仍要求显式用户写操作，绝不由刷新逻辑触发。

## 9. 状态、错误与可访问性一致性

- 将来源、任务、审计、草稿、计划、检索和发布错误映射集中在 typed 常量／函数；状态 chip、严重度、未知值 fallback 和日期格式由共享组件处理。API 新增状态时 TypeScript 或测试必须显式失败，不能静默显示空白。
- 所有页面的加载、空结果、无权限、失败、stale、cancelled、degraded 和成功状态有可读文本；颜色图标均为辅助信息。动态任务与批量结果使用适当 `aria-live`，焦点在弹窗关闭和路由操作后可预测恢复。
- 筛选表单有可见 label，日期输入使用本地日期但发送明确 UTC 边界；开始时间晚于结束时间在前端提示且 API 返回 `INVALID_FILTER`。
- 工作台窄屏布局、长标题、长安全错误码和 100 条任务页不得横向撑破页面；任务表可切换为语义列表或提供可访问滚动容器。
- 所有写操作继续要求 Session＋CSRF；读取要求 Session。统一组件不得绕过 middleware、把 CSRF 写入持久存储或把管理员数据带入公开 Nuxt payload。

## 10. 契约、测试与首期完成门槛

- OpenAPI 同步 `packages/contracts/openapi.json` 与 Web 类型；overview、通用 job、owner、health component、attention item 和任务筛选均有明确 Schema，禁止以无界 `dict[str, Any]` 代替核心契约。
- Pytest 覆盖全部 job owner 映射、列表筛选／分页／排序、非 event job 详情、取消状态、健康总体判定、attention 计数、Token 精度分组、overview 有界性、非法日期及迁移索引。
- Vitest 覆盖共享 URL 解析／序列化、筛选重置、选择清理、状态／错误穷尽映射、健康严重度、owner 路由白名单、轮询启动／停止／可见性恢复和过期快照提示。
- Playwright 新增工作台整合场景：导航五入口、概览 attention 跳转、三个池筛选 URL 往返、任务中心观察并取消一个安全可取消任务、Worker／检索／LLM 健康呈现。
- 现有 `publishing-loop.spec.ts` 继续作为“摄入 → 审计 → 草稿 → 发布 → 公开引用 → 回滚”代表性业务闭环；增加断言使关键异步任务可在任务中心定位。第三方 LLM、网页来源和本地检索均使用确定性本地替身，不需要真实 API Key 或公网。
- API 全量 Pytest、Ruff、Alembic 升降级、OpenAPI snapshot、Web Vitest、typecheck、production build、全部 Playwright E2E、WCAG A／AA 和 Lighthouse 四项 `>= 90` 继续通过。
- 更新 API／Web／contracts L1 边界说明和知识孵化首期完成状态；只提交紧凑 evidence manifest，不提交数据库、原始资料、模型二进制、重日志、报告、截图或测试密钥。

# Risks

- **聚合页变成昂贵总查询**：所有 recent／attention 有硬上限，计数批量聚合，任务列表有复合索引，测试用放大数据断言无 N+1 和无界嵌套。
- **状态被前端重复解释**：API 提供结构化 capability／severity／attention，前端只映射展示和受控跳转，不重新推导发布或批量资格。
- **非摄入任务无法表示**：通用 job 响应把 `event_id` 改为可选并解析八种 owner；owner 缺失时降级显示，不让整个工作台失败。
- **轮询泄漏与请求风暴**：统一 composable 单实例计时、终态停止、页面隐藏暂停、短暂错误退避并在卸载时清理。
- **批量选择作用于旧数据**：选择绑定当前查询与当前页，任何查询／分页／刷新变化都收敛；后端继续做最终资格和版本校验。
- **健康状态误导**：每项标注观测时间、能力影响和本地／外部边界；未配置真实 LLM 明确 blocked，不因测试 double 或最近历史成功伪造当前 ready。
- **任务中心绕过领域安全**：只提供查询和现有取消；重试、外发、确认与发布必须回到领域页面执行原有闸门。
- **范围膨胀**：本阶段整合已存在的首期能力，不借 UI 重构增加新来源、模型、队列、权限或自动化行为。

# Verification plan

1. **TDD**：先为通用 job owner、任务筛选、overview 聚合、健康判定、共享 URL、选择生命周期和轮询可见性建立失败测试，再实现最小契约与组件。
2. **Contract**：从当前 Alembic head 升级、降级再升级并检查任务复合索引；生成 OpenAPI，断言 overview／jobs／health／attention Schema、nullable owner 字段和 Web 类型一致。
3. **Integration**：以真实临时 SQLite 为八类 owner 各创建任务，验证列表、详情、取消、缺失 owner、稳定排序、聚合计数、最近失败、Token 精度和 Worker 心跳 TTL。
4. **Security**：伪造 owner、job type、目标跳转、日期、错误消息、CSRF 和未认证请求；证明 Web 路由白名单生效，API 不泄漏正文、Key、提示、响应或向量，轮询只执行 GET。
5. **E2E**：使用现有隔离包装进程和确定性 fetch／retrieval／LLM doubles，覆盖工作台导航、三个池、任务观察／取消、健康状态，并继续跑通完整知识发布闭环。
6. **Quality**：执行 API Pytest／Ruff、Web Vitest／typecheck／build／全部 E2E／axe／Lighthouse；对 overview 与 1,000 条任务种子执行有界查询检查。
7. **Harness**：更新相关 L1 边界元数据后，从 `harness/` 运行 `python -m tools.harness index`；全部门槛通过后写入紧凑 evidence，并运行 `python -m tools.harness verify 20260804-incubator-workbench`。关闭前确保本 active spec 已存在于 Git 历史，最终只能用 `python -m tools.harness close 20260804-incubator-workbench` 压缩归档。
