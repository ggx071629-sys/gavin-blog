---
id: spec-20260911-assistant-about-citations
level: L1
summary: Q2-04 开放关于页安全引用并明确自述与冲突提示规则
load_when:
  - task:20260911-assistant-about-citations
task_id: 20260911-assistant-about-citations
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
documentation_reason: 同步关于页引用白名单、个人事实与冲突处理边界。
state_history:
---
# Context
Q2-01—03 已正式验收；about 已可检索，但浏览器引用白名单拒绝 /about。
# Goal
只开放 /about 精确引用路径，在公开问答和管理试问可点击；明确关于页自述及资料冲突规则。
# Non-goals
不开放任意 URL、不改 UI 设计、不调用真实付费供应商、不承诺规则能数学保证所有模型输出。
# Acceptance criteria
- AC-1: 公开回答和管理试问显示“关于 Gavin”并可打开 /about，错误外部路径仍拒绝。
- AC-2: 提示词允许关于页明确自述，保留文章主题不得冒充能力与不夸大规则；矛盾事实要求引用双方，引用仍只由 evidence alias 生成。
# Risks
浏览器允许助手入口不等于允许回答引用；两类白名单不得混用；提示测试仅证明传入规则和引用合同，不冒充真实供应商行为验证。
# Verification plan
## Verification cases
- AC-1 => M09-ABOUT-CITATION-01
- AC-2 => M09-ABOUT-FACTS-01
## Gates
- e2e => AC-1
- api-tests => AC-2
- harness-integrity => AC-1, AC-2
