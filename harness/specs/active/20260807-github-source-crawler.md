---
id: spec-20260807-github-source-crawler
level: L1
summary: 在独立私有仓库中用 GitHub Actions 无模型发现并保存文章型 Markdown
load_when:
  - task:20260807-github-source-crawler
author: Gavin
task_id: 20260807-github-source-crawler
status: frozen
frozen_at: 2026-08-07
freeze_reason: waiting for my_blog domain deployment and real cross-repository E2E
frozen_scope_sha256: 54cb3556020ab5df1977287cd171a3ea12e1a304fcf5927938b788f656f5c106
state_history:
  - {"action":"freeze","at":"2026-08-07","baseline":"migration","reason":"waiting for my_blog domain deployment and real cross-repository E2E","scope_sha256":"54cb3556020ab5df1977287cd171a3ea12e1a304fcf5927938b788f656f5c106"}
---

# Context

本任务是 [GitHub 发现画像与仓库摄入规格](20260807-github-discovery-ingestion.md) 的上游配套交付。经需求确认，首版内容发现严格限定 GitHub：GitHub Actions 从 `my_blog` 的只读机器画像读取管理员启用的栏目／标签发现规则、显式 GitHub 订阅和来源信任配置，只调用 GitHub 官方 API 搜索整个 GitHub 的公共内容，使用可解释的确定性规则过滤和排序文章型 Markdown，并把结果提交到独立私有 `knowledge-sources` 仓库。`my_blog` 不承载爬虫或评分代码。

GitHub 自定义 Topic、仓库元数据和代码搜索不理解博客栏目语义，因此机器画像必须把栏目／标签映射为显式 Topics、关键词、别名和排除词。本任务不得引入 LLM、Embedding、重排序模型或第三方搜索服务来弥补规则不足。

# Goal

建立一个与 `my_blog` 隔离的私有 `knowledge-sources` 仓库：`main` 分支保存 GitHub Actions、爬虫代码、配置与测试，`sources` 分支保存系统 Frontmatter、未改写的原始 Markdown 正文和追加式发现清单。Actions 每天唤醒，在距上次成功全局发现至少 72 小时时，按启用规则两阶段搜索 GitHub 候选仓库和文章型 Markdown；通过硬门槛的资料全部保存，无模型相关度分仅用于排序。成功提交后 Webhook 通知博客同步，失败、限流、重复、许可证和来源均可审计。

# Non-goals

- 不修改、扫描、评分或优化 `my_blog` 代码仓库；只读取其专用机器画像接口。
- 不使用 Brave、Google、Bing 或其他第三方搜索 API，不抓取搜索结果页面。
- 不实现 RSS、Atom、普通网页定时抓取或 Obsidian；显式订阅首版仅限 GitHub 仓库、目录和 Markdown 文件。
- 不使用 LLM、GitHub Copilot、Embedding、重排序模型或任何模型为候选资料评分、分类或去重。
- 不扫描私有外部仓库、Fork、归档／禁用仓库、非默认分支、PR 分支、历史 commit、Wiki、Gist、Issue、Discussion 或普通源代码。
- 不在 Actions 中执行被发现仓库的脚本、构建、Hooks、Submodule 或 Git LFS 对象。
- 不自动调用博客审计、生成草稿或发布文章；Action 的终点是向 `sources` 分支提交资料并发送 Webhook。
- 不创建多资料仓库、多用户审批、独立消息队列或常驻爬虫服务。
- 不以 Stars、Forks、Watchers 或作者知名度替代相关度或来源信任判断。

# Acceptance criteria

## 1. 独立仓库与分支边界

- 创建独立私有 `knowledge-sources` 仓库。`main` 只保存 `.github/workflows/`、爬虫实现、测试和人工维护配置；`sources` 只保存 `articles/`、`manifests/discoveries.jsonl`、同步状态及生成数据。
- Actions 从 `main` 运行，以普通非 force-push commit 更新 `sources`；生成数据不得反向修改 `main`。博客只读取 `sources`，Webhook 只为 `sources` push 通知博客。
- 采集文章按稳定仓库 ID、owner/repository 与原始相对路径形成无冲突路径；路径规范化必须阻止绝对路径、`..`、保留名、大小写碰撞和超长路径。
- 生成 commit 使用固定 Bot 身份并包含运行 ID、画像版本、规则版本、新增／更新／删除／重复／拒绝统计；没有数据变化时不得创建空 commit 或发送同步 Webhook。

