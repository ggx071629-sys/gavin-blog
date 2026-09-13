---
id: archive-20260808-electric-editorial-admin-core
level: L2
summary: 以 Electric Editorial 共享令牌重构非孵化管理后台，并保留全部认证与内容工作流
load_when:
  - task:20260808-electric-editorial-admin-core
author: Gavin
task_id: 20260808-electric-editorial-admin-core
status: compressed
restoration_source: "c3da86edaddec06b596dabaaad239f61d5e36319:harness/specs/active/20260808-electric-editorial-admin-core.md"
restored_at: 2026-08-11
---

# 20260808-electric-editorial-admin-core

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变 API 契约、数据库、公开 URL、后台 URL、认证规则、内容状态机和自动保存／发布一致性屏障的前提下，完成 16 个非孵化后台路由的 Electric Editorial 双主题 UI 重构，建立高密度、可扫描、移动可用且满足 WCAG AA 的后台壳层、列表、表单、编辑器、版本历史和工具页面。

## Acceptance criteria

- 新的非孵化后台壳层在桌面采用紧凑侧边导航与实用工具区，在移动端收敛为可键盘操作的抽屉／菜单；保留文章、读书、项目、个人名片、栏目与标签、媒体、回收站与迁移、知识孵化、查看站点和退出的现有目标，并提供当前项语义、跳到正文和明确焦点。
- 后台壳层与登录页支持浅色／深色独立设计，复用 `--ee-*` 基础令牌；深色不是简单反转，浅色酸性绿不用于未达到 4.5:1 的小号文字。状态、错误、警告和成功不只依赖颜色表达。
- 登录页保留用户名、密码、CSRF 获取、限流错误、错误凭据反馈、hydration 禁用和登录后跳转；两种主题均满足 WCAG AA，密码管理器所需 autocomplete 不回归。
- 文章、项目和读书列表使用同一高密度列表语法，保留真实状态、版本和现有操作；桌面易扫描，390px 下重排为单列操作区且整页无水平溢出。不得为了视觉效果新增不存在的筛选、数据列或统计。
- 三类新建页复用统一页面标题、表单区、帮助／错误反馈和操作栏，保留现有字段顺序、输入类型、最大长度、slug 同步、默认 Markdown、关联数据与成功跳转。
- `ArticleEditor`、`ProjectEditor`、`BookNoteEditor` 建立一致的编辑工作台：桌面双栏呈现编辑与真实预览，移动端提供单列且可到达的编辑／预览顺序；自动保存状态、冲突警告、媒体插入、发布按钮、禁用条件和 `queue.flush()` 发布屏障保持原行为。
- 文章草稿预览明确展示“未公开”状态并保留返回编辑；渲染继续使用真实 `MarkdownArticle`，视觉上与公开阅读层同源但不能混淆为已发布页面。
- 版本历史页保留发布修订分页、当前修订、孵化来源链、快照详情、差异、回滚资格、确认和错误／成功状态；长 Markdown 与 diff 在桌面和移动端均可读，不造成页面级水平溢出。
- 栏目／标签、媒体、回收站与迁移、个人名片四类工具页分别形成一致的表单、资产、危险操作和设置预览模式；原有 CRUD、上传、复制、导入导出、恢复／永久删除、技能排序、公开开关、冲突与未保存离开提醒全部保留。
- 后台共用组件和样式使用语义类或语义令牌替代页面散落的 slate／blue／purple 与不一致圆角；公开博客和后台共享基础令牌，但后台不得直接复用只适合阅读的页面结构，也不得建立孵化依赖。
- 正文／表单文字在两种主题满足 WCAG AA；所有核心操作可由键盘完成，焦点顺序与视觉顺序一致，焦点环清晰，表单具备可见标签和就近错误，触控目标至少 44×44px，并尊重 `prefers-reduced-motion`。
- 16 个非孵化路由均执行 light/dark × 1440×1100/390×844 四象限的无溢出与视觉检查；每个页面族至少一个固定数据代表页执行 axe WCAG 2.0/2.1 A/AA，自动扫描零违规。
- `/admin/incubator`、`/admin/incubator/inbox` 和一个孵化详情页保留现有布局与可访问性基线；实现 diff 不得包含 `pages/admin/incubator/**` 或两个 Incubator 组件。
- 保留既有 `data-testid` 和高价值闭环；将依赖 `.editor-grid > div` 的脆弱测试定位改为稳定语义／testid 时，不改变可观察行为。
- Nuxt 类型检查、全部 Vitest、生产构建、适用 Playwright E2E、质量门禁、`git diff --check` 和 Harness 验证通过；首页 Lighthouse 四项继续不低于 90，后台页面维持 `noindex,nofollow`。

## Result

Verified and closed by the harness close command.

## Evidence

[20260808-electric-editorial-admin-core.json](../../verification/evidence/20260808-electric-editorial-admin-core.json)

Closed at 2026-08-09T11:32:09.241221+00:00.
