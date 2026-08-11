---
id: spec-20260811-harness-close-signal-integrity
level: L1
summary: 消除关闭流程的空 Evolution proposal，并保证压缩归档保留关键章节
load_when:
  - task:20260811-harness-close-signal-integrity
author: Codex
task_id: 20260811-harness-close-signal-integrity
status: active
---

# Context

已确认的 `workflow.friction_confirmed` 事件显示两类关闭生命周期缺陷：普通 spec close 无条件生成缺少证据和变更内容的 proposal，43 份此类记录最终全部无行动；同时压缩器只识别 H2 标题，导致 43 个归档中的 23 个把实际存在的 Goal 与 Acceptance criteria 写成 `Not recorded.`。

# Goal

让确定性 close 只记录完成事件而不制造空 proposal，并在删除 active spec 前可靠提取和验证 H1/H2 关键章节，使新归档始终保留非空 Goal 与 Acceptance criteria。

# Non-goals

- 不修改产品代码、API、数据模型或发布行为。
- 不自动回写 23 个历史压缩归档；原始 active spec 继续由 Git 历史保存。
- 不修改 `AGENTS.md`，不恢复或实施两个冻结 GitHub spec。
- 不取消显式 Evolution event 生成 proposal 的能力。

# Acceptance criteria

1. `python -m tools.harness close <task_id>` 继续生成 archive、evidence、索引和 `spec.completed` event，但默认不生成同名 proposal。
2. `python -m tools.harness emit-event ...` 继续为显式、带 reason 的允许事件生成 proposal。
3. 压缩器精确支持 H1 或 H2 的 Goal 与 Acceptance criteria，不把 H3 或正文中的相似文本当作章节。
4. Goal 或 Acceptance criteria 缺失、仅空白时，close 在删除 active spec 前失败并回滚，不留下 archive、event、proposal 或错误 evidence。
5. SDD template 与 lifecycle guidance 明确规范章节结构和关闭前完整性要求。
6. 自动化测试覆盖 H1/H2、缺失/空章节、默认 close 无 proposal、显式 event 有 proposal及回滚语义。
7. Harness verify 与完整 `quality:release` 通过；关闭本 spec 时实际证明新行为不生成空 `spec.completed` proposal。

# Risks

- 事件与 proposal 写入解耦若回滚不完整，可能留下孤立文件；测试必须覆盖失败清理。
- 标题正则若过宽会误取嵌套章节，若过窄会继续丢失合法结构。
- 新完整性检查可能阻止结构不规范的旧 active spec 关闭；模板和错误信息必须给出明确修复方式。

# Verification plan

1. 先添加会在当前实现失败的 Harness 单元/集成测试，再实施最小修复。
2. 运行 `python -m pytest verification/tests` 和 `python -m tools.harness verify 20260811-harness-close-signal-integrity`。
3. 从仓库根运行完整 `npm run quality:release`，确认控制面变化未破坏发布门禁。
4. 提交实现后运行确定性 close；确认只新增 completion event，没有 completion proposal。
5. 将已接受的 Evolution proposal 更新为 `applied` 并记录验证结果。
