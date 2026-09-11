---
id: spec-20260911-assistant-defense
level: L1
summary: 保留正常安全讨论并检查资料元数据与历史的指令边界
load_when:
  - task:20260911-assistant-defense
author: Codex
task_id: 20260911-assistant-defense
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明安全词汇讨论与执行请求的区别及资料字段、历史的有限规则防护。
state_history:
---
# Context
阶段二逐块支持契约已通过验收；S1 基线正常提示词工程问题被关键词误拒，改写泄露请求放行，hydrate 只扫描正文。
# Goal
保留正常技术讨论，拒绝代表性直接执行/泄露请求；资料正文、标题、heading 和历史均不能授予行为权限。
# Non-goals
不调用外部模型、不引入分类模型/在线裁判、不更改认证、工具权限、预算、索引结构或运行资格；不声称消除所有注入。
# Acceptance criteria
- AC-1: 提示按权限、历史、逐块证据、夹带指令、错误前提/时间与格式分段；保留自然综合、自述、冲突、部分回答、片段限制与简历例外。
- AC-2: 正常提示词工程/安全教程不再单凭词汇拒绝；直接、改写、角色冒充、混合、英文、编码和 Unicode 代表攻击继续拒绝，既有凭据/工具/路径约束不回退。
- AC-3: hydrate 与恢复复核都扫描正文、标题和 heading；带明确执行指令的旧历史不进入模型，普通历史保持指代功能且不是证据；正常公开技术内容仍可回答。
# Risks
有限规则仍有改写漏检和讨论误拒；过滤放行与实际模型服从必须分别报告。提示增量继续消耗原预算。
# Verification plan
## Verification cases
- AC-1 => M09-DEFENSE-01, M09-ANSWER-PATHS-02, M09-EVIDENCE-BUDGET-01, M08-DOCS-01
- AC-2 => M09-DEFENSE-02, M09-EVIDENCE-LINKS-01, M09-EVIDENCE-LINKS-02
- AC-3 => M09-DEFENSE-03, M09-GROUNDING-03
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
