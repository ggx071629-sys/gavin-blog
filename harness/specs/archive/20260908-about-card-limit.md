---
id: archive-20260908-about-card-limit
level: L2
summary: 关于页各支持十项并提供十种不同的几何动效图标
load_when:
  - task:20260908-about-card-limit
task_id: 20260908-about-card-limit
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录两个关于页可编辑集合各自的数量上限。
evidence_sha256: 144b509eadca37f4c1c8bded8a6f6f1124961abcec13100ea1e200846b078f27
state_history:
---

# 20260908-about-card-limit

Deterministic compressed record. The original active spec remains in Git history.

## Goal

能力领域与最近在做分别最多十项，保持现有自动保存、预览和显式发布流程。能力领域前十项使用互不相同的几何动效图标。

## Acceptance criteria

- AC-1: 两个区域各显示数量 / 10，允许新增至十项，满额禁止新增，删除后可再次新增。
- AC-2: API 接受各十项并保留顺序，独立拒绝任一区域的第十一项；保存不改变公开内容，发布后公开内容完整包含十项。
- AC-3: 十张能力卡片显示十种不同的 SVG 几何图标；鼠标悬停有短过渡反馈，离开平滑复位，减少动态效果与触屏不触发位移动画。

## Result

Verified and closed by the harness close command.

## Evidence

[20260908-about-card-limit.json](../../verification/evidence/20260908-about-card-limit.json)

SHA-256: `144b509eadca37f4c1c8bded8a6f6f1124961abcec13100ea1e200846b078f27`

Closed at 2026-09-08T14:20:23.200181+00:00.
