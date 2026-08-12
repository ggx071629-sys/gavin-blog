---
id: archive-20260812-documentation-impact-gate
level: L2
summary: 让 active spec 的文档影响在验证和关闭前形成确定性闭环
load_when:
  - task:20260812-documentation-impact-gate
author: Gavin
task_id: 20260812-documentation-impact-gate
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - harness/specs/_sdd/README.md
  - harness/specs/_sdd/template.md
  - harness/workflows/verify.md
  - harness/evolution/policy.md
  - harness/verification/README.md
documentation_reason: Harness 的文档迭代约束、事件边界和操作者流程发生变化。
state_history:
---

# 20260812-documentation-impact-gate

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立可执行的文档影响契约：每个非冻结 active spec 必须声明文档影响；需要更新文档的任务只有在声明目标已于 spec 基线之后提交、证据记录一致且工作区干净时才能验证和关闭。

## Acceptance criteria

- AC-1: 非冻结 active spec 必须声明 `documentation_impact`、单行 `documentation_reason`；`required` 必须包含安全的项目相对 Markdown 目标，`none` 不得包含目标。
- AC-2: 既有 frozen spec 无需补充文档影响字段，当前两个 frozen spec 的内容和生命周期状态保持不变。
- AC-3: task verify 对 `required` spec 检查每个目标存在于 HEAD、无未提交变更，并且在 spec 首次进入 Git 的提交之后发生过已提交变更；条件不满足时不执行产品 gate。
- AC-4: schema v2 task evidence 记录规范化的文档影响契约与目标指纹，close 会按当前 HEAD 重新验证契约、完成状态和指纹，过期证据不能关闭任务。
- AC-5: SDD 模板、验证 workflow、演进策略和根 README 说明人工维护边界以及 verify/close 门禁，不再暗示 `spec.completed` 事件会自动触发 README 迭代。
- AC-6: 自动化测试覆盖缺失或非法声明、路径穿越、冻结兼容、目标未更新、目标已更新、未提交漂移和证据漂移。

## Result

Verified and closed by the harness close command.

## Evidence

[20260812-documentation-impact-gate.json](../../verification/evidence/20260812-documentation-impact-gate.json)

Closed at 2026-08-12T05:02:53.269454+00:00.
