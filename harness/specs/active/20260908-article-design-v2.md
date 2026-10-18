---
id: spec-20260908-article-design-v2
level: L1
summary: 对齐工程设计稿的文章列表与正文阅读视觉
load_when:
  - task:20260908-article-design-v2
task_id: 20260908-article-design-v2
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/ui-refinement/IMPLEMENTATION.md
documentation_reason: 记录文章页面的设计来源和阅读宽度取舍。
state_history:
---
# Context
用户要求文章页对齐 site_engineering_design_preview.html 中对应页面。列表已有宽屏适配，正文仍为旧版标头与无边框目录。
# Goal
对齐列表筛选分组、标签及正文返回栏、分类元信息、标题、引用框、代码框和目录卡片；保留现有宽屏列表与 740px 正文轴。
# Non-goals
不修改数据、接口、筛选分页、复制、目录定位或主题合同，不复制设计稿的示例内容。
# Acceptance criteria
- AC-1: 列表分组与卡片贴近设计稿，真实分类和标签可用，手机无页面横溢。
- AC-2: 正文具有顶部返回栏、分类徽章和目录卡片，双主题及窄屏可读，开始阅读、复制和目录定位保留。
# Risks
共享阅读 CSS 可能影响项目和书籍；新增规则限定文章根节点。原稿注释宽度与实际网格不一致，以现有 740px 阅读约束为准。
# Verification plan
## Verification cases
- AC-1 => M01-PUBLIC-SURFACES-01
- AC-2 => M01-PUBLIC-READING-01, M01-UNIT-ARTICLE-READING-01
## Gates
- e2e => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
