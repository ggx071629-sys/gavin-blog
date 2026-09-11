---
id: spec-20260911-resume-page-coverage
level: L1
summary: 避免简历预算选取遗漏后页项目并将片段误作完整清单
load_when:
  - task:20260911-resume-page-coverage
task_id: 20260911-resume-page-coverage
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明简历页覆盖与局部证据的枚举边界。
state_history:
---
# Context
简历原文与索引均含第一页Signal Desk和第二页Quant Workbench；历史问题参与检索后预算选取偏向第一页，遗漏第二个项目。
# Goal
预算压力下让同一简历不同页获得首条候选机会，保留完整切片与引用；要求回答枚举已支持条目，不把片段当成全文。
# Non-goals
不硬编码项目名称或数量，不提高预算，不变更PDF解析或付费供应商配置，不保证未检索到的资料可被回答。
# Acceptance criteria
- AC-1: 超限时简历按来源/版本/页轮转，第二页首项先于第一页追加项；其他来源行为及引用完整性保持。
- AC-2: 枚举提示要求列出所有有证据的不同条目，说明局部片段不能证明全文总数；当前真实项目提问与追问选中两个项目。
# Risks
页不等于项目；不能宣称任意文档的完整统计。额外提示也计入原输入预算。
# Verification plan
## Verification cases
- AC-1 => M09-RESUME-PAGES-01
- AC-2 => M09-RESUME-PAGES-01, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
