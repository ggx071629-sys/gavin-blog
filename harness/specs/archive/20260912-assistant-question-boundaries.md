---
id: archive-20260912-assistant-question-boundaries
level: L2
summary: Q4-04 页面优先及未核验的全量和时效请求
load_when:
  - task:20260912-assistant-question-boundaries
author: Codex
task_id: 20260912-assistant-question-boundaries
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 明确页面候选优先条件、全量与时效请求的能力边界。
evidence_sha256: 8daff69894c6612eb35885e9313974cb800fa09fbd890990ee3c3245506abbe2
state_history:
---

# 20260912-assistant-question-boundaries

Deterministic compressed record. The original active spec remains in Git history.

## Goal

明确页面指代或已解析来源才优先该页；可识别的全量/全局时效请求明确未核验，局部事实仍可回答。

## Acceptance criteria

- AC-1: 当前路径仅在明确页面指代或成功解析来源时优先；无关新题不提升当前页。
- AC-2: 明确全量计数/清单和最新/当前任职请求分别返回未核验专用终态，零Chat和Embedding；普通局部清单、技术计数和历史事实不被这些规则拦截。
- AC-3: 浏览器分别展示并恢复完整性/时效未核验提示，不称证据不存在或生成错误。
- AC-4: 文档记录规则边界、片段限制与仍未支持的通用能力。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-question-boundaries.json](../../verification/evidence/20260912-assistant-question-boundaries.json)

SHA-256: `8daff69894c6612eb35885e9313974cb800fa09fbd890990ee3c3245506abbe2`

Closed at 2026-09-12T15:09:08.869516+00:00.
