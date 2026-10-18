---
id: archive-20260911-assistant-evidence-budget
level: L2
summary: 按模型剩余输入空间选取可引用的本站证据
load_when:
  - task:20260911-assistant-evidence-budget
task_id: 20260911-assistant-evidence-budget
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录证据输入预算、完整切片选择与引用校验边界。
evidence_sha256: b634d3ad654552e2101cceebd4bc776dfcc1c863813351e3f139dde9b9d6bf93
state_history:
---

# 20260911-assistant-evidence-budget

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在现有输入和每日费用上限内，确定性选择完整证据，让普通问题进入回答生成，并只接受实际发送证据的引用。

## Acceptance criteria

- AC-1: 完整证据可容纳时保持原排序；超限先裁剪历史，再在检索候选内按来源轮转选择能装下的完整切片，跳过过大项并去除同来源同正文重复项，输入及输出预留均不超限。
- AC-2: 生成与已成功attempt恢复均将实际选中证据传给后续引用校验；未选中的别名不能被采纳。没有任何证据能装下时仍返回明确输入超限。
- AC-3: 本机既有代表问题在原8000上限内构建成功；不调用真实Chat、不修改配置和费用；文档同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-evidence-budget.json](../../verification/evidence/20260911-assistant-evidence-budget.json)

SHA-256: `b634d3ad654552e2101cceebd4bc776dfcc1c863813351e3f139dde9b9d6bf93`

Closed at 2026-09-11T03:42:34.968504+00:00.
