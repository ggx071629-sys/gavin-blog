---
id: archive-20260808-electric-editorial-ui
level: L2
summary: 以 Stitch Electric Editorial 原型重构主项目公开 UI，并建立可复用的双主题视觉基础
load_when:
  - task:20260808-electric-editorial-ui
author: Gavin
task_id: 20260808-electric-editorial-ui
status: compressed
restoration_source: "c3da86edaddec06b596dabaaad239f61d5e36319:harness/specs/active/20260808-electric-editorial-ui.md"
restored_at: 2026-08-11
---

# 20260808-electric-editorial-ui

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变 API、数据、公开 URL、认证和业务状态的前提下，建立共享语义令牌和可访问的公开站点壳层，并严格迁移首页、文章卡片及个人名片，使它们可在浅色／深色和桌面／移动四种组合下运行与验收。

## Acceptance criteria

- 浅色和深色使用同一组语义令牌名称，但分别定义颜色、背景、边框、文字层级、圆角、阴影和交互状态。
- 公开导航、移动菜单、主题切换、跳到正文和页脚保持可用；公开 URL 不变。
- 首页布局、品牌字标、编辑式网格、最近文章区和个人名片与对应 Stitch 原型的结构和视觉层级一致，同时继续使用真实 API 数据。
- `ArticleCard` 与 `ProfileCard` 保留现有可观察业务行为与测试选择器。
- 390px 移动端无横向溢出，触控目标不小于 44px，键盘焦点可见，并尊重减少动态效果偏好。
- 首页在浅色／深色、桌面／移动四种组合下具有可重复的 Playwright 截图证据，并通过适用的 axe WCAG A/AA 检查。
- Web 类型检查、Vitest、生产构建及相关 Playwright 检查通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260808-electric-editorial-ui.json](../../verification/evidence/20260808-electric-editorial-ui.json)

Closed at 2026-08-09T11:31:27.974219+00:00.
