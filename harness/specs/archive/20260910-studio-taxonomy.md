---
id: archive-20260910-studio-taxonomy
level: L2
summary: 栏目标签开放列表、编辑与关联约束提示
load_when:
  - task:20260910-studio-taxonomy
task_id: 20260910-studio-taxonomy
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
evidence_sha256: ee66bd8a9af03e8ceec9c316902d400a70a830ce0dfc1bb5d582c2aa1c91cb9e
state_history:
---

# 20260910-studio-taxonomy

Deterministic compressed record. The original active spec remains in Git history.

## Goal

栏目标签开放列表、编辑与关联约束提示

## Acceptance criteria

- AC-1: 栏目与标签有清晰列表、数量和独立编辑区，键盘焦点、长文本及双主题响应式可用。
- AC-2: 真实新增、编辑和删除保留服务端关联约束与失败反馈，取消编辑不修改数据。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-taxonomy.json](../../verification/evidence/20260910-studio-taxonomy.json)

SHA-256: `ee66bd8a9af03e8ceec9c316902d400a70a830ce0dfc1bb5d582c2aa1c91cb9e`

Closed at 2026-09-10T11:12:26.071080+00:00.
