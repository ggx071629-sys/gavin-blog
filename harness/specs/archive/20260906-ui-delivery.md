---
id: archive-20260906-ui-delivery
level: L2
summary: 修复全站集成发现的写作预览无障碍缺陷并验证发布候选
load_when:
  - task:20260906-ui-delivery
author: Gavin
task_id: 20260906-ui-delivery
status: compressed
documentation_impact: required
documentation_targets:
  - ui-fix/PHASE-7.md
documentation_reason: 记录集成缺陷、全站验证、默认关闭产物、恢复版本及不能由自动化抵扣的设备验收缺口。
evidence_sha256: 2640041e6cb3b9ab887ad1de9e01d4cb9dc1143f3eb218da0913b36b10a50d32
state_history:
---

# 20260906-ui-delivery

Deterministic compressed record. The original active spec remains in Git history.

## Goal

保持写作区受控目标稳定存在、预览正文仍按需创建，完成原有全量发布候选门禁和交付记录。

## Acceptance criteria

- AC-1: 三类新建和编辑页面初始 Markdown 状态及预览切换后，每个写作区域按钮的 aria-controls 均指向存在的唯一元素；预览内容按需创建，正文输入保留，隐藏预览不暴露重复内容。
- AC-2: 原有完整 release 门禁通过，包括生产页面无障碍矩阵和 Lighthouse 四项 90 门槛；全站业务回归、默认关闭和实际隔离问答保持，失败记录不被隐去。
- AC-4: 完整串行 release 的监督预算由 900 秒提高至 1200 秒以容纳实测约 15 分钟的前序步骤及助手组；保留原有超时终止、所有测试和质量阈值。
- AC-3: 阶段七文档记录真实覆盖、检查结果、默认关闭候选与恢复边界；第六阶段真机缺口保持待验收，不宣称生产资格或全阶段已完成。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-ui-delivery.json](../../verification/evidence/20260906-ui-delivery.json)

SHA-256: `2640041e6cb3b9ab887ad1de9e01d4cb9dc1143f3eb218da0913b36b10a50d32`

Closed at 2026-09-06T08:30:27.995799+00:00.
