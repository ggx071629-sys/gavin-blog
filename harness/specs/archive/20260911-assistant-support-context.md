---
id: archive-20260911-assistant-support-context
level: L2
summary: 高风险支持句核对保留原始来源中的周围语境
load_when:
  - task:20260911-assistant-support-context
author: Codex
task_id: 20260911-assistant-support-context
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确支持原文不能裁掉前后语境，仍不保证通用语义蕴含。
evidence_sha256: da4d1d728b74f70a24f16524d8411f41b1099f79aea85832cdf86f3dbedafe44
state_history:
---

# 20260911-assistant-support-context

Deterministic compressed record. The original active spec remains in Git history.

## Goal

高风险断言使用 quote 在原文中的完整周围句子检查，不能仅根据模型自选短引文断定有据。

## Acceptance criteria

- AC-1: 谣言/否定上下文中的获奖短引文不能发布为真实奖项；已有自述、部分回答、主体/数字/跨块代表例保持正确预期，内部 quote 不改写或公开。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-support-context.json](../../verification/evidence/20260911-assistant-support-context.json)

SHA-256: `da4d1d728b74f70a24f16524d8411f41b1099f79aea85832cdf86f3dbedafe44`

Closed at 2026-09-11T15:12:01.146826+00:00.
