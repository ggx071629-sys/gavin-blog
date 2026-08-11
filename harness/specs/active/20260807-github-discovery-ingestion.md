---
id: spec-20260807-github-discovery-ingestion
level: L1
summary: 为博客建立 GitHub 发现画像、私有资料仓库同步与待处理池摄入闭环
load_when:
  - task:20260807-github-discovery-ingestion
author: Gavin
task_id: 20260807-github-discovery-ingestion
status: frozen
frozen_at: 2026-08-08
freeze_reason: waiting for 20260807-github-source-crawler and real cross-repository E2E
frozen_scope_sha256: 52c972a14206e4250224ccb44991d5c748cf8c3d0886e436db03d1f6d6ada361
state_history:
  - {"action":"freeze","at":"2026-08-08","baseline":"migration","reason":"waiting for 20260807-github-source-crawler and real cross-repository E2E","scope_sha256":"52c972a14206e4250224ccb44991d5c748cf8c3d0886e436db03d1f6d6ada361"}
---

# Context

[知识孵化工作台需求设计](../../docs/product/knowledge-incubator.md) 的首期六段已经完成，其中 GitHub 摄入、主动发现和定时来源维护被明确排除。经新一轮需求确认，GitHub 现被授权为首期之后的独立资料来源：博客负责维护栏目／标签驱动的发现画像，并从一个固定私有资料仓库拉取 GitHub Actions 已采集的 Markdown；全局 GitHub 搜索、抓取、硬过滤和无模型评分不在本项目执行。

当前摄入链只支持 `file` 与一次性 `url`，通过 FastAPI 快速持久化意图、SQLite Worker 串行处理、不可变原始层和资料修订、正文 SHA-256 精确去重及待处理池人工闸门完成闭环。本任务将复用这些边界，并命中用户可见行为、API、数据模型、认证、安全、跨端契约和外部仓库协作风险。

本规格与 [GitHub 资料爬虫规格](20260807-github-source-crawler.md) 共同冻结跨仓库契约；本任务先实现项目侧基础，外部爬虫后实现并按本规格提供的机器画像和资料格式协作。

# Goal

管理员可以在现有栏目和标签之上维护独立 GitHub 发现规则、显式 GitHub 订阅与来源信任规则。项目通过只读机器接口向独立 `knowledge-sources` GitHub Actions 导出启用画像；资料仓库 `sources` 分支更新后，经过验签的 Webhook 创建可恢复同步任务，Worker 使用 GitHub 官方 REST API 按固定 commit 拉取新增或变化的 Markdown，复用现有清洗与精确去重后自动进入现有待处理池。同步、来源、分数、许可证、上游版本和失败均可观察，但检索、LLM 审计、草稿和发布仍只由管理员主动触发。

# Non-goals

- 不在 `my_blog` 中实现 GitHub 全局搜索、候选仓库发现、文章硬过滤或相关度评分。
- 不执行 `git clone`、`git pull`、仓库脚本、Hooks、Actions 或任何摄入内容。
- 不支持多个资料仓库，也不允许项目向资料仓库或其他 GitHub 仓库写入。
- 不实现 Obsidian、RSS、Atom、GitHub 之外的定时网页发现；现有一次性公网 URL 摄入保持不变。
- 不使用 LLM、Embedding 或重排序模型为 GitHub 候选资料评分。
- 不因资料入池而自动检索、审计、生成草稿、消耗第三方 Token 或发布文章。
- 不做语义去重；相似但非完全相同的正文保持为独立资料。
- 不建立第二套 GitHub 审核池，不改变现有三池和人工发布闸门。
- 不确定部署平台，不创建 `infra/` 或 `deploy/` 目录，也不在仓库中保存真实 Token。
- 不在本任务创建或实现独立 `knowledge-sources` 仓库；该交付由配套规格负责。

# Acceptance criteria

## 1. 发现画像与管理契约

- 发现规则是独立业务实体，不向 `categories` 或 `tags` 表塞入搜索职责。每条规则必须引用一个现有栏目，可引用零到多个现有标签，并保存启用状态、名称、GitHub Topics、正向关键词／别名、负向关键词及每轮查询上限；栏目或标签删除时不得留下悬空规则。
- 不自动组合全部栏目与标签。只有管理员显式创建并启用的规则才能导出；一条规则最多允许爬虫生成 3 条 GitHub 查询。
- 显式订阅是独立实体，首版类型仅包括 GitHub 仓库、目录和单个 Markdown 文件。Obsidian、RSS、Atom 和普通网页订阅不能通过空类型或占位实现混入。
- 来源信任规则独立于相关度：支持 `trusted`、`unverified`、`blocked`，并允许管理员显式维护仓库、作者／组织、路径忽略和阻止规则。全局发现默认 `unverified`，显式订阅或白名单可以标记 `trusted`，命中黑名单必须标记 `blocked`。
- 管理 API 和页面提供发现规则、GitHub 订阅及信任规则的增删改查，写操作继续要求 Session 与 CSRF；公共 taxonomy API 不暴露关键词、订阅或信任配置。
- 待处理池普通“丢弃”不得自动修改评分、发现规则或信任状态；界面另提供“忽略此路径”“阻止仓库”“阻止作者／组织”“添加排除词”等显式动作。

