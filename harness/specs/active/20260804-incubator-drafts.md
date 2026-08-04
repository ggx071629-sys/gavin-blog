---
id: spec-20260804-incubator-drafts
level: L1
summary: 将已确认审计转化为可版本化生成、人工编辑、差异预览和安全重生成的孵化草稿
load_when:
  - task:20260804-incubator-drafts
author: Gavin
task_id: 20260804-incubator-drafts
status: active
---

# Context

[知识孵化工作台需求设计](../../docs/product/knowledge-incubator.md) 的摄入、检索和 LLM 审计三段已经实现、验证并压缩归档，当前没有其他 active spec。系统已有不可变资料修订、文章发布修订、审计版本、证据快照、人工有效角色／目标、第三方 LLM 配置、外发确认、调用 attempt、Token 账本和串行持久 Worker。本规格启动第 4 段“孵化草稿”。

上一阶段的报告确认只表示管理员接受审计结论并授权后续生成，不会自动调用 generation model。生成仍会向第三方发送内容并产生费用；增补／重构需要发送目标文章当前发布快照，新分支需要发送现有栏目和标签候选。所有 AI 输出必须先进入独立孵化草稿池，不能修改普通文章工作副本、创建普通文章草稿或影响公开站点。

当前文章编辑器已有 900ms 自动保存队列、版本号乐观锁、Markdown 实时预览和发布前 `flush()` 屏障。孵化草稿复用这些交互原则，但拥有独立数据模型、角色特定结构和生成版本；后台生成任务不得覆盖生成期间发生的人工编辑。

# Goal

管理员可以从当前有效且已确认的审计报告显式规划并确认一次草稿生成。Worker 为增补生成结构化锚点补丁，为重构生成完整新正文和可选标题／摘要，为新分支生成完整正文及受现有分类约束的建议元数据。结果作为不可变生成版本进入独立草稿池，并复制为带乐观锁的工作副本。管理员可以编辑、自动保存、预览角色特定差异、比较和激活历史生成版本，并在填写反馈且确认外发后重生成；任何审计、资料或目标文章变化都会显式使草稿失效。

# Non-goals

- 不执行“确认并发布”，不修改、合并或替换正式文章，不创建文章发布修订、索引任务或公开来源引用。
- 不实现有限批量发布、文章版本差异／回滚、最终 slug 冲突处理或新分支发布前相似性复检；这些属于下一段“发布闭环”。
- 不自动生成草稿；审计报告确认后仍需管理员显式发起生成并确认第三方外发。
- 不允许 conflict 角色直接生成。冲突必须在审计阶段改判／裁决为增补、重构或新分支并完成逐条确认。
- 不允许 AI 创建栏目或标签，不因建议缺失自动创建分类，不改变目标文章 slug、首次发布时间或当前分类。
- 不实现多轮对话、流式前端生成、自动分段生成、多个审计报告合并生成、多人协作或审批流。
- 不引入新的模型供应商协议、独立队列、Redis、Celery、对象存储、`infra/` 或 `deploy/` 目录。
- 不使用真实 API Key 或公网供应商完成自动化测试；默认测试只使用确定性本地同契约替身。

# Acceptance criteria

## 1. 草稿与生成版本数据边界

- Alembic 增加职责分离的生成计划／计划项、孵化草稿、不可变草稿版本、生成 attempt 和角色特定结构实体。表名可按现有惯例调整，但逻辑草稿、当前可编辑工作副本和不可变生成结果必须分离。
- 每个孵化草稿唯一绑定一个当前有效的已确认审计版本，并冻结资料 ID／修订、有效角色、目标文章 ID／发布修订、是否来自冲突裁决、审计证据和首次生成计划。重复确认或任务重放不得创建第二个逻辑草稿。
- 草稿状态至少覆盖 `queued`、`generating`、`ready`、`regenerating`、`stale`、`discarded`、`failed`；`publishing` 和 `published` 留给下一阶段，不在本段产生。状态转换由后端集中校验。
- 草稿拥有单调递增的 `edit_version` 乐观锁、当前工作副本、当前激活生成版本指针和最后成功保存时间。自动保存只更新工作副本与 `edit_version`，不修改不可变生成版本。
- 每次成功的首次生成或重生成创建新的不可变草稿版本，保存版本号、角色、结构化内容、生成提示版本、generation model、服务标识、请求／响应 SHA-256、基础草稿版本、基础 edit version、反馈、attempt 与 Token 关系。旧版本不覆盖、不删除。
- `incubator_jobs` 保留全部现有 owner 行为，并增加生成计划项与生成 attempt／版本所需的外键 owner；数据库 CHECK 继续保证每个任务恰有一个归属。任务类型使用有界名称 `draft_plan` 与 `draft_generate`，租约、取消、不确定结果和幂等规则沿用审计阶段。

