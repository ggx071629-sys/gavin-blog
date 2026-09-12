---
id: spec-20260912-assistant-discussion-context
level: L1
summary: 有限地区分技术讨论和执行请求以及示例占位符和凭据
author: Codex
load_when:
  - task:20260912-assistant-discussion-context
task_id: 20260912-assistant-discussion-context
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录规则识别边界及真实模型测试与离线验收的区别。
state_history:
---
# Context
Q2-06/G06 的正常邮件、数据库、命令安全讨论被动作词拦截，示例占位符被当作真实凭据。G07 真实模型效果需独立实际验收，不能用此离线子规格代替。
# Goal
采用有限完整讨论框架和精确占位符豁免，保留框架外的执行/泄露拦截；检索和恢复仍扫描全部证据字段。
# Non-goals
不声称通用注入防护或真实模型抗攻击效果；不增加工具能力、不清空预算、不改变资料权限。
# Acceptance criteria
- AC-1: 邮件、数据库和命令安全的明确中英文讨论、已知占位符通过；已索引教程可以 hydrate 并恢复。
- AC-2: 混合执行、真实凭据、占位符尾缀、标题/正文/历史指令仍拦截；原技术引文与编码防护不回退。
# Risks
规则只识别有限语法；复杂讨论可能误拒，未覆盖攻击可能漏检。真实模型 G07 测试未通过前 Q2-06 不得完成。
# Verification plan
## Verification cases
- AC-1 => M09-DISCUSSION-CONTEXT-01, M09-DISCUSSION-HYDRATE-01, M09-GAP-DISCUSSION-01
- AC-2 => M09-DEFENSE-01, M09-DEFENSE-02, M09-DEFENSE-03, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
