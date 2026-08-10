---
id: spec-20260809-mobile-accessibility-assets
level: L1
summary: 建立可访问移动后台抽屉、合格触控目标与自托管字体边界
load_when:
  - task:20260809-mobile-accessibility-assets
author: Codex
task_id: 20260809-mobile-accessibility-assets
status: active
---

# Context

批次 6 覆盖 AUD-13、AUD-14、AUD-16：移动后台抽屉具有遮罩和滚动锁，却没有 modal dialog 语义、背景 inert 或焦点循环；Profile 技能图标按钮实际触控区域约 16–19px；Inter、Hanken Grotesk 与 JetBrains Mono 仍在运行时依赖 Google Fonts。

# Goal

把移动导航明确实现为键盘和辅助技术一致的 modal drawer；让相邻小图标按钮满足 WCAG 2.2 触控目标基线；把实际使用字体及字重作为构建资产自托管，断网时不产生外部字体请求或布局溢出。

# Non-goals

- 不重做后台导航视觉、信息架构或桌面 sidebar。
- 不处理批次 7 的日期、分页、Mermaid、SEO 等边界问题。
- 不引入部署 CDN、字体服务或新的运行时第三方依赖。
- 不预建后续 active spec。

# Acceptance criteria

1. 移动抽屉具有 `role=dialog`、`aria-modal=true`、可见标题/label，打开后初始焦点进入抽屉，Tab/Shift+Tab 在抽屉可用控件内循环，Escape 和遮罩关闭并把焦点返回触发按钮。
2. 抽屉打开时主内容及移动 header 的非抽屉部分不可聚焦/交互；路由变化、跨桌面 breakpoint 与组件卸载均释放 body lock 和 inert 状态。
3. Profile 技能上移、下移、删除按钮及同组相邻图标按钮具有至少 32×32 CSS px 的命中区；移动验证目标优先达到 44×44，禁用状态不缩小布局。
4. Inter 400/500/600、Hanken Grotesk 700/800、JetBrains Mono 400/500/600 的 WOFF2 构建资产本地提供，`font-display` 明确；删除 Google Fonts stylesheet 与 preconnect。
5. CSP Report-Only 的 font/style 来源同步收敛到 self；浏览器网络记录无 `fonts.googleapis.com` 或 `fonts.gstatic.com` 请求。
6. 390×844、375×667 与移动横屏完成焦点循环、背景不可聚焦、Escape/返回焦点；200% 文本缩放不遮挡关闭按钮和末项导航，断网/字体失败 fallback 不产生水平溢出。

# Risks

- `inert` 与条件渲染组合若清理不完整会在关闭后留下不可交互页面；必须集中设置并在所有退出路径恢复。
- 焦点 trap 必须跳过 disabled/hidden 元素并处理控件动态变化，不能只硬编码首尾链接。
- 字体包会增加仓库依赖与构建体积；只引入实际字族/字重，避免全量语言/样式资产。
- WCAG 2.2 2.5.8 的 24px 最低与项目 32/44px 更严格目标需区分；几何测试采用本 spec 的更严格目标。

# Verification plan

1. Vitest/静态契约覆盖 dialog/inert/focus trap 清理和图标按钮尺寸类，字体配置不含 Google URL。
2. Playwright 在 390×844、375×667、844×390 验证正反向 Tab 循环、背景不可聚焦、Escape 与焦点返回；逐个断言技能按钮 bounding box。
3. 生产浏览器拦截/记录字体请求，证明无 Google Fonts，并在离线/字体失败与 200% 字号下检查无水平溢出。
4. 运行 Web typecheck/unit/build、相关 quality/E2E 及完整 `npm run quality:release`。
5. 从 `harness/` 运行 verify；全部通过后用确定性 close 命令归档本 spec。
