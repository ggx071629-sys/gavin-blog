---
id: archive-20260804-incubator-llm-audit
level: L2
summary: 建立显式外发确认、结构化证据校验、人工裁决与 Token 留痕的 LLM 审计闭环
load_when:
  - task:20260804-incubator-llm-audit
author: Gavin
task_id: 20260804-incubator-llm-audit
status: compressed
restoration_source: "22df98e9c87025620eceb53b1d2afda7064167a0:harness/specs/active/20260804-incubator-llm-audit.md"
restored_at: 2026-08-11
---

# 20260804-incubator-llm-audit

Deterministic compressed record. The original active spec remains in Git history.

## Goal

管理员可以从待处理池选择最多 50 条资料，先异步完成本地检索、外发内容快照和 Token 估算，再明确确认第三方外发。Worker 对每条资料执行一次独立、无状态、版本化且严格结构化的 LLM 审计，生成带稳定证据、角色、目标文章版本、置信度、风险和模型元数据的可审阅报告。管理员可以逐条改判、裁决冲突、确认、丢弃或带反馈重新判定，并可在安全范围内批量确认高置信增补／新分支。资料或目标文章变化会立即使旧报告失效；所有调用尝试和实际／估算 Token 均进入只观察、不阻断消费的账本。

## Acceptance criteria

## 1. 第三方 LLM 配置与健康

- 使用环境变量配置 `GAVIN_LLM_BASE_URL`、`GAVIN_LLM_API_KEY`、`GAVIN_LLM_AUDIT_MODEL`、`GAVIN_LLM_GENERATION_MODEL`、`GAVIN_LLM_CONTEXT_WINDOW`、`GAVIN_LLM_AUDIT_MAX_OUTPUT_TOKENS`、`GAVIN_LLM_TIMEOUT_SECONDS`、`GAVIN_LLM_STRUCTURED_OUTPUT_MODE` 和可选 tokenizer 标识。审计只使用 audit model；generation model 本段只显示配置状态。
- `base_url` 必须是无 userinfo、无 query／fragment 的绝对 HTTP(S) 地址；生产环境只允许 HTTPS，development／test 可使用 HTTP 本地替身。调用路径固定为相对 `chat/completions`，认证使用 `Authorization: Bearer`，不把供应商部署拓扑写死到业务代码。
- `structured_output_mode` 只允许 `json_schema` 或 `json_object`。`json_schema` 使用供应商原生严格 Schema；`json_object` 仍必须经过完全相同的后端 Pydantic／业务引用校验。实现不以静默重试方式猜测供应商能力。
- API Key 只存在于进程配置，禁止写入数据库、响应、日志、异常文本、任务 payload 或测试快照。健康响应只显示已配置／未配置、经过净化的服务地址标识和模型名称。
- `GET /api/v1/admin/incubator/llm/health` 只检查本地配置，不访问第三方，区分 `not_configured`、`configured` 和最近一次连接测试结果。配置缺失时规划可显示本地估算，但确认审计返回 `LLM_NOT_CONFIGURED`，不创建付费任务。
- `POST /api/v1/admin/incubator/llm/tests` 创建异步最小连接测试并返回 `202`；测试只发送固定的无用户内容提示和最小输出，结果通过任务轮询查看。它区分 `LLM_AUTH_FAILED`、`LLM_MODEL_NOT_FOUND`、`LLM_UNAVAILABLE` 和成功，并像其他第三方调用一样记录 Token 元数据。

## 2. 两阶段审计计划与外发同意

- `POST /api/v1/admin/incubator/audit-plans` 接受 1–50 个唯一 `source_id` 和 `mode = full|fts_only`，要求管理员 Session＋CSRF，返回 `202`、计划 ID 和逐条本地规划任务。只有当前状态为 `inbox`、存在当前资料修订且未丢弃的资料可进入计划；同一资料修订的未完成计划通过幂等键复用。
- API 请求不执行本地模型或第三方调用。Worker 为每个计划项读取冻结的资料修订，重新运行当前检索，保存检索候选快照、外发文章修订／片段快照、资料证据片段、提示词版本、检索 pipeline／manifest、上下文估算和计划状态。
- `GET /api/v1/admin/incubator/audit-plans/{plan_id}` 返回逐项规划进度、将外发的资料标题、资料数量、候选旧文数量、估算输入／输出／总 Token、估算精度、完整／降级模式和失败原因；不把全部正文放进批次摘要响应。
- 资料正文按确定性 Markdown 块切成带稳定计划内 ID 的证据片段，审计提示仍包含该资料完整标准化正文。旧文只包含最多 8 篇当前发布修订的标题、摘要和每篇最相关 1–3 个检索片段，不发送旧文全文。
- `full` 计划要求本地模型和全量文章索引 ready，否则以 `LOCAL_MODEL_NOT_READY`／`ARTICLE_INDEX_STALE` 失败；`fts_only` 必须由管理员显式选择，计划与后续报告永久标记 `degraded = true`。
- 计划是不可变外发快照。当前资料修订、任一主要候选文章发布修订、检索 pipeline／manifest 或提示词版本变化时，计划变为 stale，不能确认，必须重新规划。
- `POST /api/v1/admin/incubator/audit-plans/{plan_id}/confirm` 必须携带 `external_transfer_confirmed = true`。前端确认弹窗明确说明“新资料全文和相关旧文摘要／片段将发送给第三方”，列出资料数量、服务标识、模型、估算 Token 和降级状态；未确认时不创建审计版本或付费任务。
- 确认使用部分成功：每个仍有效的计划项独立创建一个审计版本和一个 `llm_audit` 任务，stale／非法项返回逐项错误且不影响其他合法项。每条资料始终独立调用，不合并请求。

