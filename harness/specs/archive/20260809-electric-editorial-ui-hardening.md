---
id: archive-20260809-electric-editorial-ui-hardening
level: L2
summary: 硬化 Electric Editorial 语义设计系统并完成公开站、后台与知识孵化的全站最终验收
load_when:
  - task:20260809-electric-editorial-ui-hardening
author: Gavin
task_id: 20260809-electric-editorial-ui-hardening
status: compressed
restoration_source: "c3da86edaddec06b596dabaaad239f61d5e36319:harness/specs/active/20260809-electric-editorial-ui-hardening.md"
restored_at: 2026-08-11
---

# 20260809-electric-editorial-ui-hardening

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变任何 API 契约、数据库、公开／后台 URL、认证规则、业务状态机和页面信息架构的前提下，完成主项目 Electric Editorial 设计系统的语义化硬化，移除无消费者旧后台壳层和宽泛颜色兼容选择器，使公开站、非孵化后台、知识孵化在浅色／深色、桌面／移动端中直接由可审计的语义令牌和基础原语驱动，并以一次全站最终验证证明 UI 已达到后续独立迁移前的可交付状态。

## Acceptance criteria

- 建立明确的语义令牌分层：canvas／surface／surface-low／surface-high、ink／muted／faint、line／line-soft、primary／signal、focus，以及 info／success／warning／danger 各自的 background／border／ink。浅色和深色分别定义可读组合，不通过反转或 opacity 猜测状态色。
- --admin-warning-*、--admin-danger-* 等重复作用域变量收敛为单一语义来源；浏览器 theme-color、Nuxt loading indicator 和共享基础组件使用与当前主题体系一致的值，不再维护无说明的平行颜色常量。
- 全局 field、editor、surface、status、notice、button、action、dialog、empty、loading 和 code／diff 区域使用语义类或无领域基础组件表达意图。组件 API 不包含 slate、blue、rose 等视觉实现词，也不引入知识孵化专属类型。
- 删除 .incubator-workbench [class*="..."]、.admin-modal [class*="..."] 及其他依靠类名子串重映射颜色／圆角的兼容选择器；语义样式必须直接落在调用方或明确的基础原语上，不能用更高 specificity 的新补丁替代旧补丁。
- apps/web/pages/admin/**、后台专用组件和 Incubator 组件的模板不再使用 slate／gray／blue／purple／rose／red／amber／emerald／green 等原始调色板颜色工具类；布局、间距、尺寸和响应式工具类可以保留。对 Markdown 代码语法、用户内容渲染等确有隔离需要的例外必须位于专用样式作用域并写明原因。
- 新增可执行的静态防回归检查，至少阻止后台模板重新引入原始调色板颜色类、阻止 [class*="..."] 兼容选择器、阻止页面重新声明 layout: admin。检查不得误报普通内容文字或布局类。
- 在确认消费者仍为 0、Nuxt 构建和所有后台路由均正常后删除 apps/web/layouts/admin.vue；admin-core 保持唯一受保护后台主壳层。登录、草稿预览等既有例外模式保留，不为“唯一布局”强行套壳。
- 公开站继续严格保持 Stitch 已确认的浅／深色结构、排版、背景、边框、阴影和交互状态。共享令牌修改不得把阅读层变成后台密度，也不得使两套主题趋同为简单颜色翻转。
- 非孵化后台继续保持第三阶段高密度模式：列表、表单、编辑器、版本历史、媒体、危险操作和实时预览的信息层级不变；所有 hover、active、focus-visible、disabled、loading、success、warning、error、empty 和 conflict 状态可辨识且不只依赖颜色。
- 知识孵化继续保持第四阶段的来源→审计→草稿→发布证据链、五入口导航、筛选、批量操作、对话框、轮询、自动保存和任务状态；移除兼容 CSS 后 12 个路由与代表动态状态在视觉和行为上不回退。
- 酸性绿只用于满足对比要求的信号面、边缘或大号／高对比内容；正常小字在对应背景上至少 4.5:1，大号文字至少 3:1，UI 控件边界和焦点至少 3:1。错误、警告、成功、冲突和选中状态均附带文本、图标或结构语义。
- 所有交互具备明确 hover／active／focus-visible／disabled 状态；异步操作显示 loading 并防重复提交，完成和失败反馈可被辅助技术感知。错误放在相关字段或操作附近，并提供重试、修正或返回等真实恢复路径。
- 所有核心操作可键盘完成；跳到正文、桌面侧栏、移动抽屉、二级导航、分页、批量栏、编辑器、对话框和危险操作的焦点顺序、捕获、Esc 和返回焦点正确。触控目标至少 44×44px，相邻目标至少 8px，并尊重 prefers-reduced-motion。
- 390×844 下所有页面无 document 级横向溢出；不得使用全局 overflow-hidden 掩盖问题。Markdown 表格、代码、diff、原始内容和宽数据区只能在有键盘可达与可见边界的自身容器内受控滚动。
- 全站最终视觉矩阵覆盖 39 个页面族：1 个首页、10 个其他公开页面族、16 个非孵化后台路由、12 个知识孵化路由；每个执行 light/dark × 1440×1100/390×844，共 156 个基础视图。另覆盖 loading、empty、error、conflict、stale、partial success、running、cancel requested 和 destructive confirmation 等代表状态。
- 公开页面视觉验收继续对照对应 Stitch 原型；后台与知识孵化只按已声明的派生设计、真实字段和跨页一致性验收，不虚构不存在的原型。任何发现的不一致必须判断是实现错误、原型缺口还是明确例外，不能跳过。
- 39 个页面族的可达固定数据状态执行 axe WCAG 2.0／2.1 A/AA，自动扫描零违规；对动态对话框、移动菜单、轮询反馈、自动保存、错误恢复、局部滚动和状态非颜色依赖执行人工辅助技术检查。
- 保留全部既有 data-testid、E2E 闭环和可观察行为。若重构基础原语需要调整选择器，只能迁移到更稳定的语义／testid，不得删除断言、跳过用例、放宽 axe／Lighthouse 阈值或用截图更新掩盖真实回退。
- Nuxt 类型检查、全部 Vitest、生产构建、全部适用 Playwright E2E、全站质量测试、git diff --check 和 Harness 验证通过；生产首页 Lighthouse performance、accessibility、best-practices、SEO 均不低于 90。
- 生成第五阶段 application evidence，准确列出执行命令、测试数量、156 个基础视图、axe 范围、人工 Stitch／派生设计复核、Lighthouse 分数、边界检查和已知非阻断警告。截图、trace、Lighthouse 原始报告等重型产物只保存在本地。
- 最终 diff 不包含 my_blog_fork/、apps/api/、packages/contracts/、数据库迁移、两个冻结 spec 或冻结 checkpoint；主项目保持可独立运行，且未产生面向未来 fork 迁移的共享依赖。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-electric-editorial-ui-hardening.json](../../verification/evidence/20260809-electric-editorial-ui-hardening.json)

Closed at 2026-08-09T11:32:42.447695+00:00.
