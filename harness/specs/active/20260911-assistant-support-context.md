---
id: spec-20260911-assistant-support-context
level: L1
summary: 高风险支持句核对保留原始来源中的周围语境
load_when:
  - task:20260911-assistant-support-context
author: Codex
task_id: 20260911-assistant-support-context
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确支持原文不能裁掉前后语境，仍不保证通用语义蕴含。
state_history:
---
# Context
S4-03 离线评审发现 body 标记为谣言的获奖句，可以通过选择内部子串 quote 丢掉语境并被高风险检查接受。
# Goal
高风险断言使用 quote 在原文中的完整周围句子检查，不能仅根据模型自选短引文断定有据。
# Non-goals
不接入在线语义模型，不解决所有语义蕴含，不扩大外部协议、不改重试/预算或来源资格；普通自然综合仍保留。
# Acceptance criteria
- AC-1: 谣言/否定上下文中的获奖短引文不能发布为真实奖项；已有自述、部分回答、主体/数字/跨块代表例保持正确预期，内部 quote 不改写或公开。
# Risks
断句与重复引文有歧义时保守拒绝可能增加误拒；语义依赖等未覆盖事实仍需离线评审，不能宣传为通用证明。
# Verification plan
## Verification cases
- AC-1 => M09-GROUNDING-01, M08-DOCS-01
## Gates
- api-tests => AC-1
- harness-integrity => AC-1