## 2. Actions 权限与 Secret

- 爬虫只使用 Actions 自动生成的短期 `GITHUB_TOKEN` 搜索公共 GitHub 内容并写当前资料仓库；Workflow 权限显式最小化为当前仓库所需 `contents: write`，不配置可访问其他私有仓库的全局 PAT。
- `CRAWLER_PROFILE_TOKEN` 只调用博客机器画像接口；`BLOG_WEBHOOK_SECRET` 只签名博客同步通知。两个 Secret 不得进入仓库、Artifact、Cache、命令回显、日志或测试快照。
- 对 GitHub API 使用固定版本、明确 User-Agent、有限并发、超时、分页上限、ETag／条件请求、`Retry-After` 和 rate-limit reset。遇到 primary 或 secondary rate limit 时停止并按官方时限退避，不持续请求导致集成封禁。

## 3. 画像读取与失败边界

- 每次运行先通过 Bearer Token 获取规范机器画像，验证 schema version、配置版本、更新时间、规则、订阅和信任列表。画像缺失、认证失败、schema 不支持或内容无效时整次失败，不使用来源不明的本地默认配置继续发现。
- 每条发现规则必须含一个栏目、零到多个标签、Topics、正向关键词／别名、负向关键词和查询上限。爬虫不自动生成所有栏目×标签组合；一条规则最多生成 3 条 GitHub 查询。
- 显式订阅只接受公共 GitHub 仓库、默认或明确指定分支下的目录／Markdown 文件；订阅目标仍须通过安全、格式、大小和许可证记录边界，但可标记 `trusted` 并绕过文章路径偏好。

## 4. 调度、手动触发与运行上限

- Workflow 每天以 UTC cron 唤醒，从 `sources` 状态读取 `last_success_at`；距上次成功未满 72 小时时正常退出且不调用搜索 API，已满 72 小时才执行 GitHub 全局发现。
- 全局发现失败不得更新 `last_success_at`，使次日可重试。`workflow_dispatch` 支持显式强制运行并记录操作者和原因，不受 72 小时门槛限制。
- 每条规则最多生成 3 条查询；每条查询最多检查 20 个候选仓库；每个仓库最多保存 5 篇新文章；每轮最多新增 100 篇、单篇最多 2 MiB、正文总量最多 50 MiB。
- 达到查询、候选、文章或字节上限时停止对应范围并在清单保存截断游标／原因；下一轮可以确定性继续。已见 Blob SHA、固定来源版本和来源 URL 不计入新增额度。

## 5. 两阶段 GitHub 官方 API 发现

- 第一阶段把规则中的栏目／标签映射 Topics、关键词和排除词转换为 GitHub Repository／Topic 搜索，只返回公共、未归档、未禁用、非 Fork 仓库。默认分支是唯一主动发现分支。
- 第二阶段在候选仓库默认分支中使用 GitHub Code Search、Git Tree、Contents 与 Blob 等官方 REST 能力定位 `.md`／`.markdown` 候选。不得通过抓取 github.com HTML、执行 `git clone` 或读取非默认分支扩展结果。
- GitHub API 返回的 repository ID、owner、name、default branch、commit SHA、Blob SHA、path、permalink、Topics、许可证和更新时间均按原始元数据保存；分支名称或仓库重命名不得破坏稳定身份。
- 连续运行对相同画像版本、规则版本和 GitHub commit 产生相同候选集合与分数；分页、排序和并列处理必须确定性。

## 6. 文章硬门槛