## 2. 生成资格与两阶段外发计划

- 只有最新、未失效、`status = confirmed` 且非 degraded 的审计版本可以生成；有效角色必须为 `supplement`、`rewrite` 或 `new_branch`。冲突原判即使已人工改判，也记录 `from_conflict = true`，供下一阶段强制逐条发布。
- `POST /api/v1/admin/incubator/draft-plans` 接受一个 `audit_id`，要求 Session＋CSRF，返回 `202` 与异步本地规划任务。首次生成始终逐条发起，不提供批量生成。
- Worker 冻结资料修订、已验证审计结论与证据、有效角色、generation prompt version、服务／模型、上下文估算及角色特定输入。增补／重构额外冻结目标文章完整当前发布快照；新分支冻结当前全部栏目和标签的 ID／名称／slug 候选。
- `GET /api/v1/admin/incubator/draft-plans/{plan_id}` 返回计划状态、将外发的资料／目标文章／分类范围、服务标识、generation model、估算输入／输出／总 Token、估算精度和失败原因，不在摘要中返回完整正文。
- 计划不可变。资料修订、审计有效决定／状态、目标文章发布修订、分类候选或 generation prompt version 变化时计划 stale，不能确认。生成确认前再次执行上下文预检；超过窗口以 `SOURCE_TOO_LONG` 拒绝，不截断或调用 LLM。
- `POST /api/v1/admin/incubator/draft-plans/{plan_id}/confirm` 必须携带 `external_transfer_confirmed = true`，才创建草稿／生成任务。首次确认弹窗明确说明将发送资料全文、审计结论，以及增补／重构时的目标文章全文或新分支时的分类候选，并显示 Token 估算。
- 配置缺失时返回 `LLM_NOT_CONFIGURED` 且不创建付费任务。generation model、generation 最大输出 Token 或上下文配置缺失均视为未配置；新增 `GAVIN_LLM_GENERATION_MAX_OUTPUT_TOKENS`，其他连接、安全和 tokenizer 语义复用审计配置。

## 3. 版本化生成提示与共同安全规则

- 生成提示有显式 `generation-v1` 版本，使用 system role 声明资料、文章、审计文本和反馈均是不可信 data。用户内容不能进入 system role、工具定义或 Schema。
- 所有模型可引用 ID、角色、文章、发布修订、标题锚点、栏目和标签均由后端生成并列入计划。输出引用不存在、跨计划、版本不符或越权的 ID 时整个结果以 `DRAFT_RESULT_INVALID` 失败，不能创建 ready 草稿版本。
- 使用现有 OpenAI-compatible 客户端和配置的 `structured_output_mode`。原生 JSON Schema 与 `json_object` fallback 使用相同严格后端 Schema；供应商原始响应只在内存解析，数据库只保存验证后的结构、响应哈希和安全错误摘要。
- 网络超时、`429` 和 `5xx` 最多自动重试 2 次并按 1 秒／4 秒退避；鉴权、模型不存在、请求格式与结构业务错误不自动重试。每次 attempt 和实际／估算 Token 进入现有账本，task type 区分 `initial_generation` 与 `regeneration`。
- 请求发出后 Worker 崩溃或结果未知时不自动重发，以 `LLM_OUTCOME_UNKNOWN` 失败；管理员必须通过新的重生成计划明确重试。请求发出后的取消不保证停止计费，attempt／Token 保留且响应不能覆盖工作副本。
- 标题最多 180 字符、slug 最多 160 且符合现有格式、摘要最多 320 字符、Markdown 必须非空且 UTF-8 编码后不超过 2 MiB。所有超限结果整体失败，不静默截断。

## 4. 增补草稿

