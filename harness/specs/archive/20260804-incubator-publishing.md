---
id: archive-20260804-incubator-publishing
level: L2
summary: 以发布前复检、原子文章修订、永久来源链和有限批量处理完成知识孵化发布闭环
load_when:
  - task:20260804-incubator-publishing
author: Gavin
task_id: 20260804-incubator-publishing
status: compressed
restoration_source: "8a9844c657124b1319e8c04795a9af5cde0b97d9:harness/specs/active/20260804-incubator-publishing.md"
restored_at: 2026-08-11
---

# 20260804-incubator-publishing

Deterministic compressed record. The original active spec remains in Git history.

## Goal

管理员可以对一个 ready 孵化草稿创建本地发布计划，查看即将公开的文章差异、分类、来源引用和全部阻断项，显式点击“确认并发布”后原子完成增补、重构或新分支发布。符合高置信规则的增补与新分支可以有限批量发布，并以逐项独立事务实现部分成功。每个成功项只发布一次，创建不可变文章修订、索引任务和不可抹除的资料／审计／草稿来源链；管理员还可以查看全部文章发布版本、比较差异，并通过创建新版本安全回滚。

## Acceptance criteria

## 1. 发布计划、操作与来源数据边界

- Alembic 增加职责分离的发布计划／计划项、发布操作、内部来源关联和文章修订公开引用快照。表名可按现有惯例调整，但计划快照、幂等执行记录、永久内部溯源和可公开引用必须分离。
- 发布计划接受 1–20 个不同 `draft_id`，冻结每项的 draft ID、role、status、`edit_version`、工作副本规范化 SHA-256、active generation version、资料修订、审计版本、目标文章／发布修订、置信度、degraded、风险、冲突来源、分类候选、引用选项和本地检索 pipeline／manifest。计划创建不改变文章或草稿。
- 发布计划状态至少覆盖 `planning`、`ready`、`blocked`、`confirmed`、`partially_published`、`published`、`stale` 和 `failed`；计划项保存角色适配预览、资格、阻断码、警告、本地复检结果和最终发布操作。
- 每个执行项持久化服务端生成的幂等键，数据库唯一约束保证同一 draft 只能产生一个成功的孵化发布修订。确认请求、网络重试、页面刷新或 Worker 重放不得重复发布、重复增加修订号或重复登记索引任务。
- `IncubatorDraft.status` 增加 `publishing`、`published` 和 `publish_failed`。失败项保留可编辑工作副本、失败码和最近操作，可修复后创建新计划；成功项只读并永久指向发布后的 article／revision。
- `ArticleRevision.source` 使用有界值 `editor|incubator|rollback`。孵化来源关联至少冻结 article revision、source／source revision、audit version、draft／draft edit version、active generation version、role、操作者和时间；回滚修订额外冻结 `rollback_from_revision_id`。
- 已被任一发布修订引用的资料、资料修订、审计、草稿、生成版本和发布操作不得永久删除。逻辑丢弃或源站失效不破坏历史链。

## 2. 本地发布计划与最终确认

- `POST /api/v1/admin/incubator/publish-plans` 接受 1–20 个 draft ID，要求 Session＋CSRF，返回 `202` 和异步本地计划任务；不调用第三方 LLM、不产生 Token 或外发内容。
- Worker 为每个计划项独立执行资格检查与预览。增补／重构检查绑定目标和文章工作副本；新分支执行当前完整本地混合检索复检。一个计划项失败不阻止其他项完成规划。
- `GET /api/v1/admin/incubator/publish-plans/{plan_id}` 返回稳定计划状态、每项文章／角色／差异摘要、公开引用、批量资格、阻断码和警告，不返回上传文件名、原始正文、完整审计或后台内部链。
- ready 计划的最终弹窗逐项列出将创建或更新的公开文章、目标发布修订、标题／slug／栏目／标签、正文差异摘要和将展示的参考资料。按钮明确命名为“确认并发布”，不能只写“确认”或“完成”。
- `POST /api/v1/admin/incubator/publish-plans/{plan_id}/confirm` 必须携带 `publish_confirmed = true`；缺失、false 或计划尚未 ready 时不执行。计划本身不是授权，前端不能在生成计划后自动确认。
- 最终提交开始前前端必须 `flush()` 当前草稿的自动保存队列；保存失败、`409` 或存在更新排队时禁止确认。后端仍核对计划冻结的 `edit_version` 和工作副本哈希，不能信任前端已 flush 声明。
- 草稿、资料、审计、生成版本、目标修订、文章工作副本、分类、检索 manifest 或公开引用选项在规划后变化时对应项以 `PUBLISH_PLAN_STALE` 拒绝，必须创建新计划。最终确认不自动采用新状态。
- 最终文章写事务开始后不可取消。前端禁用重复操作并显示逐项结果；关闭页面后重新打开计划仍可读取确定的成功／失败状态。

