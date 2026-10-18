---
id: archive-20260912-assistant-tutorial-relations
level: L2
summary: 保留教程风险解释关系并区分跨语言事实和支持引文
load_when:
  - task:20260912-assistant-tutorial-relations
author: Codex
task_id: 20260912-assistant-tutorial-relations
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明明确风险原因关系的有限核对与跨语言空答仍须实测的边界。
evidence_sha256: 175d45d912c70c2f44d2cb7731dae391992d8a0223bcfb49e2863a2f207d9007
state_history:
---

# 20260912-assistant-tutorial-relations

Deterministic compressed record. The original active spec remains in Git history.

## Goal

比较完整的教程归属和显式危险原因关系，保留主题、原因、否定和限定；提示明确跨语言答案与原语言支持引文。运行器支持精确选择少量诊断样例，仍消费同一累计账本。

## Acceptance criteria

- AC-1: 两轮正常教程转述以及新的中文危险原因正例通过；替换对象、原因、否定、条件与撤回反例拒绝。
- AC-2: 所有24个提示在原上限内，跨语言处理保留原文quote；空blocks仍失败。运行器精确选择样例，不自动重复或扩大选定范围，仍禁止未授权调用并保留失败。
- AC-3: 既有事实语境、数量、讨论与历史提示门禁通过，文档如实记录有限范围和真实质量待验证。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-tutorial-relations.json](../../verification/evidence/20260912-assistant-tutorial-relations.json)

SHA-256: `175d45d912c70c2f44d2cb7731dae391992d8a0223bcfb49e2863a2f207d9007`

Closed at 2026-09-12T11:53:16.916779+00:00.
