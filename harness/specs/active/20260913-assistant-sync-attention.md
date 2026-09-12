---
id: spec-20260913-assistant-sync-attention
level: L1
summary: 依据当前公开内容收录事实排除已覆盖的历史同步失败提醒
load_when:
  - task:20260913-assistant-sync-attention
task_id: 20260913-assistant-sync-attention
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明同步待处理数量与保留历史任务的区别及只读判定边界。
state_history:
---
# Context
当前概览累加所有历史失败任务；完整重建后仍显示已被当前索引覆盖的失败，误导管理员重复处理。
# Goal
仅对当前未解决的同步失败提醒；历史列表标注已收录并禁止无意义重试，保留原状态及费用记录。
# Non-goals
不删除或改写任务、调用及费用账本，不发起供应商探测，不变更每日回答失败统计，不将未知调用费用标为已核清。
# Acceptance criteria
- AC-1: 当前 active 索引的公开版本、完整切片与全文检索投影一致并有成功构建或同步事实时，历史 upsert 失败不计入 queue.failed；缺版本、缺切片、缺全文记录、无运行配置或无成功事实仍保留提醒，删除清理失败保守保留。
- AC-2: 历史任务继续以原失败状态可查，返回明确的覆盖标记；前端显示历史失败已收录并隐藏重试和故障诊断动作，普通未解决失败保持原操作；读取不调用模型或向量服务。
# Risks
只读收录事实不等于供应商实时健康或旧调用费用已确认；不能仅凭任务较旧、版本不同或存在一条切片判定完成。
# Verification plan
## Verification cases
- AC-1 => M10-SYNC-ATTENTION-01, M08-DOCS-01
- AC-2 => M10-SYNC-ATTENTION-02
## Gates
- api-tests => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