## 3. 共同发布事务与一致性

- 每个草稿使用独立、短 SQLite 事务重新获取并校验全部前置状态，然后依次写入文章工作副本、不可变发布修订、来源关联、公开引用快照、公共 FTS 投影和 `article_index` intent，最后原子切换 draft／article 指针。任一步失败全部回滚。
- 对增补／重构，目标 `Article.current_revision_id` 必须等于 draft 绑定修订，文章不得删除，且当前工作副本哈希必须等于当前发布修订哈希。普通编辑器存在任何未发布修改时返回 `ARTICLE_WORKING_COPY_DIRTY`，绝不覆盖或静默合并。
- 最终写入以文章 `version` 乐观锁防止普通编辑器并发保存。提交前版本或当前发布指针改变返回 `ARTICLE_VERSION_CONFLICT`；数据库锁冲突使用有界重试，耗尽后显式失败而不是假定成功。
- 成功发布创建且只创建一个下一修订号，保持文章首次发布时间语义，更新工作副本和 `version`，使公开读取、RSS、站点地图和公共搜索立即读取新修订。索引异步失败不回滚已发布内容，但检索健康进入 stale 并显示待索引状态。
- 成功发布调用现有目标变更失效链，使依赖旧修订的其他审计／草稿 stale；本次已发布 draft 必须先被排除或保持 `published`，不能被自己的发布钩子改成 stale。
- 发布操作失败时不得残留 article、revision、revision tags、公开引用、来源关联、搜索投影或索引任务的部分写入。draft 回到 `publish_failed`，保留可修复工作副本和安全错误摘要。

## 4. 增补发布

- 发布计划和最终事务都在当前目标发布修订上重新解析 H2／H3，核对 `anchor_id`、标题层级路径、出现序号和上下文 SHA-256。锚点缺失或变化返回 `PATCH_ANCHOR_MISSING`／`ARTICLE_VERSION_CONFLICT`。
- 后端使用当前保存的工作副本在绑定修订上确定性应用一次结构化补丁，并验证所得 Markdown 与计划预览哈希一致。禁止信任模型保存的旧 merged Markdown，禁止在锚点失败时追加到正文末尾。
- 新修订只改变补丁合并后的正文；标题、slug、摘要、首次发布时间、栏目和标签与目标当前发布修订完全一致。
- 批量资格要求：审计置信度 `>= 0.95`、非 degraded、非 conflict 改判、无风险条目、草稿 ready、保存完成、目标版本／锚点／工作副本全部通过。否则仍可在无阻断项时逐条发布，但不能进入多选计划。

## 5. 重构发布

- 重构始终逐条发布。最终正文来自当前草稿工作副本；只有管理员已保存 `use_suggested_title`／`use_suggested_summary` 时才采用对应建议，否则保留目标发布修订值。
- slug、首次发布时间、栏目和标签固定为目标当前发布修订值。标题、摘要和正文执行现有长度／非空规则，目标版本或工作副本不干净时阻断。
- 计划展示目标当前发布修订与最终标题／摘要／正文差异，以及将被替换的正文规模；最终事务再次计算并核对差异输入哈希。

## 6. 新分支发布与本地相似性复检

