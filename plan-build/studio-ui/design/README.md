> 第二版设计文字基线的原文副本（2026-09-10）。原始预览、截图、参考图与资源仍位于 `.run/studio-design/`；此处的原型通过记录不代表生产验收。

# 写作台统一视觉设计稿

2026-09-10 · 第二版 · 参考图高保真优化 · 本地设计评审材料

本稿以用户提供的《Codex 图像 2026年9月10日 10_47_43.png》为视觉基准，统一 20 个写作台页面。内容为示例，所有保存、发布、删除与登录均为演示；没有接入业务 API，没有修改真实页面实现。

打开 `http://127.0.0.1:4180/#about` 查看新版关于页，`#assistant` 查看按参考图还原的问答助手。侧栏切换主页面，页内入口进入编辑、预览和版本历史。点击标题旁的“设计预览 · 演示数据”打开设计工具，查看全部页面或切换空态、读取失败、保存冲突。侧栏底部切换主题。

问答助手已改为真实 HTML 界面，支持演示试问、开放/暂停、修改预算、费用明细、同步重试及高级维护。全部使用本机示例数据，不连接业务 API。

## 页面覆盖

| 页面 | 设计入口 | 当前产品路径 / 模式 |
| --- | --- | --- |
| 文章列表 | #articles | /admin/articles |
| 新建文章 | #article-new | /admin/articles/new |
| 编辑文章 | #article-edit | /admin/articles/[id]/edit |
| 文章预览 | #article-preview | /admin/articles/[id]/preview |
| 文章版本历史 | #article-revisions | /admin/articles/[id]/revisions |
| 读书列表 | #books | /admin/books |
| 新建读书笔记 | #book-new | /admin/books/new |
| 编辑读书笔记 | #book-edit | /admin/books/[id]/edit，预览在编辑器内 |
| 项目列表 | #projects | /admin/projects |
| 新建项目 | #project-new | /admin/projects/new |
| 编辑项目 | #project-edit | /admin/projects/[id]/edit，预览在编辑器内 |
| 个人名片 | #profile | /admin/profile |
| 关于页 | #about | /admin/about |
| 关于页预览 | #about-preview | /admin/about/preview |
| 关于页版本历史 | #about-revisions | /admin/about/revisions |
| 栏目与标签 | #taxonomy | /admin/taxonomy |
| 媒体库 | #media | /admin/media |
| 回收站与迁移 | #content | /admin/content |
| 登录 | #login | /admin/login |
| 问答助手管理 | #assistant | /admin/assistant，对齐选定参考图的可交互设计 |

## 统一规范

- 浅色：主画布 `#FFFFFF`，侧栏 `#F1F5FA`，选中背景 `#E3ECFC`，正文 `#080C15`，次级文字 `#48587B`，主操作 `#005DFF`，细分隔线 `#DBE3F0`。
- 深色：主画布 `#10141E`，侧栏 `#151B28`，正文 `#F0F3FA`，主操作 `#7DAAFF`。深浅模式共用布局与语义。
- 桌面 254px 侧栏、36px 主内容边距；标准标题 36px，助手标题 38px，导航 18px，分区标题 20–22px，正文 15–18px，元信息 13px。中文 Noto Sans SC，西文 Inter，字体均为本地文件。
- 图标使用 Tabler Outline / Filled；圆形聊天图标使用 Lucide。保留对应开源许可。按钮最小触控高度 44px，主要按钮 48–54px。
- 助手基准视口 1487×1058：主内容从 x=290 开始，预算条从 x=632 开始，宽 683px；以参考图的分区、留白和视觉层级为准。
- 运营设置沿用“左侧说明—中间内容—右侧操作”；列表沿用开放行与细分隔线；编辑器为正文提供独立白色工作面，设置放到右侧。
- 危险操作收进低频入口并单独确认。草稿已保存、有未发布修改、正式发布保持不同语义。
- 手机上侧栏收起，设置与正文上下排列；保留清晰的主操作，不压缩成窄表格。

## 设计判断与待实现边界

视觉一致不代表所有页面都使用同一种布局。媒体保留图片选择场景，编辑器保留写作空间，表单保留字段分组；将所有内容都改成助手概览的三栏行会降低编辑效率。

列表搜索、发布状态筛选、媒体类型筛选属于本稿提出的交互。正式实现时需要对应的服务端查询和分页契约，不能只过滤当前页或把示例总数当真实统计。编辑器的自动保存、离页保护、发布前保存屏障与版本冲突处理必须延续现有实现；设计稿不替代这些行为验收。

本稿不新增批量发布、自动发布、项目版本历史、读书版本历史或账户管理。图文只采用本地示例，媒体页面复用仓库已有的分享封面，未上传素材。

## 交付文件

- `index.html`、`style.css`、`fidelity.css`、`app.js`：可运行设计稿，无需安装依赖。
- `assets/`：本地字体与图标、既有分享封面和用户选定的问答助手参考截图。
- `screenshots/`：20 个画面的桌面浅色稿，另含文章深色桌面稿，以及重点页面的深浅手机稿。
- `design-qa.md`、`qa-results.json`：视觉对照、240 组主题/尺寸检查和交互检查结果。
- `compare.html`：参考图与浏览器实拍并列对照；详细截图在 `screenshots/comparison-*.png`。

重启预览：在本目录执行 `python -m http.server 4180 --bind 127.0.0.1`。
