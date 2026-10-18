---
id: archive-20260912-assistant-technical-text
level: L2
summary: 允许有依据的比较符号和数组表达并保留输出安全
load_when:
  - task:20260912-assistant-technical-text
author: Codex
task_id: 20260912-assistant-technical-text
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 说明纯文本技术表达与禁止HTML/模型自造引用的边界。
evidence_sha256: cd372a47bbc19863b8d69d9a87459eb3bf5db1e5db07f624f59084a493c0cecd
state_history:
---

# 20260912-assistant-technical-text

Deterministic compressed record. The original active spec remains in Git history.

## Goal

允许有支持的比较符号、数组下标与简单类型参数；保留HTML、危险链接、图片及游离引用标记的拒绝，并保留来源地址转标题行为。

## Acceptance criteria

- AC-1: 有依据的中英文比较、数组和简单泛型可通过，技术表达中的数字变化仍被拒绝；浏览器数组下标保留为纯文本，真实末尾引用仍闭合到来源。
- AC-2: script/HTML、危险链接、Markdown图片、javascript和手写引用标记仍拒绝；受绑定来源地址继续只显示正确标题，引用闭合与不支持陈述保护不回退。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-technical-text.json](../../verification/evidence/20260912-assistant-technical-text.json)

SHA-256: `cd372a47bbc19863b8d69d9a87459eb3bf5db1e5db07f624f59084a493c0cecd`

Closed at 2026-09-12T10:21:36.076543+00:00.
