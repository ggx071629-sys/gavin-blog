---
id: spec-20260812-public-reading-maturity
level: L1
summary: 补齐公开文章的 SEO、阅读上下文、搜索摘要与移动导航成熟度，并按实际加载证据收敛重依赖
load_when:
  - task:20260812-public-reading-maturity
author: Codex
task_id: 20260812-public-reading-maturity
status: active
verification_profile: stack
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - apps/api/README.md
documentation_reason: 新增公开文章上下文契约并改变公开 SEO、Markdown 标题、搜索摘要和移动导航行为，需要同步两端边界文档。
state_history:
---

# Context

公开站已经具备响应式主题、搜索、RSS、站点地图、规范链接、Open Graph、JSON-LD 与自动化质量门禁，但空文章摘要会让 SEO 描述退化，正文可再产生 H1，阅读页缺少修订信息和上下篇／相关文章，搜索摘要暴露 Markdown 标记，移动导航缺少 Escape 与焦点恢复。生产构建还报告大 chunk，但当前 Lighthouse Performance 为 99，必须先用实际模块和请求证据定位，不能仅为消除警告盲目拆包。

# Goal

在不扩张内容模型、不修改公开内容和个人资料的前提下，使公开文章分享与结构化数据在摘要缺失时仍完整，使文章阅读形成可验证的上下文闭环，使搜索摘要和移动导航达到稳定的纯文本与键盘交互边界，并仅对确实进入无关公开页面的重依赖实施按需加载。

# Non-goals

- 不删除、改写或新增文章、项目、读书笔记及个人资料内容。
- 不修改 GitHub、邮箱、技能或其他占位资料。
- 不把文章摘要或封面改成数据库必填字段，不新增数据迁移。
- 不加入评论、统计、Newsletter、外部推荐服务或个性化算法。
- 不以任意 bundle 大小阈值替代实际路由加载证据，不重写 Markdown 技术栈。

# Acceptance criteria

- AC-1: 文章 summary 为空时，HTML description、Open Graph、Twitter、JSON-LD 与 RSS 使用同一类干净纯文本回退；文章与站点分享元数据包含可部署为绝对 URL 的默认 1200×630 分享图，文章 JSON-LD 的作者、发布者和主实体 URL 均为绝对 URL。
- AC-2: 公开文章页只渲染一个 H1；Markdown 正文标题在不改写源 Markdown 和现有锚点的前提下下移一级，目录层级与渲染层级一致；更新时间与发布时间存在实质差异时显示最后更新。
- AC-3: 新的公开文章上下文 API 只读取已发布快照，稳定返回时间上更早／更晚的相邻文章与最多三篇按同栏目、共同标签和发布时间排序的相关文章；公开阅读页展示该上下文且空结果自然降级。
- AC-4: 全站搜索响应的 snippet/summary 呈现为安全纯文本，不暴露 Markdown 标题、反引号、围栏、链接目标或 HTML 标记，并保留可理解的命中上下文。
- AC-5: 移动公开导航维持 disclosure 语义，支持 Enter/Space 与点击切换；焦点可按 Tab 进入链接；在触发按钮或展开导航内按 Escape 会关闭并把焦点返回触发按钮；路由变化后菜单关闭且 aria-expanded 与可见状态一致。
- AC-6: 构建分析明确记录公开路由的大 chunk 来源；无 Mermaid 或数学内容的公开页面不请求对应运行时代码，或证据证明这些代码原本未进入该路由而无需重构；首页不预加载文章增强运行时，现有 Lighthouse 90 门槛保持通过。
- AC-7: OpenAPI 合同、前后端单元／集成测试、公开 E2E、axe WCAG A/AA 与 Lighthouse 门禁覆盖新增行为且全部通过。

# Risks

- Markdown 标题降级可能让目录、锚点或深链接漂移；实现必须保持原 slug/anchor，只改变语义层级。
- 相邻与相关文章查询可能泄露草稿工作副本；查询必须以不可变发布快照和公开可见状态为边界。
- 搜索清洗过度可能丢失技术符号或命中上下文；清洗只移除表现语法并保留可读代码文本。
- 默认分享图如果依赖本地主机或相对 URL，会在真实域名失效；所有 URL 必须通过运行时 site URL 生成。
- 动态加载 Markdown 增强器可能引入水合漂移或首屏闪烁；只在构建证据确认收益后实施并纳入生产浏览器门禁。

# Verification plan

- api-lint => AC-3, AC-4, AC-7
- api-tests => AC-3, AC-4, AC-7
- web-quality => AC-1, AC-2, AC-5, AC-6, AC-7
- e2e => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
