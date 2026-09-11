---
id: spec-20260911-assistant-live-activation
level: L1
summary: 实际内容库接入并补齐本机快捷启动器的既有worker生命周期
load_when:
  - task:20260911-assistant-live-activation
task_id: 20260911-assistant-live-activation
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/docs/operations/local-real-qa.md
documentation_reason: 明确真实内容库、后台worker启停以及实际简历接入结果。
state_history:
---
# Context
用户要求完成实际接入，先前隔离验收不等于实际启用。已备份升级两份实际内容库并保存URL；本机快捷启动器只启动E5/Qdrant/Web/API，没有持续消费简历队列的worker。
# Goal
快捷启动器统一管理既有索引worker，使用.env.e5真实库和模型配置，使实际导入及后续手动刷新生效。
# Non-goals
不增加服务种类，不改模型/预算/供应商资格，不部署生产，不修改其他用户界面。
# Acceptance criteria
- AC-1: worker由同一个快捷启动管理进程创建并纳入现有退出清理和失败检测；在E5/Qdrant就绪后启动，使用.env.e5，默认库和Chat秘密不被误用。
- AC-2: 快捷入口现有端口检查、受控进程身份与配置错误脱敏合同保持；实际库导入和版本引用可验，结果与隔离测试区分。
# Risks
误读.env会消费错误库；独立未管理worker会在关闭后残留；真实问答不得扩大已有费用授权。
# Verification plan
## Verification cases
- AC-1 => M09-LIVE-WORKER-01
- AC-2 => M09-LIVE-WORKER-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
