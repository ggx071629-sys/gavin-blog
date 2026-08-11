---
id: archive-20260803-incubator-ingestion
level: L2
summary: 建立文件与一次性网页资料的安全摄入、异步清洗、精确去重和待处理池闭环
load_when:
  - task:20260803-incubator-ingestion
author: Gavin
task_id: 20260803-incubator-ingestion
status: compressed
restoration_source: "f16fedf9fa581da2781055aae9a89ef216c41b81:harness/specs/active/20260803-incubator-ingestion.md"
restored_at: 2026-08-11
---

# 20260803-incubator-ingestion

Deterministic compressed record. The original active spec remains in Git history.

## Goal

管理员可以在知识孵化入口一次提交最多 50 个 Markdown／TXT 文件和公网 URL。API 快速持久化摄入意图，独立 Worker 安全抓取或清洗每一项；系统保留原始层与不可变标准化修订，以稳定正文指纹精确去重，并把成功资料放入可筛选、可修订、可丢弃、可恢复和可重试的待处理池。批次内单项失败不回滚其他项，刷新页面或重启服务后任务仍可观察并安全恢复。

## Acceptance criteria

## 1. 数据、迁移与状态

- Alembic 新增职责分离的摄入批次、摄入事件、资料、原始载荷、资料修订和任务实体。表名可按现有 SQLAlchemy 命名惯例调整，但一条提交项必须对应一条摄入事件；精确重复事件只关联首次规范资料，不创建第二条可审计资料。
- 资料状态至少覆盖 `queued`、`processing`、`inbox`、`duplicate`、`failed`、`discarded`；任务状态至少覆盖 `queued`、`running`、`succeeded`、`failed`、`cancelled`。状态转换由后端集中校验，取消、失败、恢复和重试不能跳过前置状态。
- 原始文件字节或抓取到的原始 HTML 以带压缩格式版本、MIME、原始编码、抓取时间和 SHA-256 校验值的压缩 BLOB 保存；标准化标题和 Markdown 保存在不可变资料修订中。当前修订由资料显式指向，历史修订不被覆盖。
- 所有瞬时时间遵守既有 UTC 语义。数据库约束、唯一键和事务保证任务幂等键唯一、修订号对单资料单调递增、正文指纹在所有未永久删除的规范资料中唯一；逻辑丢弃不会释放指纹。
- 迁移只建立空结构，不抓取 URL、不清洗正文、不启动 Worker，并能从当前最新迁移升级和完整降级；现有博客数据不变。

## 2. 批量摄入契约

- 所有端点位于 `/api/v1/admin/incubator`，所有读取要求管理员 Session，所有写入同时要求 CSRF。OpenAPI 是唯一跨端契约来源，并同步生成到 `packages/contracts/openapi.json` 和 Web 类型。
- `POST /api/v1/admin/incubator/batches` 接受 `multipart/form-data` 中重复的 `files` 与 `urls` 字段。至少提交一项；文件和 URL 合计超过 50，或上传文件实际读取总量超过 10 MiB 时，整次请求不创建任何记录并返回稳定错误码 `BATCH_LIMIT_EXCEEDED`。成功接收返回 `202`、批次 ID、逐项事件 ID 与初始状态。
- 单文件超过 2 MiB、扩展名不属于 `.md`／`.markdown`／`.txt`、URL 格式不受支持等单项可归因错误，保存为该事件的失败结果并使用 `SOURCE_TOO_LARGE`、`UNSUPPORTED_SOURCE_TYPE` 或对应稳定错误码；同批其他合法项仍排队处理。
- `GET /api/v1/admin/incubator/batches/{batch_id}` 返回批次汇总和逐项状态、错误码、可理解消息及规范资料关联；轮询同一批次不会改变状态。
- `GET /api/v1/admin/incubator/sources` 支持 `status`、`source_type`、`q`、`created_from`、`created_to`、`limit`（默认 20，1–100）和 `offset`（默认 0，0–100000），在数据库层按 `created_at DESC, id DESC` 稳定分页。默认不返回 `discarded`，显式状态筛选可以查看。
- `GET /api/v1/admin/incubator/sources/{source_id}` 返回来源元数据、当前状态、当前及历史修订摘要、关联摄入事件、任务和错误，但不在列表响应中携带大 BLOB。详情可按需读取原始内容的纯文本安全预览与当前标准化 Markdown；响应不得把原始 HTML 标记为可直接渲染内容。
- `PATCH /api/v1/admin/incubator/sources/{source_id}` 接受 `base_revision`、标准化标题和 Markdown，只允许修改 `inbox` 资料。版本不匹配返回 `409`；成功创建新修订，重新计算指纹和 Token 近似估算。若正文与其他规范资料精确重复，则以 `SOURCE_DUPLICATE` 拒绝本次修订且不改变当前修订。
- `POST /sources/{source_id}/discard`、`POST /sources/{source_id}/restore`、`POST /sources/{source_id}/retry` 和 `DELETE /sources/{source_id}` 分别执行逻辑丢弃、恢复、失败项人工重试和逐条永久删除。重复操作必须幂等或返回稳定的状态冲突；永久删除只接受已丢弃资料，前端二次确认，后端在存在不可删除来源关联时返回 `409`。
- `GET /jobs/{job_id}` 和 `POST /jobs/{job_id}/cancel` 提供本段任务观察与取消。排队任务立即取消；运行任务记录取消请求并在抓取流、清洗阶段边界等安全点停止。已结束任务再次取消不改变结果。

