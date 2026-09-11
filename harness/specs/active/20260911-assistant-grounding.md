---
id: spec-20260911-assistant-grounding
level: L1
summary: 自然综合回答按块绑定支持材料并拒绝已知事实错配
load_when:
  - task:20260911-assistant-grounding
author: Codex
task_id: 20260911-assistant-grounding
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明内部支持材料、兼容失败、留存预算与确定性校验的语义局限。
state_history:
---
# Context
S1-01 离线函数基线复现无关引用假奖项、累计引用及数字子串误配；已确认自然综合和先离线语义核对。技术契约见 plan-build/assistant-safety/completed/phase-1-baseline/S1-03.md。
# Goal
每块自然综合回答绑定本轮有效证据原句，拒绝已确认的不支持结论，保证共同消费链路和内部材料隔离。
# Non-goals
不调用配置模型、不上线、不引入在线语义模型、不改输入过滤（由阶段三另立短期 spec）；不改公开 schema、来源资格或提高预算。
# Acceptance criteria
- AC-1: 无关引用假奖项、跨块借证据、数字单位/子串误配被拒；有据自述、自然综合、部分回答及路径呈现仍可用。
- AC-2: 每块 supports 与所引本轮 body 绑定，缺失/伪造/错绑拒绝；生产与本地 JSON 模式字段一致，固定简历提示例外保留；输入/输出预算包含材料且不提高配置额度。
- AC-3: 公开/管理问答、SSE、恢复和成功历史仅消费校验后回答；支持材料不进公开载荷、历史或 checkpoint，失败/成功终止清除临时解析材料，旧未完成输出不得绕过校验；撤销来源仍不能发布。
# Risks
连续原句存在不等于语义支持，主体、否定和时间仍需代表例离线复核；不宣称通用事实验证。增加 schema 会占用既有 token 空间。拒绝未知旧输出可能减少可恢复回答。
# Verification plan
## Verification cases
- AC-1 => M09-GROUNDING-01, M09-ANSWER-PATHS-01, M09-ANSWER-PATHS-02, M08-DOCS-01
- AC-2 => M09-GROUNDING-02, M09-EVIDENCE-BUDGET-01, M09-EVIDENCE-BUDGET-02
- AC-3 => M09-GROUNDING-03, M09-ANSWER-PATHS-03
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