- 后端从冻结的目标文章发布修订解析全部 H2／H3，为每个标题生成计划内稳定 `anchor_id`、层级路径、标题文本、出现序号和上下文校验值；这些锚点随计划发送给模型。
- 增补结构化输出固定包含一个 `anchor_id`、`placement = after_heading|before_next_heading`、Markdown 补丁正文、引用说明和来源证据 ID。模型不能自由返回未签发标题文本作为合并依据。
- 目标文章没有可用 H2／H3 时计划以 `PATCH_ANCHOR_MISSING` 失败并提示重新审计为重构／新分支；禁止创建“文末追加”或 document root 兜底锚点。
- 生成成功时后端在冻结文章快照上确定性应用补丁，保存补丁结构、合并后 Markdown 和合并前后差异预览。补丁不能修改目标文章标题、slug、摘要、栏目、标签或首次发布时间。
- 工作副本允许管理员修改锚点、插入位置、补丁 Markdown、引用说明；可选锚点只能来自同一冻结目标发布修订。每次保存重新计算合并预览，锚点失效时拒绝保存而不是追加到末尾。

## 5. 重构草稿

- 重构结构化输出包含完整新 Markdown、可选建议标题和可选建议摘要；正文不能为空。目标 article ID、发布修订、slug、首次发布时间、栏目和标签由后端冻结，不由模型输出或修改。
- 工作副本分别保存正文、建议标题／摘要及 `use_suggested_title`／`use_suggested_summary` 人工选择。默认不采用建议标题和摘要；管理员显式选择后预览才显示建议值。
- 详情提供冻结目标发布修订与当前工作副本的 Markdown／标题／摘要差异。生成或编辑均不修改目标文章工作副本或公开修订。
- 目标文章在生成期间产生新发布修订或被删除时，attempt 与验证结果仍可留痕，但草稿直接进入 stale，不能成为 ready 工作副本。

## 6. 新分支草稿

- 新分支结构化输出包含完整 Markdown、建议标题、建议摘要、可选建议 slug、一个可选栏目 ID 和零个或多个标签 ID。栏目／标签建议只能来自计划冻结的现有候选；未知 ID 使整体结果失败，AI 不得返回“创建新分类”指令。
- 工作副本提供标题、slug、摘要、正文、栏目和标签编辑。生成成功后可以暂时缺少栏目／标签并保持 ready，但界面明确显示发布准备项；下一阶段发布前必须满足一个栏目和至少一个标签。
- 建议 slug 只执行现有格式校验，不在本段自动加后缀、预占或发布。当前已有相同 slug 时显示冲突警告与对应文章，但仍由下一阶段在最终发布事务中决定 `SLUG_CONFLICT`。
- 预览使用现有 Markdown 渲染组件，但不创建普通文章草稿、公开 URL、RSS／站点地图条目或搜索索引记录。

## 7. 自动保存与并发一致性

- `PATCH /api/v1/admin/incubator/drafts/{draft_id}` 接受 `edit_version` 和角色特定工作字段，只允许 ready 草稿。版本不一致返回 `409`；成功增加版本、更新时间并返回规范化工作副本。
- Web 复用现有 `AutosaveQueue` 的延迟、串行 drain、错误／冲突状态和 `flush()` 行为。生成页离开前可以提示未完成保存；保存失败或冲突在本阶段已显示为未来“确认并发布”的阻断状态，但不提供发布按钮。
- 生成任务创建时冻结 `base_edit_version`。响应完成时若草稿仍处于同一 edit version，首次生成可初始化、重生成可显式切换当前激活版本；若期间发生人工编辑，新生成版本仍保存但不得覆盖工作副本或当前激活指针，界面显示“新版本可用”并等待人工选择。
- `POST /api/v1/admin/incubator/drafts/{draft_id}/versions/{version_id}/activate` 要求当前 `edit_version`，把选定历史生成版本复制为新的工作副本并增加 edit version。存在未保存修改时前端先 flush；切换会覆盖当前工作副本时必须二次确认。
- 后台任务、重复响应和页面轮询不能静默覆盖人工修改。所有服务端写入在事务内核对草稿状态、base edit version、当前审计和目标文章版本。

## 8. 重生成与版本比较

