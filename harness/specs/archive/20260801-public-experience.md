---
id: archive-20260801-public-experience
level: L2
summary: 启动第三阶段，补齐响应式公共导航、归档与关于页面，并建立无障碍交互基线
load_when:
  - task:20260801-public-experience
author: Gavin
task_id: 20260801-public-experience
status: compressed
---

# 20260801-public-experience

Deterministic compressed record. The original active spec remains in Git history.

## Goal

读者可以在桌面与移动设备上清晰地访问全部公共栏目、切换主题、使用键盘跳到正文，并通过归档与关于页面理解和浏览站点内容。

## Acceptance criteria

- 公共站点提供首页、文章、读书、项目、归档、关于和搜索入口；写作入口与公共内容导航保持视觉区分。
- 宽屏导航完整可见；窄屏使用带 `aria-expanded` 与明确标签的菜单按钮，打开后所有入口均可键盘访问，路由跳转后菜单关闭。
- 页面提供“跳到正文”链接；主内容区有稳定目标，焦点样式清晰可见。
- 主题切换按钮在桌面和移动导航均可使用，并继续由 color-mode 持久化偏好。
- `/archive` 按发布时间降序并按年份分组已发布文章；空数据时给出明确状态。
- `/about` 解释站点定位、内容范围和公开原则，不引入联系表单或统计。
- 动效尊重 `prefers-reduced-motion`，交互目标在触屏下保持可用尺寸。
- Vitest 覆盖归档分组与排序；Playwright 覆盖移动菜单、主题切换和跳到正文；类型检查与生产构建通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-public-experience.json](../../verification/evidence/20260801-public-experience.json)

Closed at 2026-08-01T16:43:44.618210+00:00.
