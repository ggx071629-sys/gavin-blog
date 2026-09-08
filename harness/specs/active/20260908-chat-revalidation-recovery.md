---
id: spec-20260908-chat-revalidation-recovery
level: L1
summary: 分离本机兼容性证据与费用授权并提供保留历史的探测恢复
load_when:
  - task:20260908-chat-revalidation-recovery
task_id: 20260908-chat-revalidation-recovery
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/operations/local-real-qa.md
documentation_reason: 说明兼容性触发、旧证据离线转换、累计授权及失败恢复命令
state_history:
---
# Context
阶段1已关闭。本机v1证据与ledger把价格/预算/兼容性混绑，旧失败会永久拒绝再探测。用户只授权实现，不授权真实付费或改变真实账本。
# Goal
兼容性与费用分别校验；用同一账本保留历史并承接显式累计授权、可解释恢复，无隐式模型调用。
# Non-goals
不部署、不调用真实供应商、不修改真实账本/费用授权、不改生产资格或在线熔断恢复；正常问答成功时间不替代资格证据。
# Acceptance criteria
- AC-1: 新本机签名证据绑定凭据、endpoint、模型、token/context/timeout及输出协议；价格变化与授权内日预算变化仅本地校验，兼容性漂移拒绝。旧v1证据可用原配置离线转换至不同文件，原始证据和完成时间保持。
- AC-2: 显式授权以唯一ID和累计次数/金额上限写入同一签名账本，保存旧ledger快照及全部费用/失败；重放同ID不增加机会，耗尽即拒绝且无请求。新增累计额度须明确给出，不从日预算推导。
- AC-3: sending/unknown/measured_fail阻断新调用；确认无活动探测并注明原因后追加恢复事实，原attempt状态/金额不改，sending/unknown按保守上限计入。恢复不增加额度、不触发请求；并发授权/恢复/探测受同一独占锁保护。
- AC-4: 原命令提供状态、授权、恢复和离线转换入口，生产参数隔离；文档说明未知结算、次数与金额耗尽及旧证据限制，所有验证使用隔离数据和传输替身。
# Risks
旧v1只保存混合摘要，无法从新价格反推旧兼容性，因此转换必须在原配置下验证，绝不猜测。新账本签名使用原readiness密钥，密钥轮换需另行受控迁移。累计授权不能使旧费用归零。恢复确认是操作者对进程静止和故障调查的声明，账本仍保留失败事实与保守费用。新日预算上限属于显式授权声明，不通过运行自动提升。
# Verification plan
## Verification cases
- AC-1 => M09-REVALIDATION-COMPAT-01
- AC-2 => M09-REVALIDATION-BUDGET-01
- AC-3 => M09-REVALIDATION-RECOVERY-01
- AC-4 => M09-REVALIDATION-CLI-01
## Gates
- harness-integrity => AC-1, AC-2, AC-3, AC-4
- api-tests => AC-1, AC-2, AC-3, AC-4