- `POST /api/v1/admin/incubator/drafts/{draft_id}/regeneration-plans` 要求 1–2000 字反馈，冻结当前工作副本、当前激活生成版本、原审计结论／证据、资料修订和角色特定目标，返回 `202` 与本地计划任务。缺少反馈不执行规划或调用。
- 重生成和首次生成使用相同两阶段外发确认、上下文预检、结构 Schema、重试、取消和 Token 规则。提示包含上一版当前工作副本与反馈，不继承供应商对话。
- 同一浏览器工作会话已经对该草稿、服务标识和 generation model 完成外发确认时，前端可以不重复弹窗，但后端每次仍要求 `external_transfer_confirmed = true`。会话确认只保存在浏览器 session scope，不进入数据库或跨登录复用；服务／模型变化必须重新提示。
- `GET /api/v1/admin/incubator/drafts/{draft_id}/versions` 返回有界版本历史；`GET /drafts/{draft_id}/diff?from_version_id=&to_version_id=` 返回角色适配差异。默认展示最新版生成版本与当前工作副本差异，管理员可查看并激活任一历史生成版本。
- 每个重生成结果创建新版本而不覆盖旧版本。失败／取消版本保留 attempt／Token 与安全错误，但不进入可激活版本列表。

## 9. 草稿失效、丢弃与只读历史

- 资料当前修订、审计有效决定／状态或有效角色变化时草稿立即 stale。增补／重构的目标文章产生新发布修订、被删除或标题锚点集合不匹配时草稿立即 stale；其他参考文章变化只显示警告。
- 生成结果完成时必须再次核对计划、资料、审计、目标文章和分类候选。调用期间发生变化时仍保存 attempt、Token 和经验证生成版本，但草稿直接 stale，绝不能短暂进入 ready。
- stale 草稿只能查看历史、差异、Token、丢弃或返回审计报告重新判定；不能编辑、激活版本或重生成。下一阶段也不得发布 stale 草稿。
- `POST /api/v1/admin/incubator/drafts/{draft_id}/discard` 逻辑归档草稿并记录操作者、原因和时间。已丢弃草稿不出现在默认池中，但可筛选、查看历史和 Token；本段不提供永久删除或恢复。
- 已进入草稿来源链的资料、审计版本、生成版本、attempt 和 Token 不能永久删除。原始审计报告与 AI 原判不因草稿编辑或丢弃而改变。

## 10. 管理 API 与草稿池界面

- `GET /api/v1/admin/incubator/drafts` 支持角色、状态、来源类型、目标文章、来自冲突、时间和关键词筛选，使用默认 20、最多 100、offset 最大 100000，并按 `updated_at DESC, id DESC` 稳定排序。
- `GET /api/v1/admin/incubator/drafts/{draft_id}` 返回工作副本、edit version、当前／历史生成版本摘要、来源资料与审计、角色、目标发布修订、stale／冲突原因、生成 attempt 和 Token；不返回 API Key、完整 system prompt 或未验证响应。
- `GET /api/v1/admin/incubator/drafts/{draft_id}/preview` 返回角色特定预览：增补为合并前后与结构化 diff，重构为目标版本对比，新分支为独立文章预览与发布准备项。
- `/admin/incubator/drafts` 是可筛选草稿池；`/admin/incubator/drafts/{id}` 是稳定编辑／预览 URL，支持浏览器前进、后退和复制链接。管理导航启用草稿池入口。
- 已确认审计详情提供“生成孵化草稿”；已有草稿时链接现有草稿而不是重复创建。报告未确认、stale、degraded 或 conflict_pending 时不显示可用生成操作。
- 草稿详情复用 Markdown 编辑／预览、自动保存状态和可访问表单模式；角色、stale、保存冲突、生成进度与版本切换不能只靠颜色表达。发布入口明确留空至下一阶段。
- `/admin/incubator` 增加 queued／generating／ready／stale／failed 草稿数量和 generation model 状态；Token 汇总纳入 initial generation／regeneration。
- 所有新 API 位于 `/api/v1/admin/incubator`，读取要求 Session，写入要求 Session＋CSRF。OpenAPI 同步 `packages/contracts/openapi.json` 与 Web 类型，稳定错误码由前端映射中文说明。

## 11. 错误、安全与工程验收

