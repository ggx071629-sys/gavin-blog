---
id: spec-20260914-admin-trial-recovery
level: L1
summary: 修复管理试问工具引用与恢复失败提示
load_when:
  - task:20260914-admin-trial-recovery
task_id: 20260914-admin-trial-recovery
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 恢复既有试问引用和错误反馈约定，不新增接口、权限或持久化结构。
state_history:
---

# Context

线上最近文章工具回答缺失 TrialCitation.excerpt，导致 read_trial 返回 500。前端丢弃具体错误，且流解析失败后可能把已完成问题保留为 pending。用户要求仅本地修复，不部署或推送。保留工作区其他任务改动。

# Goal

管理工具回答提供真实标题和公开时间依据；旧引用缺少摘录时恢复为空摘录并保留原文链接。区分已拒绝、调用未知、回答记录读取失败及限流等待；恢复读取不得自动重新提问。

# Non-goals

不放宽限流或预算，不改变会话权限、公开引用契约、数据库和线上开关，不清除旧回答。

# Acceptance criteria

- AC-1: 管理试问时间工具引用包含真实有界摘录，读取记录及随后提问成功，公开回答格式不变。
- AC-2: 旧记录缺少摘录仍可读取，显示未保存摘录；畸形引用仍拒绝。
- AC-3: 明确区分提交拒绝、限流等待、登录失效、结果读取失败和流中断，未知结果须恢复确认，不自动重发。

# Verification plan

## Verification cases

- AC-1 => M09-TRIAL-CATALOG-01
- AC-2 => M09-TRIAL-LEGACY-01
- AC-3 => M09-TRIAL-ERROR-01

## Gates

- api-tests => AC-1, AC-2
- web-quality => AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
