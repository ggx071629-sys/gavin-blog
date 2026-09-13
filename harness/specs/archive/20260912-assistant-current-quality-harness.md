---
id: archive-20260912-assistant-current-quality-harness
level: L2
summary: Q5 固定当前语料评测输入与受累计授权约束的运行器
load_when:
  - task:20260912-assistant-current-quality-harness
author: Codex
task_id: 20260912-assistant-current-quality-harness
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 说明固定题集、当前语料、独立/调试划分、授权和实际质量局限。
evidence_sha256: d1320b0f8325927db8d3dd1bb6657aede66697473c0c41c97c8e7270c273e437
state_history:
---

# 20260912-assistant-current-quality-harness

Deterministic compressed record. The original active spec remains in Git history.

## Goal

固定当前语料题集与可复核期望，建立默认不付费、沿用原签名账本且拒绝漂移的评测运行器，并验证浏览器自动化范围。

## Acceptance criteria

- AC-1: 题集区分debug/evaluation，来源版本和全文摘要固定，期望定位到原文；缺失来源、占位事实及独立人工复核未测范围显式记录。
- AC-2: 默认prepare不调用Chat/写费用；实际调用先复核同一授权/累计余额与语料，逐次预留/结算，未知结果保守结算后停止，拒绝额度/输入漂移。
- AC-3: 浏览器自动化验证恢复、移动布局/焦点、键盘和a11y可执行范围；人工读屏及实体设备验证保留未验证。
- AC-4: 真实输出/问题只保存在忽略的本地data，提交紧凑结果和限制；不把替身或离线准备当真实模型质量。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-current-quality-harness.json](../../verification/evidence/20260912-assistant-current-quality-harness.json)

SHA-256: `d1320b0f8325927db8d3dd1bb6657aede66697473c0c41c97c8e7270c273e437`

Closed at 2026-09-12T15:30:13.612921+00:00.
