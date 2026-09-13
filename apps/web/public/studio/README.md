# Studio 资源与主题边界

本目录提供写作台静态图标及许可证；页面实现位于 [pages/admin](../../pages/admin/)，共用组件位于 [components](../../components/)，当前整体职责见 [Web README](../../README.md)。这里不是独立应用或一套演示后台。

## 资源来源

[icons/](icons/) 保留选定设计使用的 SVG 及 Tabler MIT、Lucide ISC 许可证。[StudioIcon](../../components/StudioIcon.vue) 通过 currentColor CSS mask 显示图标；装饰图标不提供重复读屏内容，控件名称由可见文字或 aria-label 提供。

字体由 [Nuxt 配置](../../nuxt.config.ts) 中的 fontsource 依赖构建并自托管，后台正文/标题使用 Inter 与 Noto Sans SC，不依赖设计稿的外部字体服务。字体许可证随对应 fontsource 包分发。

## 当前主题与布局

[studio.css](../../assets/css/studio.css) 在 `.admin-core-shell`、`.admin-login-shell` 和 Teleport 的 `.admin-modal-backdrop` 上定义 `--studio-*`。这些颜色变量继承全站 `--ee-*`，浅深主题由同一 color-mode 偏好控制；当前没有原设计稿那套独立硬编码后台配色。字体、圆角和布局仍可在后台根节点内设置。新增 Teleport 容器需显式接入该主题边界。

后台外壳、移动抽屉、主题切换和退出分别由 [admin-core 布局](../../layouts/admin-core.vue)、[AdminCoreNavigation](../../components/AdminCoreNavigation.vue) 等组件负责。断点和尺寸以当前 CSS 与布局媒体查询为准；抽屉保留 Escape、焦点管理、路由/断点清理和滚动锁释放。

内容列表共用 StudioContentList，写作区共用 WritingWorkspace，管理弹窗共用 AdminDialog。页面继续调用真实 API，保留保存屏障、版本冲突、失败重试与显式发布/回滚确认；静态资源不能替代业务状态。

## 历史设计与验证

第二版设计文字基线见 [设计资料](../../../../plan-build/studio-ui/design/README.md)。六阶段实施记录、历史截图说明与当时的尺寸/对比度测量见 [主计划](../../../../plan-build/studio-ui/STUDIO-UI-PLAN.md) 和 [最终阶段](../../../../plan-build/studio-ui/STUDIO-UI-PHASE-6.md)。历史通过记录只证明所绑定版本，不自动证明后续主题或页面改动通过。

主题变更需同步检查 [studio-theme.spec.ts](../../tests/e2e/studio-theme.spec.ts)；其他布局、弹窗和内容流程由对应 E2E 场景覆盖。维护本说明时只更新现行资源来源、许可证、主题与消费边界，阶段过程继续放在 plan-build。