## 2. 只读机器画像接口

- 提供专用机器接口导出启用的发现规则、显式 GitHub 订阅、白名单／黑名单、配置版本和更新时间，不返回文章草稿、管理员资料或其他后台数据。
- 接口使用独立高熵 Bearer Token，不复用管理员 Session、CSRF 或 GitHub PAT。Token 仅通过服务端环境变量注入，不进入数据库、OpenAPI 示例、日志或响应。
- 缺失、错误或撤销 Token 返回稳定认证错误；健康响应只报告是否配置，不回显 Secret。
- 配置响应具有确定性排序和版本标识；相同版本生成相同规范 JSON，供 GitHub Actions 缓存和审计。

## 3. 单一私有资料仓库配置

- 服务端配置固定资料仓库 `owner/repository`、读取分支 `sources`、文章根目录 `articles/`、只读 Fine-grained PAT 和 Webhook Secret。首版不提供多仓库 CRUD。
- PAT 权限文档明确限制为指定私有资料仓库 `Contents: Read-only`；项目不得要求 Actions、Issues、Administration 或写权限。
- 配置和健康状态只显示经过净化的仓库身份、分支、最近验证时间与稳定错误码，不记录带凭据 URL、Authorization Header 或 Token。
- GitHub REST 请求使用固定 API 版本、超时、有限重试、`Retry-After`／rate-limit reset 退避及可观察错误；不得在限流期间无界重试。

## 4. Webhook 与同步任务

- 提供 GitHub `push` Webhook 入口，使用原始请求体校验 `X-Hub-Signature-256`；只接受配置仓库和 `sources` 分支，其他仓库、分支、无效签名或超时重放明确拒绝。
- `X-GitHub-Delivery` 与目标 commit SHA 均持久化并幂等；重复投递不得创建第二个有效同步任务。
- Webhook 请求只验证并排队，不拉取仓库或清洗正文。现有持久 Worker 执行同步，页面另提供要求 Session+CSRF 的“立即同步”按钮。
- 同一仓库同时最多一个同步任务运行。运行期间收到多个新 SHA 时只保留最新目标；当前任务结束后从已保存 checkpoint 直接同步到最新 SHA，不强制逐个处理机械中间提交。
- 同步任务保存目标 SHA、基准 SHA、状态、进度、尝试次数、租约、错误、开始／完成时间和成功／重复／失败／删除／跳过统计，并出现在现有全局任务观察面。

## 5. 首次全量与后续增量

- 首次同步扫描配置分支和文章目录的完整当前快照；后续保存最后成功同步 commit，并使用 GitHub 官方 Compare／Git Tree／Blob 等 REST 能力读取变更，不维护服务器 Git 工作副本。
- 如果基准 commit 不可比较、发生 force-push／历史重写、增量结果截断或 checkpoint 不再可达，任务退回完整快照对账，不猜测缺失变更。
- 资料仓库树、清单或必要 Blob 列表未完整取得时，整次同步失败且 checkpoint 不前移。完整变更清单已持久化后，逐文件处理允许部分成功。
- 每个变化文件先保存独立摄入事件与原始 Blob。合法项分别清洗入池；元数据缺失、超限或清洗失败项独立失败并可用已保存原始 Blob 重试，不依赖上游 commit 继续可用。
- 所有变化均形成持久事件后允许 checkpoint 前移，即使存在文件级失败；失败项不得因 checkpoint 前移消失。
- 固定目录外文件、隐藏文件、符号链接、Submodule、Git LFS 指针、二进制文件及非 `.md`／`.markdown` 文件忽略并留有可审计计数。单文件继续使用 2 MiB 上限。

## 6. GitHub 来源、版本与去重

- GitHub 来源记录至少覆盖稳定 GitHub repository ID、`owner/repository`、相对路径、默认／来源分支、Git Blob SHA、源 commit SHA、固定 permalink、原始来源 URL、抓取时间、发现规则、匹配栏目／标签、规则版本、0–100 分数及拆解、信任状态、许可证状态和上游状态。
- 资料仓库 Markdown 必须满足配套规格的系统 Frontmatter 契约；项目自行验证仓库、分支、路径、commit 和 Blob，不信任文件声明覆盖同步上下文。Frontmatter 后正文按原始载荷保存，正式清洗只在项目 Worker 内执行。
- 同一 Blob SHA 重复同步直接跳过；同一路径 Blob 改变时创建不可变资料新修订、返回待处理池，并使绑定旧修订的审计报告和草稿按现有规则失效。
- 清洗后正文 SHA-256 在所有来源类型间执行全局精确去重。不同仓库／路径正文完全相同时只新增摄入事件与镜像溯源，不创建第二条可审计资料或重复消耗 Token。
- 原始来源 URL 相同但正文变化时视为同一来源的新版本；正文仅相似时不做语义合并。
- 上游删除只将来源标记为 `upstream_deleted` 并记录 tombstone；不得自动删除原始载荷、资料修订、审计、草稿、已发布文章或来源链。路径变化首版可表示为旧路径删除加新路径新增。

