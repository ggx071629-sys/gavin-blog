---
id: spec-20260827-cancel-public-penpot-specs
level: L1
summary: 取消八个未完成的公开页面 Penpot 对齐规格，并从博客主项目开放规格列表移除
load_when:
  - task:20260827-cancel-public-penpot-specs
author: Gavin
task_id: 20260827-cancel-public-penpot-specs
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/decisions/20260827-cancel-public-penpot-specs.md
documentation_reason: 八个公开页面对齐任务不再推进，需要长期记录取消而非完成的语义、保留范围和未来重新立项边界。
state_history:
---

# Context

博客主项目当前有八个公开页面 Penpot 对齐规格处于 active：Chrome/Home、About、Archive、Articles、Books、Projects、Search 和 Article Detail。用户明确决定不再继续这些规格，并要求删除或归档。

Harness 的 `specs/archive/` 只表示经过验证并确定性关闭的 compressed task；这八项均未满足关闭条件：六项没有 task evidence，Chrome/Home 与 Article Detail 的本地 evidence 也因未提交源码漂移或风险门禁不匹配而无效。把它们直接 close 或手工移动到 compressed archive 会伪造完成状态。

当前主工作树存在与部分公开页面对齐相关的未提交 Web、E2E、截图、QA 文档和本地 evidence。取消规格不自动授权删除或提交这些用户资产，本任务必须在隔离 worktree 中只处理 Harness 生命周期和长期说明。

# Goal

以“取消、未完成”的语义从博客主项目开放规格列表移除八个公开页面 Penpot 规格，由 Git 历史和长期 ADR 保留原始边界与取消原因；不关闭旧任务、不删除现有 UI/QA 工作树修改，并保留未被用户列出的 Admin Login Penpot 规格继续处于 active。

# Non-goals

- 不继续实现、验证、恢复或关闭被取消的八个规格。
- 不在 `harness/specs/archive/` 为这八项创建 compressed 记录，不生成 passed evidence 或 `spec.completed` 事件。
- 不删除、回滚、提交或重写当前主工作树中的 Web、E2E、截图、QA 文档和本地 evidence。
- 不取消或修改 `20260827-admin-login-penpot-alignment`。
- 不修改 Penpot 文件、产品行为、API、数据、依赖、质量门槛或部署边界。
- 不把旧规格复制到新的常驻 `cancelled/` 目录；原文由 Git 历史保留。

# Acceptance criteria

- AC-1: 除本清理规格外，`harness/specs/active/` 和生成索引不再包含用户列出的八个 task ID；`20260827-admin-login-penpot-alignment` 保持 active，frozen 计数保持 0。
- AC-2: 主项目不为八个旧 task ID 新增 compressed spec、passed evidence 或 `spec.completed` 事件；长期 ADR 明确它们未完成、不可恢复、原文由 Git 历史保留。
- AC-3: 长期 ADR 明确当前未提交 UI/QA/evidence 不随规格删除，也不因此获得完成或可合入状态；未来若继续任何页面对齐，必须按当时产品基线创建新 task/spec。
- AC-4: 根 README 将公开页面 Penpot 批次标记为已取消，并准确说明仍保留的 Admin Login active spec；生成索引和全局 Harness 完整性检查通过。

# Risks

- 手工压缩或 close 会把未通过验收的工作伪装成已完成。
- 删除规格同时删除未提交代码会造成不可恢复的用户工作损失。
- 保留失效 evidence 而不解释保证等级，可能让后续维护者误认为任务曾经 verified。
- 清理时误删 Admin Login 规格会扩大用户明确列出的范围。

# Verification plan

- harness-integrity => AC-1, AC-2, AC-3, AC-4
