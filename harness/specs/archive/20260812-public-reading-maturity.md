---
id: archive-20260812-public-reading-maturity
level: L2
summary: 补齐公开文章的 SEO、阅读上下文、搜索摘要与移动导航成熟度，并按实际加载证据收敛重依赖
load_when:
  - task:20260812-public-reading-maturity
author: Codex
task_id: 20260812-public-reading-maturity
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - apps/api/README.md
documentation_reason: 新增公开文章上下文契约并改变公开 SEO、Markdown 标题、搜索摘要和移动导航行为，需要同步两端边界文档。
state_history:
---

# 20260812-public-reading-maturity

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不扩张内容模型、不修改公开内容和个人资料的前提下，使公开文章分享与结构化数据在摘要缺失时仍完整，使文章阅读形成可验证的上下文闭环，使搜索摘要和移动导航达到稳定的纯文本与键盘交互边界，并仅对确实进入无关公开页面的重依赖实施按需加载。

## Acceptance criteria

- AC-1: 文章 summary 为空时，HTML description、Open Graph、Twitter、JSON-LD 与 RSS 使用同一类干净纯文本回退；文章与站点分享元数据包含可部署为绝对 URL 的默认 1200×630 分享图，文章 JSON-LD 的作者、发布者和主实体 URL 均为绝对 URL。
- AC-2: 公开文章页只渲染一个 H1；Markdown 正文标题在不改写源 Markdown 和现有锚点的前提下下移一级，目录层级与渲染层级一致；更新时间与发布时间存在实质差异时显示最后更新。
- AC-3: 新的公开文章上下文 API 只读取已发布快照，稳定返回时间上更早／更晚的相邻文章与最多三篇按同栏目、共同标签和发布时间排序的相关文章；公开阅读页展示该上下文且空结果自然降级。
- AC-4: 全站搜索响应的 snippet/summary 呈现为安全纯文本，不暴露 Markdown 标题、反引号、围栏、链接目标或 HTML 标记，并保留可理解的命中上下文。
- AC-5: 移动公开导航维持 disclosure 语义，支持 Enter/Space 与点击切换；焦点可按 Tab 进入链接；在触发按钮或展开导航内按 Escape 会关闭并把焦点返回触发按钮；路由变化后菜单关闭且 aria-expanded 与可见状态一致。
- AC-6: 构建分析明确记录公开路由的大 chunk 来源；无 Mermaid 或数学内容的公开页面不请求对应运行时代码，或证据证明这些代码原本未进入该路由而无需重构；首页不预加载文章增强运行时，现有 Lighthouse 90 门槛保持通过。
- AC-7: OpenAPI 合同、前后端单元／集成测试、公开 E2E、axe WCAG A/AA 与 Lighthouse 门禁覆盖新增行为且全部通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260812-public-reading-maturity.json](../../verification/evidence/20260812-public-reading-maturity.json)

Closed at 2026-08-12T07:21:17.321547+00:00.
