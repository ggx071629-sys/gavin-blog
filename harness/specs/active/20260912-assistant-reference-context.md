---
id: spec-20260912-assistant-reference-context
level: L1
summary: Q4-03 有限来源指代、换题隔离和专用澄清
author: Codex
load_when:
  - task:20260912-assistant-reference-context
task_id: 20260912-assistant-reference-context
verification_profile: stack
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 说明有限来源指代、专用澄清、历史不作为事实及未覆盖语言。
status: active
---
# Context
Q4-02 已验收。当前检索和提示无条件拼接旧问题/答案，有限指代没有可靠澄清路径。
# Goal
仅将上一有效回答唯一且当前可用的公开来源用作对象线索；重新检索，未知对象先澄清，换题不带旧问答。
# Non-goals
不解析答案条目顺序，不推断任意自然语言实体，不改变四轮留存、TTL、数据库或付费次数上限。
# Acceptance criteria
- AC-1: 有限中英指代可由上一回答唯一公开来源辅助检索与提示，当前问题保留；旧问答正文不进入新提示，旧来源撤销不能继续被解析。
- AC-2: 缺少、多个、序号或TTL失效对象返回 clarification_required 专用终态，零Chat/Embedding调用；换题只查当前问题。
- AC-3: 浏览器独立显示并恢复澄清提示，不显示证据不足或操作失败；已有多编号场景按已实施的逐卡定位预期回归。
- AC-4: 记录有限范围与残余限制，不声称通用多轮成功或生产资格。
# Risks
规则漏检仍可能发生；来源更新时只用当前公开版重新检索，不沿用旧事实。
# Verification plan
## Verification cases
- AC-1 => M09-REFERENCE-RESOLVE-01
- AC-2 => M09-REFERENCE-CLARIFY-01
- AC-3 => M09-REFERENCE-WEB-01
- AC-4 => M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- e2e => AC-3
- harness-integrity => AC-4
