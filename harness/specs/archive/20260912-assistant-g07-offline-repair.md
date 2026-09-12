---
id: archive-20260912-assistant-g07-offline-repair
level: L2
summary: 修复真实正常教程改写误拒并准备空答复验
load_when:
  - task:20260912-assistant-g07-offline-repair
author: Codex
task_id: 20260912-assistant-g07-offline-repair
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明有限教程转述边界及空答提示改进尚需真实模型复验。
evidence_sha256: a1f2e70e9ccd6f98b7f64801e488a53f738ac682da21a3c97f1084093bea5d20
state_history:
---

# 20260912-assistant-g07-offline-repair

Deterministic compressed record. The original active spec remains in Git history.

## Goal

重放真实有据转述并保留否定、主体、限定和注入防护；明确提示如何回答相关教程，修正合成材料歧义，完成离线验收。Q2-06真实模型结果另行验收。

## Acceptance criteria

- AC-1: 两条真实有据正常回答离线重放可用，教程转述的否定、主体、限定、错误事实与错误标题反例仍拒绝。
- AC-2: 提示明确技术讨论可答及部分有据优先；空blocks仍失败；24个修订挑战满足原预算，正常对照有明确证据，准备和断网运行器不新增真实调用。
- AC-3: 既有事实语境、数量、讨论防护及提示历史预算回归通过；文档区分离线结果与未验证的真实空答质量。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-g07-offline-repair.json](../../verification/evidence/20260912-assistant-g07-offline-repair.json)

SHA-256: `a1f2e70e9ccd6f98b7f64801e488a53f738ac682da21a3c97f1084093bea5d20`

Closed at 2026-09-12T11:41:35.070401+00:00.
