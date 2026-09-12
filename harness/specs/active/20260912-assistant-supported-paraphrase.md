---
id: spec-20260912-assistant-supported-paraphrase
level: L1
summary: 减少明确技术改写与枚举摘要的误拒并保留边界
author: Codex
load_when:
  - task:20260912-assistant-supported-paraphrase
task_id: 20260912-assistant-supported-paraphrase
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录已支持的有限技术等价与显式计数摘要，以及未证明的自由语义改写。
state_history:
---
# Context
G04 的使用/用、SQLite/SQLite数据库、60秒/1分钟和枚举数量摘要需要成对验证，不能用全拒绝降低漏检。Q2-02/Q2-03已处理部分正例。
# Goal
允许已确认的有限等价改写和有显式数量、项目数一致的枚举摘要，拒绝虚构数量与限定语丢失，单独报告残余误拒。
# Non-goals
不提供自由语义蕴含，不把合成诊断集当作真实模型准确率，不推断含重叠/未明示集合的总数。
# Acceptance criteria
- AC-1: G04四对正例通过，正常技术改写和有限自述仍可用；新增的等价/摘要路径拒绝错误数量、不支持属性及不完整枚举。
- AC-2: 既有普通事实、否定、数量和自述反例继续拒绝；诊断结果区分已支持样例与任意改写、集合运算等残余范围，文档不宣称通用语义校验。
# Risks
只处理可逐项证明的有限表达；相似词、举例清单或不一致数量不能被机械当作等价事实。
# Verification plan
## Verification cases
- AC-1 => M09-SUPPORTED-PARAPHRASE-01, M09-GAP-CLAIMS-01
- AC-2 => M09-CLAIM-CONTEXT-01, M09-QUANTITY-BINDING-01, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
