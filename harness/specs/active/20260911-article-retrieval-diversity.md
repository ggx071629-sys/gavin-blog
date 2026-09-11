---
id: spec-20260911-article-retrieval-diversity
level: L1
summary: 避免重复切片挤掉其他文章并隐藏来源路径文本
load_when:
  - task:20260911-article-retrieval-diversity
task_id: 20260911-article-retrieval-diversity
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录候选来源覆盖和面向用户的标题引用规则。
state_history:
---
# Context
真实E5检索中，文章列表问题的8个候选被多段简历及相同文章挤占，导致其他已收录技术文章未被传入回答。来源卡片还显示裸路径。
# Goal
扩大默认候选池至32条（可配置到128），证据组装上限扩大至24000字符；在候选上限前按当前有效来源轮转，优先不同资料的首个命中，再追加同来源切片；去掉用户可见的来源路径文本并保留标题跳转。
# Non-goals
不写死文章ID或名称，不提高预算，不声称有限召回结果是完整目录，不改变公开内容范围或安全过滤。
# Acceptance criteria
- AC-1: 默认候选32条、组装上限24000字符且可配置，模型输入及费用上限不变；同一资料多个高排名切片不会挤掉可用的其他来源首项，过期/删除资料仍不返回，真实两个技术文章均可进入提示。
- AC-2: 提示描述不提供来源路径，要求正文用标题和引用；来源卡片不显示裸路径，仍按原路径跳转。
# Risks
来源多样性可能减少单篇细节候选；多于候选上限的来源仍不保证全量覆盖。
# Verification plan
## Verification cases
- AC-1 => M10-SOURCE-DIVERSITY-01
- AC-2 => M09-SOURCE-TITLE-01, M09-SOURCE-TITLE-02, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