- 本段至少落实 `LLM_NOT_CONFIGURED`、`LLM_AUTH_FAILED`、`LLM_MODEL_NOT_FOUND`、`LLM_UNAVAILABLE`、`LLM_OUTCOME_UNKNOWN`、`SOURCE_TOO_LONG`、`DRAFT_RESULT_INVALID`、`DRAFT_STALE`、`ARTICLE_VERSION_CONFLICT`、`PATCH_ANCHOR_MISSING` 和 `SLUG_CONFLICT` 警告语义。
- Pytest 覆盖三种角色 Schema、锚点签发／应用、禁止文末兜底、分类 ID 越权、两阶段同意、上下文拒绝、attempt／Token、重试与未知结果、幂等创建、edit version 冲突、生成期间人工编辑、历史激活、失效和丢弃。
- LLM 自动化测试只使用本地确定性 OpenAI-compatible double，覆盖成功、401／404／429／5xx、超时、无效 JSON、越权 ID 和超限输出；没有真实 API Key 或供应商时，真实连接状态保持未配置，不伪造成功。
- Vitest 覆盖角色表单、自动保存、版本切换确认、外发同意 session、差异视图、发布准备项、状态／错误映射；Playwright 覆盖“确认审计 → 生成计划 → 外发确认 → 三类草稿之一 → 自动保存 → 反馈重生成 → 比较／激活版本”的代表性闭环。
- API 全量测试、Ruff、OpenAPI 契约、Web Vitest、类型检查、生产构建、既有 E2E、WCAG 与 Lighthouse 门槛继续通过；真实内容、API Key、模型二进制、重日志和截图不进入 Git。

# Risks

- **后台生成覆盖人工编辑**：任务冻结 base edit version；返回时只创建不可变版本，只有版本未变化才允许切换工作副本，否则必须人工激活。
- **增补定位漂移**：模型只能选择后端签发的发布修订锚点；没有 H2／H3 或锚点变化即失败／stale，绝不回退为正文末尾追加。
- **越权分类或文章变更**：结构输出中的 article、revision、anchor、category 和 tag ID 全部与计划白名单核对，发布修订变化使结果 stale。
- **重复外发与计费**：首次生成和重生成均有不可变计划、显式确认、attempt 账本和未知结果人工恢复；浏览器 session 只减少重复弹窗，不绕过后端确认字段。
- **角色结构混淆**：三种角色使用判别联合 Schema 和独立后端验证／预览；不能把重构正文解释为增补补丁或把新分支写入目标文章。
- **未发布内容泄漏**：草稿表与普通文章／公开 API／公共搜索完全隔离，所有生成和预览只在受保护管理路由中出现。
- **范围膨胀**：本段只产出 ready 工作副本；最终一致性校验、来源链、文章版本、回滚和批量发布留给下一 active spec。

# Verification plan

1. **TDD**：先为角色判别 Schema、锚点、补丁应用、分类白名单、状态机、edit version、生成竞态、失效和错误映射建立失败测试，再实现最小行为。
2. **Contract**：用临时 SQLite 从当前 Alembic head 升级、降级再升级，验证草稿、版本、attempt 和扩展 job owner 约束；生成 OpenAPI，断言 plan、confirm、draft CRUD、preview、versions、diff、regeneration 和稳定错误码与 Web 类型一致。
3. **Integration**：以真实 SQLite、现有审计／文章快照和本地 LLM double 验证三种结构输出、两阶段外发、Token、重试／取消／未知结果、任务重放、人工编辑竞态、锚点失效和审计／文章发布钩子。
4. **Security**：注入来源指令、伪造 anchor／article／revision／taxonomy ID、超长 Markdown、API Key 回显和恶意错误；证明越权结果失败，日志／数据库错误／OpenAPI／快照无 Key、完整提示和未验证响应。
5. **E2E**：现有隔离包装进程启动 API、Web、Worker、检索替身与 LLM double，覆盖生成计划、外发确认、角色编辑、自动保存、反馈重生成、版本差异／激活和 stale；不访问公网、开发数据库或真实供应商。
6. **Quality**：从 `apps/api/` 执行 Pytest 全量与 Ruff；从 `apps/web/` 执行 Vitest、类型检查、生产构建、既有 E2E 和适用 axe／Lighthouse，确认公开页面与发现输出无回退。
7. **Harness**：更新相关 L1 边界元数据后，从 `harness/` 运行 `python -m tools.harness index`；实现和全部门槛通过后写入紧凑 evidence，并运行 `python -m tools.harness verify 20260804-incubator-drafts`。关闭前确保本 active spec 已存在于 Git 历史，最终只能用 `python -m tools.harness close 20260804-incubator-drafts` 压缩归档。