## 3. 文件清洗与标准化

- 文件只接受 `.md`、`.markdown` 和 `.txt`。先尝试 UTF-8／UTF-8 BOM，再尝试 GB18030；两者均失败时以 `SOURCE_DECODE_FAILED` 结束该项，不继续猜测编码。标准化 Markdown 统一为 UTF-8 文本并记录检测到的原始编码。
- Markdown 仅解析 `title`、`author`、`source_url`、`published_at`、`tags`。Frontmatter 上限复用现有 64 KiB 导入边界；YAML 使用安全加载，只允许标量字段及一维字符串 `tags`，禁止对象构造、anchor／alias、复杂嵌套。未知字段仅留在原始载荷，不进入标准化正文或业务字段，来源标签不创建博客栏目或标签。
- 标题严格遵循总设计顺序：Markdown 使用 Frontmatter `title`、首个 H1、文件名；TXT 仅在第一行去除空白后长度为 1–180 个 Unicode 字符时将其视为短标题，否则使用文件名。所有标准化标题最终校验为 1–180 个字符；标准化正文移除有限 Frontmatter，执行确定性的换行、空白和 Markdown 规范化，并拒绝空正文或明显乱码为 `SOURCE_EMPTY` 或 `SOURCE_DECODE_FAILED`。
- 清洗器具有显式版本。相同清洗器版本与相同原始输入必须产生相同标题、正文和 SHA-256 正文指纹；重试不得创建重复资料、修订或任务结果。

## 4. 一次性 URL 抓取安全

- 只接受无凭据的公网 `http`／`https` URL，fragment 在抓取前丢弃；拒绝 localhost，以及 URL 中的 IP 或 DNS 解析结果属于环回、私网、链路本地、保留、多播和未指定地址的目标，公网 IP 字面量仍按相同地址规则校验。每次跳转前重新解析并验证 URL 与全部 DNS 结果，实际连接不得绕过已验证地址，测试证明 DNS rebinding 不能把请求转向被禁止地址。
- 抓取不携带管理员 Cookie、浏览器登录态、API 凭据或调用方自定义 Header，不执行 JavaScript，不绕过访问控制。最多跟随 5 次重定向；连接超时 5 秒、读取超时 15 秒、单项总时限 30 秒，超时或非成功 HTTP 结果使用 `URL_FETCH_FAILED`。
- 响应按流读取；声明或实际读取的解压后响应体超过 5 MiB 立即停止并使用 `SOURCE_TOO_LARGE`。正文提取结果超过 2 MiB、为空或明显依赖 JavaScript 时明确失败，不截断后继续。
- URL 标题严格使用 Open Graph／`<title>`、首个 H1、域名与路径的顺序。正文提取移除脚本、样式、导航、广告和明显页面噪声并输出标准化 Markdown；原始 HTML 只能以纯文本转义或经过严格净化的预览呈现，不能通过 `v-html` 或等价未净化路径注入管理页面。
- 同一 URL 再次提交始终创建新的摄入事件并重新抓取；是否重复只由标准化正文指纹决定。不同文件名或 URL 产生同一指纹时，事件标记 `duplicate`、关联首次资料并返回 `SOURCE_DUPLICATE`，不创建第二条待审计资料，也不排队任何后续付费工作。