## 3. 上下文预检与 Token 估算

- 提示构造器有显式 `audit-v1` 版本并准确计入系统提示、结构 Schema、新资料全文、候选旧文、反馈、输出预留和供应商消息包装。配置 tokenizer 可识别时使用对应 tokenizer；不能识别时使用保守通用近似并标记 `low` 精度，绝不把近似值伪装为实际值。
- 上下文窗口和最大输出 Token 必须为正且最大输出小于上下文窗口。预检为输出和结构留足配置空间；任何计划项预计超过单次上下文时以 `SOURCE_TOO_LONG` 失败，不截断资料、不调用 LLM，并提示管理员拆分或精简。
- 重新判定把当前资料修订、最新检索、上一版结构化报告和必填反馈纳入同一次新请求；每次调用独立无状态，不发送供应商会话 ID或继承历史对话。
- 计划页展示的是估算值；供应商返回 `usage` 时账本保存实际 input／output／total 并标记 `actual`。未返回 usage 时使用配置 tokenizer 估算并标记 `model_estimate`，未知 tokenizer 使用通用近似并标记 `low_precision_estimate`。
- 不设置日、周、任务或金额配额，Token 数量不会自动拒绝合法调用。工作台的日／周／任务类型汇总只用于观察。

## 4. 调用、重试、取消与不确定结果

- 使用有边界的 HTTP 客户端调用 OpenAI-compatible `chat/completions`，不在 FastAPI 请求中执行第三方调用。每次实际 HTTP 尝试在发送前先持久化 attempt、请求指纹、尝试号和 `sending` 状态，响应后再保存 HTTP／供应商结果元数据。
- 网络超时、HTTP `429` 和 `5xx` 最多自动重试 2 次，总尝试不超过 3 次，退避固定为 1 秒和 4 秒；每次尝试单独记录并通过 `retry_of_attempt_id` 关联。`401/403`、模型不存在、请求格式错误和结构业务错误不做传输层自动重试。
- Worker 在调用前与响应后检查取消。请求已经发出时取消不保证停止计费；对应 attempt 与 Token 仍保留，取消只阻止报告进入可审阅状态。排队任务立即取消。
- Worker 在请求发出后、结果持久化前崩溃属于不确定结果。租约恢复不得静默重发该 attempt；任务以稳定 `LLM_OUTCOME_UNKNOWN` 失败，管理员明确人工重试后才创建新的审计版本，避免隐藏的重复计费。
- 同一审计版本只有一个逻辑成功结果；自动重试、租约恢复或重复确认不能创建第二份报告。日志只包含 task／audit／attempt ID、耗时、HTTP 类别、错误码、Token 数和模型，不记录正文、完整提示或供应商原始响应。

## 5. 提示注入防护与结构化结果

- 系统提示明确声明资料正文、旧文片段及其中任何指令均是不可信数据，只能作为待分析内容。提示使用后端生成的稳定 ID 和明确数据边界，用户内容不能进入 system role、工具定义或 Schema。
- 结构化响应严格包含：唯一主角色、`0..1` 置信分数、判定理由、主要目标文章 ID、其他相关文章 ID、预计产出类型与范围、关键判断、风险、不确定性、是否建议拆分及原因。
- 主角色枚举固定为 `supplement`（增补）、`rewrite`（重构）、`conflict`（冲突待裁决）和 `new_branch`（新分支）。增补／重构／冲突必须且只能引用一篇本次候选中的当前文章发布修订；新分支必须没有主要目标。其他相关文章也只能来自本次候选。
- 每个关键判断至少引用一个本次资料证据片段 ID；增补、重构和冲突还至少引用一个主要目标文章片段 ID。后端验证每个 ID 的类型、所属计划、文章与修订、文本快照和字段长度；不存在、跨计划、跨文章、越权目标或证据不足使整个结果以 `AUDIT_RESULT_INVALID` 失败，不能进入人工审阅。
- 供应商原始响应只在内存中解析；数据库保存已验证的结构字段、响应 SHA-256、验证错误摘要和必要证据快照，不保存未验证的完整自由文本响应。
- 判定理由、产出范围、风险、不确定性和反馈均有明确长度与数量上限；超限不是静默截断，而是结构校验失败。实现采用共享 Schema，使原生 JSON Schema 与 fallback JSON 校验完全一致。

