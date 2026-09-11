---
id: spec-20260911-assistant-gap-closure
level: L1
summary: 修复数字和断句缺口并收紧已复现的无据断言与讨论误拒
load_when:
  - task:20260911-assistant-gap-closure
author: Codex
task_id: 20260911-assistant-gap-closure
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明中文数值、完整句核对、自述归属及教程引文的有限支持边界。
state_history:
---
# Context
后续复核发现中文紧邻数字漏检、逗号分句导致原句误拒；离线评审另有个人未记载经历、关系推断、第一人称转述、完整攻击句讨论误拒和改写攻击漏检。
# Goal
修复已复现缺口及紧邻正反例，保留自然综合、原句上下文、当前来源绑定和正常教程讨论。
# Non-goals
不调用配置模型或在线语义裁判，不以有限规则声称通用语义证明；不改变外部接口、预算、重试、来源资格或部署。
# Acceptance criteria
- AC-1: 中文紧邻/带空格的数字一致校验，数值或单位错配拒绝；完整原句含逗号可通过，丢掉限定或添入新断言不能通过。
- AC-2: 作者第一人称可在明确归属的自述来源中转述为作者自述；第三方、否定和时间不可洗成作者事实；无据个人经历与共现推依赖代表例拒绝，普通技术综合和部分回答仍可用。
- AC-3: 明确分析风险的教程引文可讨论并进入证据/历史；引文外夹带执行请求、实际凭据及引用后要求照做不能获豁免；已知改写、原注入/工具/路径边界继续拒绝。
# Risks
保守句式比对仍有语义误拒/漏检；教程豁免必须绑定完整解释语境，不能凭话题词或引号全局放行。自述转换只能绑定来源归属，不能替换任意人名。
# Verification plan
## Verification cases
- AC-1 => M09-GAP-NUMBERS-01, M09-GROUNDING-01, M08-DOCS-01
- AC-2 => M09-GAP-CLAIMS-01, M09-GROUNDING-03
- AC-3 => M09-GAP-DISCUSSION-01, M09-DEFENSE-02, M09-DEFENSE-03, M09-EVIDENCE-LINKS-01, M09-EVIDENCE-LINKS-02
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
