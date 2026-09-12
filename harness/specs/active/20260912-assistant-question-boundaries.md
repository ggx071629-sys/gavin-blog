---
id: spec-20260912-assistant-question-boundaries
level: L1
summary: Q4-04 页面优先及未核验的全量和时效请求
author: Codex
load_when:
  - task:20260912-assistant-question-boundaries
task_id: 20260912-assistant-question-boundaries
verification_profile: stack
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 明确页面候选优先条件、全量与时效请求的能力边界。
status: active
---
# Context
当前页面无条件提升，片段证据不能证明全站完整性或全球当前事实。
# Goal
明确页面指代或已解析来源才优先该页；可识别的全量/全局时效请求明确未核验，局部事实仍可回答。
# Non-goals
不增加全量库存、通用重排、在线查询改写或全局时间元数据；不设质量成功率。
# Acceptance criteria
- AC-1: 当前路径仅在明确页面指代或成功解析来源时优先；无关新题不提升当前页。
- AC-2: 明确全量计数/清单和最新/当前任职请求分别返回未核验专用终态，零Chat和Embedding；普通局部清单、技术计数和历史事实不被这些规则拦截。
- AC-3: 浏览器分别展示并恢复完整性/时效未核验提示，不称证据不存在或生成错误。
- AC-4: 文档记录规则边界、片段限制与仍未支持的通用能力。
# Risks
有限意图规则存在漏检与歧义，不据此承诺全部自然语言覆盖；技术词中的first不应误认序号。
# Verification plan
## Verification cases
- AC-1 => M09-PAGE-PRIORITY-01
- AC-2 => M09-SCOPE-NOTICES-01
- AC-3 => M09-SCOPE-WEB-01
- AC-4 => M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- e2e => AC-3
- harness-integrity => AC-4