## 5. 持久 Worker 与故障恢复

- 提供独立的 Python Worker 启动入口；FastAPI 请求只验证批次边界、持久化上传原始字节或 URL 意图并创建任务，不在请求内抓取网页或执行正文清洗。
- Worker 使用 SQLite 任务表串行原子领取任务，保存类型、进度、尝试次数、租约到期时间、最后错误和幂等键。同一数据库上即使误启多个 Worker，同一租约期内也只有一个 Worker 能拥有任务。
- Worker 崩溃或进程重启后，过期租约任务可被重新领取；已持久化的步骤结果被复用，重放不会增加第二条资料、修订或完成记录。本段不引入独立调度服务，也不把进程常驻方式写死为特定部署平台。
- 抓取、解码、清洗、去重和持久化失败映射到稳定错误码，保存可安全展示的简短原因与内部任务 ID；日志不得记录原始正文、完整 HTML、Session／CSRF 值或其他秘密。

## 6. 管理端纵向闭环

- 管理导航新增“知识孵化”。`/admin/incubator` 提供文件／URL 混合摄入入口、限制说明、最近批次汇总、待处理／处理中／失败／重复／已丢弃数量和 Worker 健康状态；本段不展示模型、审计或生成操作。
- `/admin/incubator/inbox` 提供来源、类型、状态、时间和关键词筛选，使用与 API 一致的有界分页与稳定 URL 查询参数；刷新、前进、后退和复制链接保持当前视图。
- `/admin/incubator/inbox/{source_id}` 是稳定详情 URL，提供原始内容与标准化 Markdown 的安全对照预览、来源与修订历史、标题／正文编辑、丢弃、恢复和失败重试。所有状态和错误显示可理解中文，不以颜色作为唯一提示。
- 混合批次明确显示部分成功：每项可以独立到达待处理、重复或失败，失败项可单独重试。上传提交后关闭页面、刷新或重新登录不会丢失批次和任务进度。
- Vitest 覆盖批次限制、状态／错误映射、筛选 URL 和修订冲突交互；Playwright 使用确定性本地 HTTP 抓取替身覆盖“登录 → 混合提交 → 部分成功 → 查看对照 → 修订 → 丢弃／恢复”的代表性闭环，不访问公网。

## 7. 错误、安全与契约完整性

- 本段至少落实 `UNSUPPORTED_SOURCE_TYPE`、`SOURCE_TOO_LARGE`、`BATCH_LIMIT_EXCEEDED`、`SOURCE_DECODE_FAILED`、`URL_FETCH_FAILED`、`URL_BLOCKED`、`SOURCE_EMPTY` 和 `SOURCE_DUPLICATE`。同步 API 错误载荷与单项失败字段，Web 不通过解析自由文本判断错误类型。
- Pytest 覆盖未登录读取、缺少 CSRF 的写入、越权详情、文件名注入、压缩／响应体超限、恶意 YAML、恶意 HTML、SSRF、每跳重定向、DNS 变化、超时、精确重复、并发任务领取、租约恢复、取消、幂等重试和 SQLite 事务回滚。
- 原始资料不会进入公开 API、搜索、RSS、站点地图或页面；robots 继续禁止 `/admin/`。数据库、日志、OpenAPI 示例和测试快照均不包含真实摄入正文。
- API 全量测试、Ruff、OpenAPI 生成与契约断言、Web Vitest、类型检查、生产构建和既有 E2E 均通过；本段新增页面满足现有 WCAG A／AA 自动扫描零违规，既有公开页面 Lighthouse 阻断门槛不回退。

## Result

Verified and closed by the harness close command.

## Evidence

[20260803-incubator-ingestion.json](../../verification/evidence/20260803-incubator-ingestion.json)

Closed at 2026-08-03T14:48:29.346132+00:00.
