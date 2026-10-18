---
id: archive-20260815-article-detail-hifi
level: L2
summary: 在公开文章契约不变的前提下，按 Penpot V1 系统合同与 V2 阅读外观重做文章详情
load_when:
  - task:20260815-article-detail-hifi
author: Gavin
task_id: 20260815-article-detail-hifi
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开文章阅读页的 Hero、目录、代码块和相关推荐 chrome 改变，需要同步 Web 边界说明。
state_history:
---

# 20260815-article-detail-hifi

Deterministic compressed record. The original active spec remains in Git history.

## Goal

把 `/notes/{year}/{month}/{slug}` 做成单一 V2 阅读页：窄正文、宽证据块、可结束的目录、可复制的代码块和自适应相关推荐，同时保持已发布快照契约与现有知识链接。

## Acceptance criteria

- AC-1: 文章详情仍只读取公开文章与 `/context`。页面块顺序为 Hero、正文、参考资料、反链、相邻、相关；空块不渲染。保留 `article-updated-at`、`article-references`、`content-backlinks`、`article-neighbors`、`related-articles`。
- AC-2: 桌面宽度至少 1280 时，正文约 760px、证据块约 820–880px、目录约 220px。Hero 提供“开始阅读”与“复制文章链接”。目录强激活且 sticky 在正文结束处停止，不覆盖相关或页脚。页面仍只有一个可见 H1。
- AC-3: 768–1279 时正文不超过容器、证据块随容器、目录可降级。小于 768 时左右留白约 24px，只有代码区可以横向滚动，目录是内联 disclosure 而不是模态 sheet。
- AC-4: 围栏代码从 info string 解析语言和可选文件名，并提供 default、hover、copied、error 复制反馈。不渲染虚构的校验结果。
- AC-5: 相关文章 1 条铺满、2 或 3 条自适应且不留空网格位。参考资料、反链、相邻在有数据时可见。
- AC-6: 明确 404 仍表示文章不存在，已知 5xx 或网络失败不渲染成空文章。焦点环可见，交互目标至少 44×44 CSS px，减少动态效果偏好关闭非必要运动。文章路由滚动超过约 120px 时顶栏从约 76px 压缩到约 56px，且不删除现有导航项。
- AC-7: Web 类型检查、Vitest、公开文章 E2E、axe WCAG A/AA 与现有 Lighthouse 门槛覆盖本页行为；`apps/web/README.md` 记录阅读页 chrome。
- AC-8: 带公开 URL 参考资料的孵化发布后，工作副本与当前修订一致，现有发布闭环回滚不被 `ARTICLE_WORKING_COPY_DIRTY` 误拒绝。

## Result

Verified and closed by the harness close command.

## Evidence

[20260815-article-detail-hifi.json](../../verification/evidence/20260815-article-detail-hifi.json)

Closed at 2026-08-15T08:27:00.143279+00:00.
