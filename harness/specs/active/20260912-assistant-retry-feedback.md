---
id: spec-20260912-assistant-retry-feedback
level: L1
summary: Q3-03 区分输出失败并为有界重试提供无正文反馈
load_when:
  - task:20260912-assistant-retry-feedback
task_id: 20260912-assistant-retry-feedback
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确重试反馈、失败原因及费用与隐私边界。
state_history:
---

# Context
G13 将收到的非法输出与供应商结果未知混淆，第二次请求没有纠正反馈。

# Goal
为已有最多两次生成提供固定原因反馈并持久化无正文的阶段分类。

# Non-goals
不增加调用或费用上限，不新增在线校验模型、正文留存或生产资格。

# Acceptance criteria
- AC-1: 输出校验失败的第二次请求包含固定结构化原因，反馈进入输入预算，不复制失败正文。
- AC-2: 格式/支持失败、缺证据和供应商未知可区分；未知调用不重发，重试仍最多两次且幂等恢复不新增调用。
- AC-3: 运行文档说明有限纠正能力、后台原因及累计预算不变。

# Risks
反馈占用输入预算；可纠正不代表真实模型一定纠正成功。原因码必须为白名单。

# Verification plan
## Verification cases
- AC-1 => M09-RETRY-FEEDBACK-01
- AC-2 => M09-RETRY-FAILURE-01
- AC-3 => M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-unit => AC-3
