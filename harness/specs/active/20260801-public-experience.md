---
id: spec-20260801-public-experience
level: L1
summary: 启动第三阶段，补齐响应式公共导航、归档与关于页面，并建立无障碍交互基线
load_when:
  - task:20260801-public-experience
author: Gavin
task_id: 20260801-public-experience
status: verified
---

# Public experience

## Context

第一阶段核心文章闭环和第二阶段完整内容系统已经实现。产品基线将第三阶段定义为“视觉与工程质量完善”，同时既定导航中的归档与关于页面仍未落地，现有主导航在窄屏也会溢出。本任务以公共站点外壳为第一个可独立验证的纵向增量。

第三阶段后续按依赖拆分为：SEO 与内容发现输出（RSS、站点地图、规范链接、Open Graph、结构化数据），以及可执行质量门禁（WCAG AA、Lighthouse、类型、测试和构建阈值）。

## Goal

读者可以在桌面与移动设备上清晰地访问全部公共栏目、切换主题、使用键盘跳到正文，并通过归档与关于页面理解和浏览站点内容。

## Non-goals

- RSS、站点地图、规范链接、Open Graph 与结构化数据。
- 新增 API、数据库模型或内容管理能力。
- 部署平台、监控、公开评论、统计或联系表单。
- 本任务内承诺 Lighthouse 具体阻断阈值。

## Acceptance criteria

- 公共站点提供首页、文章、读书、项目、归档、关于和搜索入口；写作入口与公共内容导航保持视觉区分。
- 宽屏导航完整可见；窄屏使用带 `aria-expanded` 与明确标签的菜单按钮，打开后所有入口均可键盘访问，路由跳转后菜单关闭。
- 页面提供“跳到正文”链接；主内容区有稳定目标，焦点样式清晰可见。
- 主题切换按钮在桌面和移动导航均可使用，并继续由 color-mode 持久化偏好。
- `/archive` 按发布时间降序并按年份分组已发布文章；空数据时给出明确状态。
- `/about` 解释站点定位、内容范围和公开原则，不引入联系表单或统计。
- 动效尊重 `prefers-reduced-motion`，交互目标在触屏下保持可用尺寸。
- Vitest 覆盖归档分组与排序；Playwright 覆盖移动菜单、主题切换和跳到正文；类型检查与生产构建通过。

## Risks

- 服务端渲染与客户端主题偏好可能造成 hydration 差异，因此主题按钮文案保持稳定，不依赖首屏颜色状态。
- 移动菜单可能遮挡或困住键盘焦点，因此它保持普通文档流，并在导航后关闭，不实现不必要的模态焦点陷阱。
- 归档页复用公开文章 API，避免新增只服务展示层的数据边界；排序与分组在纯函数中保持确定性。

## Verification plan

- 先以 Vitest 描述跨年份文章的降序分组与输入不可变性，再实现最小纯函数。
- Playwright 在移动 viewport 验证菜单展开、全部导航项、路由后收起、主题切换与正文跳转。
- 执行现有 Vitest 回归、Nuxt typecheck 与生产构建。
- 运行 `python -m tools.harness index` 与 `python -m tools.harness verify 20260801-public-experience`，生成紧凑 evidence。

## Implementation record

- 公共头部现按宽窄屏分别提供完整导航与可展开菜单，归档、关于、搜索和写作入口均可触达，当前路由具有明确视觉状态。
- 默认布局增加键盘跳到正文入口；主题控件使用稳定无障碍名称，触屏目标尺寸与减少动态效果偏好由公共样式统一处理。
- `/archive` 复用公开文章 API，并通过无副作用纯函数按 UTC 发布时间降序、按年份分组。
- `/about` 已说明站点定位、内容类型与可复验、可修订、少噪音的公开原则。
- Vitest 4 个文件共 9 项、Nuxt typecheck、生产构建和 Playwright 2 条完整旅程均通过。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
