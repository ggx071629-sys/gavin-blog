---
id: archive-20260904-public-ui-refinement
level: L2
summary: 修复公开导航一致性、窄屏横溢与长文首屏比例，同时保留现有视觉身份和测试数据
load_when:
  - task:20260904-public-ui-refinement
author: Codex
task_id: 20260904-public-ui-refinement
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 统一移动导航顺序会更新 Web 边界文档中已明确记录的公开导航次序，其他产品边界保持不变
evidence_sha256: 6d6644ff24717ddc0f1b570f65cb186072fb23f0dfd0e816663d0a155c6fcf6b
state_history:
---

# 20260904-public-ui-refinement

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变公开内容、认证、路由和 Electric Editorial 视觉身份的前提下，修复导航、窄屏和长文首屏的已确认 UI 缺陷，并用真实响应式浏览器检查验证结果。

## Acceptance criteria

- AC-1: 桌面与移动公开导航从同一规范顺序呈现文章、项目、读书、归档、关于；移动端额外保留搜索，写作台入口和既有模态交互保持不变。
- AC-2: 首页在 320、360、375、390px 视口的 `scrollWidth` 不超过 `clientWidth`，标题标记仍完整可读且保留信号色强调。
- AC-3: 1440×900 的长文章 Hero 明显短于修复前的 32.5rem 首屏区，仍保留日期、元数据、标题、摘要/操作和长短文视觉差异，正文或章节轨在首屏可见。

## Result

Verified and closed by the harness close command.

## Evidence

[20260904-public-ui-refinement.json](../../verification/evidence/20260904-public-ui-refinement.json)

SHA-256: `6d6644ff24717ddc0f1b570f65cb186072fb23f0dfd0e816663d0a155c6fcf6b`

Closed at 2026-09-04T15:12:18.997748+00:00.
