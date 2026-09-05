---
id: spec-20260906-public-reading
level: L1
summary: 完成视觉方案第三阶段的公开索引、详情与统一阅读体验
load_when:
  - task:20260906-public-reading
author: Gavin
task_id: 20260906-public-reading
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-3.md
documentation_reason: 同步公开页面布局、目录与阅读合同以及阶段验收记录。
state_history:
---

# Context

用户要求完成 ui-fix/PROPOSAL.md 第三阶段。基线 5c60bfbb6fd5ebbb8e723838b67b221211a2fec1；前两阶段已完成。当前公开页面仍有巨型详情标题、重复文章目录、手机详情目录在正文后、缺封面假书封及较重代码容器。保留用户已有 UI_AUDIT_REPORT.md 修改。

# Goal

将文章、项目、读书、归档、关于、搜索与错误页迁入已确认的双主题工程视觉，保持真实 URL、发布快照、SEO 和现有业务边界。

# Non-goals

不实现阶段四至七，不新增 API、结构图数据模型或搜索类型筛选接口，不按标题推断拓扑，不改已发布内容，不部署或启用助手。

# Acceptance criteria

- AC-1: 文章列表、项目列表、读书列表、归档、关于、搜索与错误页采用紧凑共同尺度；元信息、真实资料和真实筛选链接可用，空项目/读书仍完整，无伪造事实或封面。
- AC-2: 长短文章、项目与书籍详情采用最大 740px 正文轴、43/34px 标题、17px 正文；日期在元信息行；长文只有一套主要目录，手机目录先于正文；代码复制、表格局部横滚、已有内容图、来源及相关链接可用。
- AC-3: 隔离发布数据验证列表到详情、搜索到阅读、目录、引用、关联及公开快照；canonical、结构化信息及既有 SEO、404 与服务故障分类保持正确。
- AC-4: 双主题、320–1440px、480px 短视口、长标题/代码/表格/多条目、键盘与减少动态效果通过检查；加载、空数据、404 与服务故障分别验证，生产无障碍和性能门槛不降低。
- AC-5: 范围、差异、执行命令、真实证据和恢复边界写入阶段记录，Harness 影响计划与模块合同同步并确定性关闭。

# Risks

共享 Markdown/目录影响后台预览，需回归现有渲染；样例仅在隔离数据库发布。前端无类型搜索 API，因此搜索类型只作为范围说明，不伪造筛选。工程图由实际 Markdown Mermaid/图片提供，无图内容自然收束。验证不得干扰现有预览构建目录。

# Verification plan

## Verification cases

- AC-1 => M01-PUBLIC-SURFACES-01, M01-UNIT-ARTICLES-INDEX-01, M01-UNIT-ARCHIVE-INDEX-01, M01-UNIT-ABOUT-INDEX-01, M04-UNIT-PROJECTS-INDEX-01, M04-UNIT-BOOKS-INDEX-01, M03-UNIT-SEARCH-STATES-01, M03-UNIT-SEARCH-THEME-01
- AC-2 => M01-PUBLIC-READING-01, M04-PUBLIC-DETAILS-01, M01-UNIT-ARTICLE-READING-01, M01-UNIT-KNOWLEDGE-LINKS-01, M01-UNIT-MARKDOWN-MERMAID-01
- AC-3 => M04-PUBLIC-DETAILS-01, M07-P0-01, M01-UNIT-KNOWLEDGE-LINKS-01
- AC-4 => M01-PUBLIC-SURFACES-01, M01-PUBLIC-STATES-01, M07-P1-01
- AC-5 => M08-DOCS-01, M01-UNIT-PUBLIC-UI-POLISH-01

## Gates

- e2e => AC-1, AC-2, AC-3, AC-4, AC-5
- web-quality => AC-1, AC-4, AC-5
- harness-integrity => AC-5