## 6. 报告、版本、证据和状态

- Alembic 增加职责分离的审计计划／计划项、审计报告版本、调用尝试、检索候选快照、资料证据片段、报告关键判断／证据、人工决定和 Token 账本实体。表名可按现有惯例调整，但不可变快照与当前可变状态必须分离。
- 审计报告状态至少覆盖 `queued`、`judging`、`review`、`conflict_pending`、`confirmed`、`discarded`、`stale`、`failed`、`cancelled`。角色为 conflict 的有效结果进入 `conflict_pending`，其他角色进入 `review`；失败和取消不能跳过状态机。
- 资料增加显式当前有效审计报告指针。确认计划项创建任务时资料进入 `auditing`；首次审计成功后切换当前指针并进入 `audited`，首次失败／取消后返回 `inbox`。重新判定只有在新报告完整验证成功后才原子替换当前指针；新版本失败／取消时保留上一份有效报告与资料原状态。
- 报告保存资料 ID／修订号、审计版本号、前一审计版本、AI 原始角色与目标、当前有效角色与目标、置信分数／等级、完整／降级标记、目标文章发布修订、其他候选修订、证据文本快照、检索模型／manifest／pipeline、候选数量、提示词版本、第三方服务标识／模型及 attempt／Token 关联。
- 置信等级固定为：`high >= 0.95`、`medium >= 0.70 and < 0.95`、`low < 0.70`；高置信门槛由后端配置，默认 `0.95`，健康与前端显示实际值。
- 确认只把报告标记为可供下一阶段生成草稿，不在本段创建草稿或调用 generation model。一个资料可以保留多个不可变审计版本，但只有最新未失效版本可执行人工动作。
- 当前资料修订被编辑后，绑定旧修订的最新报告立即变为 stale，资料返回待处理；增补／重构／冲突的主要目标文章产生新发布修订或被删除后报告立即 stale。其他参考文章变化只显示警告，不自动失效。
- LLM 响应完成时必须在保存可审阅状态前重新核对资料修订、计划快照和目标文章发布修订；调用期间发生变化时仍保存 attempt、Token、结构结果与证据，但报告直接进入 stale，绝不能短暂进入 review／conflict_pending。
- 资料详情允许管理员在 `audited` 状态继续人工修订；成功保存新资料修订会清除当前有效报告指针、把所有绑定旧修订的可操作报告标为 stale，并把资料送回 `inbox`。`auditing` 状态禁止编辑，避免调用中的正文与冻结计划不一致。
- 报告证据保留片段文本快照，即使可再生成的旧索引片段被清理，历史报告仍可完整回看。已进入报告来源链的资料不能永久删除。

## 7. 人工改判、冲突裁决和确认

- `PATCH /api/v1/admin/incubator/audits/{audit_id}/decision` 允许管理员修改当前角色和主要目标文章并填写可选备注。改为新分支必须清空目标；改为其他角色必须选择一篇当前已发布且未删除文章并绑定其当前发布修订。AI 原判永不覆盖，人工决定记录操作者、时间、前后值和备注。
- 人工选择检索候选以外的目标文章是允许的，但后端必须读取并冻结该文章当前发布修订，标记 `human_selected_outside_candidates = true`；后续草稿阶段仍需以人工目标为准。
- `POST /api/v1/admin/incubator/audits/{audit_id}/resolve-conflict` 只接受 `supplement`、`rewrite`、`new_branch`、`discard_source` 或 `defer`。前三者保存裁决并进入 review；`discard_source` 同时逻辑丢弃资料和报告；`defer` 保持阻断状态。冲突未经裁决不能确认。
- `POST /api/v1/admin/incubator/audits/{audit_id}/confirm` 逐条确认有效报告。重构、冲突原判或冲突改判报告始终只能逐条确认；stale、failed、cancelled、degraded 或证据无效报告不能确认。
- `POST /api/v1/admin/incubator/audits/confirm-batch` 使用逐项结果确认：只允许非降级、当前有效、`confidence >= 0.95`、`requires_split = false` 的增补或新分支。非法项保持原状态并返回稳定原因，合法项只确认一次。
- 丢弃支持逐条与批量操作；普通丢弃只归档报告，不永久删除证据或 Token。重新判定始终逐条执行，不能批量。

