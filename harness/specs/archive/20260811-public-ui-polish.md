---
id: archive-20260811-public-ui-polish
level: L2
summary: 收敛公开导航层级、文章摘要与阅读页提示和目录布局
load_when:
  - task:20260811-public-ui-polish
author: Codex
task_id: 20260811-public-ui-polish
status: compressed
state_history:
---

# 20260811-public-ui-polish

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不重排首页内容和不改公开内容数据的前提下，建立明确的公开导航层级并完善文章卡片与阅读页呈现。

## Acceptance criteria

- 桌面导航将搜索显示为图标加文字，文章仍为第一栏目且当前栏目高亮；写作台保留但使用低强调细边框。
- 移动端搜索保持独立 44×44 图标入口，移动导航中的写作台同步弱化。
- 首页“浏览全部文章”仍为主 CTA，其他公开导航页面保持一致。
- 文章摘要为空时不显示占位文案。
- Markdown 中独立的“提示”块呈现为现有令牌驱动的信息提示框。
- 桌面文章目录避免长中文标题单字孤行，正文阅读宽度不缩窄。
- 关于页图片不应用 grayscale 或降低饱和度的效果。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-public-ui-polish.json](../../verification/evidence/20260811-public-ui-polish.json)

Closed at 2026-08-12T02:23:33.410806+00:00.
