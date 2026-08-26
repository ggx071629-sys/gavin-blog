---
id: spec-20260825-article-detail-penpot-alignment
level: L1
summary: 在现有公开文章阅读契约上，对齐 Penpot Article Long/Short 展示变体并修复代码复制与移动表格溢出
load_when:
  - task:20260825-article-detail-penpot-alignment
author: Gavin
task_id: 20260825-article-detail-penpot-alignment
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开文章详情的 Long/Short 判定、Hero、720/680 阅读宽度、代码复制和移动表格滚动边界发生用户可见变化，需要同步 Web 边界说明。
state_history:
---

# Context

本任务承接已归档的 `20260815-article-detail-hifi`。仓库已有文章详情页、公开上下文、目录、参考资料、反链、相邻文章和相关推荐能力；本 spec 不重做业务层。

Penpot 没有显式的 `Implementation-ready` 状态标记。当前以唯一具备桌面/移动、浅色/深色四套画板的 `Article Long` 作为视觉基线：

- Desktop Light `faa08c08-ba3b-8031-8008-83175c70c4d0`
- Mobile Light `faa08c08-ba3b-8031-8008-83175caa86f1`
- Desktop Dark `faa08c08-ba3b-8031-8008-83175ce2b8b8`
- Mobile Dark `faa08c08-ba3b-8031-8008-83175eee5988`

Penpot 只作为视觉与交互表达依据；路由、API、数据、权限与已有业务合同以仓库为准。

已核验的 Article Short 视觉目标为：

- Desktop Light `faa08c08-ba3b-8031-8008-8319492b3c1b`
- Mobile Light `faa08c08-ba3b-8031-8008-83194959df6d`

Short 没有独立数据类型；它只是现有公开文章的确定性展示变体。未取得对应 Short Dark 画板的部分，不发明新结构，沿用同一 Short 布局并映射现有深色 `--ee-*` 语义 token。

# Goal

在不改变公开文章数据合同与现有业务区块的前提下，使 `/notes/{year}/{month}/{slug}` 按确定性规则呈现 Article Long 或 Article Short；对齐已核验 Penpot 画板的 Hero、阅读节奏、代码块、Callout、响应式布局和主题表达，并修复代码复制及移动表格横溢。

# Non-goals

- 不修改 API、数据库、共享 contracts、权限或文章数据。
- 不删除现有参考资料、反链、相邻文章、相关推荐、移动目录或文章链接复制能力。
- 不重做全站 Header、其它公开页面、后台页面或无关用户未提交修改。
- 不创建 Loading、Empty、Error 的新视觉功能；设计稿未提供这些状态，继续遵循现有失败分类。
- 不修改 Penpot 云端资源，不操作远程仓库，不部署。
- 不新增持久化文章类型、API 字段或后台选择器。
- 不用 slug、标题、文章 ID 或测试专用标记判断 Short。
- 不删除 Article Long 的桌面目录或移动内联目录。

# Acceptance criteria

- AC-1: 桌面与移动 Hero 具备 Penpot 的日期印章/内容层级和阅读提示；标题、边距、间距、圆角和色彩优先复用现有 `--ee-*` tokens。
- AC-2: Article Long 桌面阅读主列与正文宽度为 720px，代码块宽度为 680px，目录轨为 220px；不再使用原 spec 的约 760px 正文和 820–880px 证据块。移动端保持约 24px CSS 边距；表格、代码和媒体只允许局部滚动或收缩，不产生页面级横向溢出。
- AC-3: 代码块、Callout、相关区在浅色和深色主题下对齐 Penpot 的语义色、圆角和状态；保留现有真实内容和业务区块。
- AC-4: 代码复制按钮在真实浏览器中完成复制，并提供 idle、hover、focus、copied、error 的可见/可访问反馈；不伪造校验结果。
- AC-5: 文章页只有一个可见 H1，目录激活与 sticky 边界保持正确，键盘焦点可见，交互目标至少 44×44 CSS px。
- AC-6: 现有 404/5xx 失败语义、参考资料/反链/相邻/相关推荐条件渲染不回归；浏览器无 page error、console error 或新增非预期 warning。
- AC-7: Web 文档记录文章详情当前 Hero、阅读区、代码复制和移动表格滚动边界；类型检查、Vitest、构建、相关 E2E、axe/Lighthouse 质量门禁按可执行结果留证。
- AC-8: 展示变体只由 `readingTime <= 2 && headings.length <= 1 && !leadFigure` 决定，并复用现有阅读时长与 Markdown 标题/题图提取逻辑。Short 隐藏日期印章、章节概览、桌面目录和移动目录，压缩 Hero 与空白，正文保持约 65–75ch；仍展示真实分类、标签、摘要和复制链接，并保留参考资料、反链、相邻文章及相关推荐的既有条件渲染。Long 继续显示日期印章、桌面目录和移动目录。

# Risks

- 文章详情使用的 `main.css` 当前存在用户未提交的其它页面修改，补丁必须只触碰文章选择器。
- 代码复制问题可能来自事件绑定、Markdown 渲染 DOM 或水合状态，需以真实点击和 DOM 状态定位，不用测试替身掩盖。
- 文章表格必须在局部区域滚动，不能把 `overflow-x` 提升到页面级。
- Penpot 未定义参考资料、反链、相关推荐和错误态的完整视觉，应保留仓库行为并把不确定项记录为未知。
- Short 判定若另写阅读时长或标题解析会与列表和正文分叉；必须复用现有 shared utilities。
- Short 仅有已核验的浅色目标板；深色只能映射现有语义 token，不能据此发明另一套结构。

# Verification plan

- e2e => AC-1, AC-2, AC-4, AC-5, AC-6, AC-8
- web-quality => AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8
- harness-integrity => AC-7
