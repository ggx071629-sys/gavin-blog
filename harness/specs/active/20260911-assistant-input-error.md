---
id: spec-20260911-assistant-input-error
level: L1
summary: 区分问答输入超限与未确认模型调用
author: Gavin
load_when:
  - task:20260911-assistant-input-error
task_id: 20260911-assistant-input-error
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录输入超限诊断码与模型调用结果未确认的区别。
state_history:
---
# Context
真实问题在检索成功后因输入估算超过8000被拒绝，却统一返回provider_result_unknown，妨碍定位。
# Goal
输入超限返回独立可定位错误；前端明确说明原因，后台日志记录不含正文的长度诊断。
# Non-goals
不提高额度、不发起真实Chat、不调整检索或裁剪算法、不修改账本；保留真正未确认调用的保护。
# Acceptance criteria
- AC-1: 输入超限通过SSE与会话恢复返回input_budget_exceeded，Chat调用次数为零；长度日志不含问题或证据正文。
- AC-2: 公开和后台共用错误映射明确显示输入超限；未确认模型调用不再使用笼统的结果未知标题，仍只允许检查结果。
# Risks
不得将输入超限建议为刷新或重发；不得把真正未确认的调用误判为未发送。
# Verification plan
## Verification cases
- AC-1 => M09-INPUT-ERROR-01, M08-DOCS-01
- AC-2 => M09-INPUT-ERROR-02
## Gates
- api-tests => AC-1
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
