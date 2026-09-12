---
id: spec-20260912-assistant-claim-context
level: L1
summary: 校验普通陈述并保留否定、时间、主体和冲突语境
author: Codex
load_when:
  - task:20260912-assistant-claim-context
task_id: 20260912-assistant-claim-context
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明有限事实支持、相邻撤回与同主体冲突规则、问题相关性检查及未覆盖语义。
state_history:
---
# Context
Q2-01 的 40 个合成正反例显示当前规则放行 17 个无支持/错配例，完整句候选虽降低错放但增加误拒。本任务落实普通事实及语境保护，不能靠无限扩大正则宣称通用语义蕴含已完成。
# Goal
普通陈述也必须由当前引用语境支持，保留主体、否定、时间和范围；相邻撤回与同主体同属性冲突不得被选句掩盖。把当前问题传入校验，拒绝明确的主题错答并允许有界缺口说明。
# Non-goals
不新增在线语义模型；数量规范化、自由改写、技术符号和提示注入分别由 Q2-03—Q2-06 处理。不宣称覆盖所有语言、跨文档实体消歧或未知题型。
# Acceptance criteria
- AC-1: 合成正反对照拒绝普通事实发明、否定反转、主体替换、时间替换及范围扩张；继续支持原有明确 About 自述、普通技术改写、已支持关系和真实引文校验。
- AC-2: 同句与相邻跨句撤回被保留；同主体同属性的明确来源冲突不能单方断言，披露冲突须引用双方；不同主体不误判为冲突。
- AC-3: 当前问题进入校验；明确数据库/许可证等主题错答被拒，材料确无对应主题时允许有界缺口说明；未知语义范围由文档明确，SSE 与正文/支持原文清理保护继续有效。
# Risks
确定性匹配会拒绝未识别的合法改写，不能当作真实模型质量已通过；严格保护需与既有正例一起验证，未覆盖改写在后续任务继续处理。
# Verification plan
## Verification cases
- AC-1 => M09-CLAIM-CONTEXT-01, M09-GROUNDING-01, M09-GROUNDING-02, M09-GAP-CLAIMS-01, M09-ABOUT-FACTS-01, M09-RESUME-FACTS-01
- AC-2 => M09-CLAIM-CONTEXT-02, M09-GROUNDING-01
- AC-3 => M09-CLAIM-CONTEXT-03, M09-GROUNDING-03, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