## 7. 待处理池与人工闸门

- 通过清洗且非精确重复的 GitHub 资料自动进入现有待处理池，不建立独立池。列表支持按 `source_type=github`、仓库、发现规则、栏目、标签、分数区间、信任状态、许可证状态和上游状态筛选，并保持有界分页与稳定 URL。
- GitHub 资料详情显示固定 commit permalink、仓库／路径、原始正文与清洗后 Markdown 对照、分数拆解、命中规则、许可证、信任状态、同步历史和镜像／版本关系。
- 工作台概览显示资料仓库连接健康、最后成功 checkpoint、最近同步统计、Webhook／Worker 状态和“立即同步”入口；任何 Secret 均不可见。
- 分数只用于排序和解释，不阻止已经通过爬虫硬门槛的资料进入待处理池，也不自动改变审计资格。
- 进入待处理池不自动运行模型或第三方调用。只有管理员主动发起现有审计流程后，才按现有本地混合检索和外发确认边界推荐旧文并调用 LLM。

## 8. 许可证、引用与发布安全

- GitHub 公开可见不等于允许转载。资料必须保存仓库许可证信息或 `unknown`，并始终保留固定 commit permalink 与作者／仓库来源。
- 无许可证资料可以进入私人待处理与审计流程，但生成和发布提示必须禁止大段复制；公开发布仍要求人工确认并保留可追溯来源。
- 外部 Markdown 永远按不可信数据处理。Frontmatter、正文、链接、HTML 和提示注入不得改变系统指令、越权引用 ID、执行脚本或影响管理页面渲染。

## 9. 契约、迁移与兼容性

- SQLite 数据模型变化只通过新 Alembic migration 完成；迁移不得访问 GitHub、创建同步任务或读取真实 Secret，并能从当前 head 升级和完整降级。
- OpenAPI 快照和 Web 类型同步覆盖发现规则、订阅、信任规则、机器画像、Webhook 安全错误、同步任务、GitHub 来源与新筛选字段。
- 现有 `file`、一次性 `url`、LLM 审计、草稿、发布、文章版本和公开 API 行为不回退。

# Risks

- **Webhook 伪造与重放**：必须基于原始请求体执行恒定时间 HMAC 校验，并以 delivery ID 和 commit SHA 双重幂等。
- **PAT 泄露**：只读细粒度 Token 仍能读取私人资料；不得进入数据库、日志、错误、URL、前端或测试快照。
- **仓库历史重写**：只依赖线性 Compare 会漏数据；不可比较时必须完整对账且不破坏本地历史。
- **部分失败与 checkpoint**：先前移 checkpoint 会丢失失败文件，永不前移则会重复正常文件；必须先持久化逐项事件再推进。
- **跨来源重复**：镜像仓库、路径变化和显式订阅会重复发现；Blob、正文指纹和来源 URL 职责必须分离。
- **提示注入与不可信 Markdown**：GitHub 内容可能刻意攻击后续 LLM；清洗、引用白名单和外发确认不能因来源是 GitHub 而放宽。
- **版权误用**：公开仓库不自动授予文章转载权；许可证状态、固定来源和人工发布闸门必须可见。
- **范围回流**：不得把外部爬虫、无模型评分或 RSS 调度“顺手”塞入本项目实现。

# Verification plan

1. **TDD**：覆盖发现规则约束、配置规范 JSON、显式反馈动作、HMAC 验签、delivery/SHA 幂等、任务合并、完整／增量对账、部分失败 checkpoint、版本更新、删除 tombstone 和跨来源精确去重。
2. **Contract**：在临时 SQLite 上升级、降级再升级；生成 OpenAPI 并断言机器画像、Webhook、同步任务、GitHub 来源、筛选和稳定错误码与 Web 类型一致。
3. **Integration**：使用确定性 GitHub REST 测试替身覆盖私有仓库认证、树与 Blob 拉取、Compare 不可用、force-push、限流退避、超时、截断、单文件失败、重放和 Worker 崩溃恢复；测试不得访问公网或真实资料仓库。
4. **E2E**：覆盖“管理员创建发现规则 → 模拟 sources push → Webhook 排队 → Worker 同步 → GitHub 资料入待处理池 → 查看溯源与分数 → 显式阻止来源”，并证明未自动调用本地模型、第三方 LLM 或发布。
5. **Security**：断言无效签名、错误仓库／分支、缺失机器 Token、越权管理写入和恶意 Frontmatter／Markdown 均被拒绝；响应、日志和快照不出现 Secret。
6. **Quality**：API Pytest 与 Ruff、Harness checks、OpenAPI 快照、Web Vitest、类型检查、生产构建、适用 Playwright 与 WCAG 检查通过；现有 file/url 与知识孵化闭环不回退。
7. **Harness**：更新来源元数据后运行 `python -m tools.harness index` 与 `python -m tools.harness verify 20260807-github-discovery-ingestion`；只有应用检查和跨仓库契约证据齐全后才能关闭。