## 8. 重新判定与失效

- `POST /api/v1/admin/incubator/audits/{audit_id}/rerun-plan` 要求 1–2000 字反馈并创建新的本地计划项，不覆盖旧报告。缺少反馈返回验证错误且不执行检索或付费调用。
- 重新规划始终使用当前资料修订、最新检索结果和当前文章发布修订；旧候选不能复用。计划摘要显示旧报告版本、反馈、最新外发清单和新增估算 Token，管理员再次确认外发后才创建新 `llm_audit` 任务。
- 新提示包含上一版已验证结构化报告与反馈，不包含供应商历史对话。新审计保存独立版本和 `previous_audit_id`；旧报告继续可查看，不被覆盖或删除。
- stale 报告只能查看、丢弃或发起重新判定，不能改判、裁决、确认或进入下一阶段。失效原因明确区分 `source_revision_changed`、`target_revision_changed`、`target_deleted` 和其他参考变化警告。

## 9. 管理 API、报告池和 Token 观察

- `GET /api/v1/admin/incubator/audits` 支持来源类型、报告状态、角色、置信等级、完整／降级、时间和关键词筛选，以及默认 20、最多 100、offset 最大 100000 的稳定分页；排序为 `updated_at DESC, id DESC`。
- `GET /api/v1/admin/incubator/audits/{audit_id}` 返回报告版本链、AI 原判、人工决定、目标与相关文章版本、关键判断、证据快照、风险、不确定性、检索／提示／模型元数据、Token 与调用尝试，但不返回 API Key、完整系统提示或未验证供应商响应。
- `GET /api/v1/admin/incubator/tokens` 提供有界明细；`GET /api/v1/admin/incubator/tokens/summary` 支持日、周和任务类型汇总，区分 actual、model estimate 和 low-precision estimate。连接测试、初次审计、自动重试和重新判定均有明确 task type／attempt 关系。
- `/admin/incubator/inbox` 增加批量选择与“准备审计”；计划进度完成后显示外发确认弹窗。`/admin/incubator/audits` 是可筛选报告池，`/admin/incubator/audits/{id}` 是稳定详情 URL，支持浏览器前进、后退和复制链接。
- 报告详情明确展示原文／旧文证据、文章发布修订、AI 原判与人工有效判定、降级、stale、Token 和重试；角色、置信、风险不能只靠颜色表达。冲突页在裁决前隐藏确认入口。
- `/admin/incubator` 增加第三方 LLM 配置／最近连接测试、审计队列和 Token 日／周摘要。所有新读取要求 Session，所有 POST／PATCH／DELETE 要求 Session＋CSRF。
- OpenAPI 是跨端契约来源，同步生成 `packages/contracts/openapi.json` 与 Web 类型；前端只按稳定错误码映射中文信息，不解析供应商自由文本。

## 10. 错误、安全与工程验收

- 本段至少落实 `SOURCE_TOO_LONG`、`LLM_NOT_CONFIGURED`、`LLM_AUTH_FAILED`、`LLM_MODEL_NOT_FOUND`、`LLM_UNAVAILABLE`、`LLM_OUTCOME_UNKNOWN`、`LOCAL_MODEL_NOT_READY`、`ARTICLE_INDEX_STALE`、`AUDIT_RESULT_INVALID` 和 `AUDIT_STALE`。
- Pytest 覆盖配置净化、API Key 不落盘、两阶段确认、计划失效、批次部分成功、上下文拒绝、调用重试分类、不确定结果、取消后计费留痕、结构 Schema、提示注入、越权 ID、证据硬门槛、角色／目标约束、人工改判、冲突裁决、批量资格、重审版本和 Token 汇总。
- 第三方和本地模型测试全部使用确定性同契约替身；默认测试套件禁止公网访问，并断言日志、数据库错误字段、OpenAPI 与快照中不存在测试 API Key 和完整提示正文。
- Vitest 覆盖计划／确认状态、外发提示、报告筛选、置信与批量资格、冲突阻断、stale、Token 精度和错误映射；Playwright 覆盖“待处理资料 → 本地计划 → 外发确认 → 独立报告 → 人工改判／冲突裁决 → 确认／重审”的代表性闭环。
- API 全量测试、Ruff、OpenAPI 契约、Web Vitest、类型检查、生产构建、既有 E2E、WCAG 与 Lighthouse 门槛继续通过；模型二进制、真实内容、重日志和截图不进入 Git。

## Result

Verified and closed by the harness close command.

## Evidence

[20260804-incubator-llm-audit.json](../../verification/evidence/20260804-incubator-llm-audit.json)

Closed at 2026-08-04T10:35:11.422800+00:00.