- 只接受 `.md`／`.markdown`、有标题或首个 H1、正文达到配置的最低有效长度且不超过 2 MiB 的普通 Blob。符号链接、Submodule、Git LFS 指针、二进制、生成文件和无法固定到 commit 的内容硬拒绝。
- 明确排除 LICENSE、CHANGELOG、CONTRIBUTING、SECURITY、CODE_OF_CONDUCT、Issue／PR 模板及等价工程文件；自动生成标记、极端徽章／目录占比、空正文和正文主要为代码块的文件按版本化确定性规则拒绝。
- `posts/`、`articles/`、`blog/`、`content/`、`docs/` 等知识路径只是相关度信号，不单独构成硬门槛。README 默认低优先级；只有显式订阅或达到其他相关性条件时保存。
- 命中 `blocked` 仓库、作者／组织或路径规则必须拒绝；`trusted` 仍不能绕过文件安全、大小和恶意路径边界。

## 7. 无模型相关度评分

- 评分实现是版本化纯函数 `github-discovery-v1`，不得访问网络、模型或随机源。输入仅包括规范画像规则、GitHub 元数据和 Markdown 文本；输出 0–100 总分、逐项分数和命中证据。
- 基础分拆解为：标题／H1 关键词命中 30，Repository Topic 命中 15，H2／H3 命中 15，正文关键词跨自然段命中 10，文章型路径 10，合理正文长度 10，章节充分且非代码块为主 10。重复命中不得突破各项上限。
- 负向关键词、代码块比例、模板／徽章／目录比例及标题正文关键词分布异常使用确定性扣分，总分下限为 0。大小写、Unicode 规范化、中英文边界、短语匹配和停用词规则必须冻结并有单测。
- 评分只用于排序和解释。通过硬门槛的资料无论分数高低都保存；不得通过隐藏阈值、Top-K 截断或模型判断静默拒绝，只受已确认每轮 100 篇安全上限约束。
- Stars、Forks、Watchers、仓库流行度和作者身份只可作为展示元数据，不进入相关度分。

## 8. 来源信任、许可证与不可信内容

- 来源信任严格使用画像中的显式规则：订阅／白名单为 `trusted`，普通全局发现为 `unverified`，黑名单为 `blocked`。相关度高不得自动提升信任，单篇低分或后续丢弃不得自动惩罚仓库。
- 普通待处理池丢弃不自动反馈。只有管理员显式选择忽略路径、阻止仓库、阻止作者／组织或添加排除词后，下一版机器画像才改变爬虫行为。
- 保存 GitHub 返回的 SPDX／许可证信息；缺失或不明确时写 `license_status: unknown`。无许可证不阻止私人摄入，但元数据必须提醒下游不得直接转载大段正文。
- 所有外部 Markdown 都是不可信数据。爬虫不得解释其中的指令、执行代码、展开远程 include、下载图片或跟随正文链接继续爬取。

## 9. 资料文件与追加式清单

- 每篇生成 Markdown 顶部包含受限系统 Frontmatter：schema version、发现时间、画像／规则版本、规则 ID、栏目／标签、Topics／关键词命中、总分及拆解、信任状态、原 repository ID 与全名、路径、默认分支、源 commit SHA、Blob SHA、固定 permalink、许可证和原始来源 URL。
- Frontmatter 后的源 Markdown 正文必须保持原始字节不变；另记录原始 Blob SHA 和正文 SHA-256 供博客验证。系统元数据与源文件自带 Frontmatter 必须职责分离，不能让源内容覆盖系统字段。
- `manifests/discoveries.jsonl` 以追加方式记录 discovered、saved、skipped、duplicate、updated、deleted、blocked、rejected、truncated 和 failed 事件，包含运行 ID、原因、规则版本和必要稳定身份；不得保存 Secret、Authorization 或完整 GitHub API 响应。
- 相同 Blob SHA 重复发现直接跳过；同一路径 Blob 改变时更新当前生成文件并追加 `updated`；上游删除时删除 `sources` 当前镜像并追加 tombstone，Git 历史继续保留旧正文。
- 跨仓库／路径的精确正文去重最终由博客清洗后 SHA-256 决定；爬虫可提前记录相同 Blob 或原始来源 URL，但不得做语义合并。

## 10. 提交、通知与失败恢复