- 新分支工作副本必须有非空标题和正文、唯一且格式有效的 slug、一个仍存在的栏目和至少一个仍存在的标签。未知／已删除分类、重复 slug 或空必填字段分别以稳定错误阻断；不得自动创建分类或改写 slug。
- 计划 Worker 使用工作副本标题＋正文、当前完整非 stale 索引和 full 模式执行本地混合检索；不得降级为 FTS-only，不调用第三方服务。模型或索引未就绪返回 `LOCAL_MODEL_NOT_READY`／`ARTICLE_INDEX_STALE`。
- 高度相似定义为：规范化标题或 slug 与现有已发布文章精确相同，或者任一候选片段语义余弦分数 `>= 0.92` 且通过当前 reranker 最低相关阈值。阈值作为版本化后端常量 `NEW_BRANCH_SIMILARITY_THRESHOLD`，变更它必须更新检索基准和本 spec 的后继决策。
- 命中高度相似文章时以 `SIMILAR_ARTICLE_FOUND` 阻断，计划返回文章 ID、标题、公开路径、发布修订和安全分数摘要，要求返回审计重新判定为增补或重构；本阶段没有强制覆盖。
- 最终事务再次检查 slug、分类和当前索引 manifest。规划后的文章发布会使 corpus stale 或 manifest 变化，因此不能使用旧复检结果，必须重新规划；事务内最后执行唯一约束兜底。
- 成功时创建新的已发布 Article 和发布修订 1，工作副本与公开修订一致，首次发布时间为本次提交时间，来源为 `incubator`，并登记索引任务。
- 批量资格额外要求审计置信度 `>= 0.95`、非 degraded、非 conflict 改判、无风险条目、分类完整且复检无命中。

## 7. 有限批量发布与部分成功

- 只有 2–20 个全部标记 `batch_eligible` 的增补／新分支草稿可形成批量计划；重构、冲突改判、低置信、degraded、风险非空或需要人工修复的项在创建计划时以逐项原因拒绝，不能混入后再静默跳过。
- 最终弹窗列出全部将公开变更的文章并显示总数；一次人工确认授权计划中的确定快照，不授权之后新增或修改的草稿。
- 确认后按计划项 ID 稳定顺序逐项执行独立事务。成功项立即提交且只发布一次；失败项回滚自身事务并保留在草稿池。响应和持久计划都返回 `published_count`、`failed_count` 及每项 article／revision 或错误码。
- 批量处理中后续项因前项发布导致索引 stale 时，新分支不得继续使用旧复检；为避免同批互相绕过，新分支还需对计划内其他新分支执行标题、slug 和本地向量两两复检。任一对高度相似时两个项均在确认前阻断。
- 相同目标文章最多出现一个增补项；重复目标在规划阶段以 `PUBLISH_TARGET_DUPLICATE` 阻断，避免计划内顺序改变目标修订。

## 8. 来源溯源与公开参考资料

- 每个孵化发布修订永久关联其资料修订、审计版本、草稿、draft edit version 和生成版本。后台文章版本详情可沿链打开对应历史，且链中任何一层后续 stale／discarded 都不改变既有发布记录。
- URL 资料默认建议公开引用，发布计划允许管理员编辑展示标题并关闭公开展示；公开链接固定使用摄入时已保存的规范原始 URL，不接受任意新 URL。展示标题最多 180 字符。
- 上传文件默认且只能作为后台来源，不公开原文件名、存储 key、下载地址或正文。本阶段不能通过编辑公开引用绕过这一限制。
- 公开引用按文章修订保存快照，不修改 Markdown 正文。公共文章 API 可选返回 `references`，文章页在正文末尾显示“参考资料”，链接使用安全的外部链接属性。普通编辑器后续发布默认继承当前公开引用快照并允许明确关闭，但不能删除内部来源链。
- 回滚到历史修订时复制该历史修订的公开引用快照；内部 origin 记录为 rollback 并指向所选修订，不伪装成新的孵化发布。

## 9. 全局文章版本、差异与回滚

