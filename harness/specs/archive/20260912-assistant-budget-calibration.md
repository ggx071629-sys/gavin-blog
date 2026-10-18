---
id: archive-20260912-assistant-budget-calibration
level: L2
summary: 离线分解提示预算并与官方 tokenizer 和已保存 usage 校准
load_when:
  - task:20260912-assistant-budget-calibration
author: Codex
task_id: 20260912-assistant-budget-calibration
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录当前最小输入、独立开销及官方 tokenizer 校准的适用范围，避免仅增大额度。
evidence_sha256: e902434cae6a978db10e70a64525f795c0b6be07462a7a6e9e609b97e2f94e79
state_history:
---

# 20260912-assistant-budget-calibration

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立只输出数值和来源摘要的离线预算报告，分别核对固定指令/协议、当前问题、历史、候选与选中证据、回答文本、supports 和 JSON。找出有限可答样例的精确输入边界，并对官方来源计数与实际 usage 误差作可复核校准。

## Acceptance criteria

- AC-1: 报告区分 UTF-8 字节、保守估算与 tokenizer 计数；输入各组成项可核算，候选与选中证据分别记录，空答、长 supports 和非法结构不会被算作有效可答输出。
- AC-2: 有限中英文可答样例在输入/上下文的精确边界通过、少一单位拒绝；保持证据完整、历史裁剪及原最坏费用预留。
- AC-3: 官方 tokenizer 数据校验 SHA 后仅作为数据读取，离线样例与已保存模型 usage 校准有哈希/范围来源；不联网或发送模型调用，不把未知模型版本和模板差异当作已验证。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-budget-calibration.json](../../verification/evidence/20260912-assistant-budget-calibration.json)

SHA-256: `e902434cae6a978db10e70a64525f795c0b6be07462a7a6e9e609b97e2f94e79`

Closed at 2026-09-12T13:00:50.894779+00:00.