- 一轮运行先在临时工作区完成画像验证、发现、过滤、评分、限额和生成文件校验；任何仓库级不完整结果不得产生半成品 commit。
- 合法资料与逐项拒绝允许部分成功。生成数据通过测试和 schema 校验后，以一次普通 commit 原子更新 `sources`；commit 成功才更新 `last_success_at`。
- commit 成功后使用独立 Webhook Secret 对原始 JSON 请求体做 HMAC-SHA256，通知博客仓库、`sources` ref、before/after SHA 和唯一 delivery ID。通知失败不回滚 Git commit，但必须明确失败并允许人工重发。
- 同一 GitHub 内容、同一 sources commit 或重试运行具有幂等保护。运行中断、Action rerun 或 Webhook 重放不得创建不同内容、重复 manifest 事件或额外资料。

## 11. 无模型质量门槛

- 建立至少 60 个手工标注 fixture，覆盖中文、英文、中英混合、正常技术文章、代码占比高、README、模板、许可证、镜像、负向关键词和恶意 Markdown。
- 明确 LICENSE、模板、安全策略等非文章 fixture 的硬过滤通过率必须为 100%。每条代表性发现规则按确定性分排序后，Top 20 中至少 80% 被标注为相关。
- 质量测试必须离线运行，GitHub API 使用固定响应 fixture；不得通过实时搜索结果让 CI 不稳定，也不得用模型生成标签或期望值。
- 重复处理同一画像、commit 和 fixture 必须产生字节级相同的生成文件、分数和清单事件；第二次运行新增资料数为 0。

# Risks

- **栏目语义与 GitHub 元数据错位**：Topics 和关键词不是语义模型；必须靠显式规则、标注集和可解释拆解校准，不伪称理解内容。
- **搜索限额与结果截断**：Code Search 限额严格且结果有上限；查询、分页、缓存、继续游标和退避必须有界，不能通过并发绕过限制。
- **仓库垃圾与提示注入**：整个 GitHub 包含模板、镜像、恶意 Markdown 和模型提示；硬过滤、信任状态和不执行内容是安全边界。
- **Actions 权限扩大**：内置 Token 需要写当前资料仓库，但不得发展为访问账号其他私有仓库的 PAT。
- **自动提交循环**：`main` 与 `sources` 分离，Workflow 触发器和路径必须防止生成 commit 再次触发无限运行。
- **数据仓库膨胀**：100 篇／轮和 50 MiB 只是单轮边界；长期 Git 历史增长需观测，未授权 Git LFS、历史重写或对象存储迁移。
- **版权与归因**：公开 GitHub 文件不等于自由转载；固定 permalink、许可证状态和下游人工闸门不能省略。
- **跨仓库契约漂移**：机器画像、Frontmatter、manifest 和 Webhook schema 必须版本化；任一侧未知版本应失败而非猜测兼容。

# Verification plan

1. **TDD**：离线 fixture 覆盖查询生成、Topic／关键词映射、Unicode 匹配、硬过滤、分数拆解、信任规则、许可证、路径安全、限额、状态清单、幂等和 72 小时调度门槛。
2. **Contract**：为机器画像、系统 Frontmatter、`discoveries.jsonl` 和 Webhook 定义版本化 JSON Schema／示例，并与 `my_blog` 配套规格的消费者测试双向校验。
3. **Integration**：使用录制并净化的 GitHub REST fixture 覆盖 Repository／Topic／Code Search、Tree／Blob、分页、ETag、限流、截断、仓库重命名、默认分支变化和 Action rerun，不在 CI 访问实时 GitHub 搜索。
4. **Security**：验证 Workflow 最小权限、Secret 不回显、恶意路径／Frontmatter／Markdown 不执行、外部链接不跟随、黑名单硬拒绝和 Webhook HMAC。
5. **Quality**：至少 60 个标注案例、明确非文章硬过滤 100%、每条代表性规则 Top 20 相关率至少 80%；生成结果可重复且不调用任何模型或第三方搜索 API。
6. **Cross-repo E2E**：用隔离测试仓库或完全确定性替身覆盖“画像读取 → GitHub 候选 → sources commit → Webhook → 博客同步 → GitHub 资料进入现有待处理池”，并证明未自动审计或发布。
7. **Harness**：本规格只在配套消费者契约、爬虫检查和跨仓库证据齐全后运行 `python -m tools.harness verify 20260807-github-source-crawler` 并关闭；不得以只通过文档检查代替外部仓库验证。