- `GET /api/v1/admin/articles/{article_id}/revisions` 提供默认 20、最多 100、offset 最大 100000 的历史，按 `revision_number DESC` 稳定排序，返回来源类型、发布时间、校验值和来源／回滚摘要。
- `GET /api/v1/admin/articles/{article_id}/revisions/{revision_id}` 返回不可变标题、slug、摘要、正文、栏目、标签、公开引用和可访问的内部来源摘要；不返回原始资料正文、提示词或模型响应。
- `GET /api/v1/admin/articles/{article_id}/revision-diff?from_revision_id=&to_revision_id=` 返回标题、摘要、正文、栏目、标签和公开引用的结构化差异；两个修订必须属于同一 article。
- `POST /api/v1/admin/articles/{article_id}/revisions/{revision_id}/rollback` 要求 Session＋CSRF、当前 article `version`、当前发布修订 ID 和 `rollback_confirmed = true`。文章存在未发布工作副本时以 `ARTICLE_WORKING_COPY_DIRTY` 阻断，避免覆盖人工修改。
- 回滚复制所选历史快照到文章工作副本并创建新的下一发布修订，`source = rollback`，保持 article slug 和首次发布时间稳定。若历史 slug 与当前 slug 不同则阻断；历史分类实体已删除时阻断而不是创建或使用悬空分类。
- 回滚与普通／孵化发布一样同步公共投影、登记异步索引并使依赖旧当前修订的审计／草稿失效。历史行、原发布来源和原修订号永不改变。
- `/admin/articles/{id}/revisions` 提供历史、差异和回滚确认界面；文章编辑器与孵化发布成功页都能进入该稳定 URL。

## 10. 管理界面与跨端契约

- ready 草稿详情显示发布准备清单和“确认并发布”入口。点击后先 flush 自动保存，再创建发布计划；stale、discarded、generating、publishing、published 或保存冲突状态不得显示可执行入口。
- 草稿池支持勾选 batch eligible 项并创建有限批量计划；不合格项禁用选择并提供可读原因。筛选、分页、刷新和浏览器返回不能丢失服务端计划结果。
- `/admin/incubator/publish-plans/{id}` 是单条与批量共用的稳定确认／结果页，展示逐项 diff、来源引用、复检结果、阻断项和最终文章链接。状态、成功与失败不能只靠颜色表达。
- 发布成功后 draft 详情只读展示 article、revision、公开路径和来源链；失败时展示稳定中文错误并允许修复工作副本或重建计划，不提供“假定成功”。
- 文章公开页只在当前发布修订存在公开 URL 引用时显示参考资料；归档、RSS、站点地图、搜索及无引用文章行为保持不变。
- OpenAPI 同步 `packages/contracts/openapi.json` 与 Web 类型；所有知识孵化发布 API 位于 `/api/v1/admin/incubator`，读取要求 Session，写入要求 Session＋CSRF。文章版本管理沿用 `/api/v1/admin/articles` 权限边界。

## 11. 错误、安全与工程验收

- 本段至少落实 `DRAFT_STALE`、`PUBLISH_PLAN_STALE`、`PUBLISH_NOT_ELIGIBLE`、`ARTICLE_VERSION_CONFLICT`、`ARTICLE_WORKING_COPY_DIRTY`、`PATCH_ANCHOR_MISSING`、`SLUG_CONFLICT`、`SIMILAR_ARTICLE_FOUND`、`PUBLISH_TARGET_DUPLICATE`、`LOCAL_MODEL_NOT_READY` 和 `ARTICLE_INDEX_STALE`。
- Pytest 覆盖三角色发布、dirty working copy、锚点复核、slug／分类竞争、来源链、公开引用、幂等重复确认、事务回滚、批量部分成功、同批相似／同目标冲突、版本差异和回滚新修订。
- 本地相似性测试只使用当前确定性 embedding／reranker double，覆盖模型未配置、索引 stale、标题／slug 精确命中、阈值两侧、同批新分支相似和无命中；不调用第三方 LLM、不需要真实 API Key。
- Vitest 覆盖自动保存 flush 屏障、发布准备清单、单条／批量资格、最终确认、逐项结果、版本差异、回滚确认、状态和错误映射。
- Playwright 覆盖“摄入 → 审计确认 → 草稿生成／保存 → 发布计划 → 最终确认 → 公开文章／来源 → 版本回滚”的代表性闭环，以及一个批量部分失败案例；全部服务和模型使用隔离本地替身。
- API 全量测试、Ruff、Alembic 升降级、OpenAPI 契约、Web Vitest、类型检查、生产构建、既有 E2E、WCAG 和 Lighthouse 门槛继续通过；真实资料、API Key、模型二进制、重日志和截图不进入 Git。

## Result

Verified and closed by the harness close command.

## Evidence

[20260804-incubator-publishing.json](../../verification/evidence/20260804-incubator-publishing.json)

Closed at 2026-08-04T13:43:44.530003+00:00.
