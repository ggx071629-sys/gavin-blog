---
id: archive-20260908-chat-revalidation-recovery
level: L2
summary: 分离本机兼容性证据与费用授权并提供保留历史的探测恢复
load_when:
  - task:20260908-chat-revalidation-recovery
task_id: 20260908-chat-revalidation-recovery
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/operations/local-real-qa.md
documentation_reason: 说明兼容性触发、旧证据离线转换、累计授权及失败恢复命令
evidence_sha256: b8ec7045666620d5e1859f409548bc3a3ef00785752cddb9423550fd5e6cfea9
state_history:
---

# 20260908-chat-revalidation-recovery

Deterministic compressed record. The original active spec remains in Git history.

## Goal

兼容性与费用分别校验；用同一账本保留历史并承接显式累计授权、可解释恢复，无隐式模型调用。

## Acceptance criteria

- AC-1: 新本机签名证据绑定凭据、endpoint、模型、token/context/timeout及输出协议；价格变化与授权内日预算变化仅本地校验，兼容性漂移拒绝。旧v1证据可用原配置离线转换至不同文件，原始证据和完成时间保持。
- AC-2: 显式授权以唯一ID和累计次数/金额上限写入同一签名账本，保存旧ledger快照及全部费用/失败；重放同ID不增加机会，耗尽即拒绝且无请求。新增累计额度须明确给出，不从日预算推导。
- AC-3: sending/unknown/measured_fail阻断新调用；确认无活动探测并注明原因后追加恢复事实，原attempt状态/金额不改，sending/unknown按保守上限计入。恢复不增加额度、不触发请求；并发授权/恢复/探测受同一独占锁保护。
- AC-4: 原命令提供状态、授权、恢复和离线转换入口，生产参数隔离；文档说明未知结算、次数与金额耗尽及旧证据限制，所有验证使用隔离数据和传输替身。

## Result

Verified and closed by the harness close command.

## Evidence

[20260908-chat-revalidation-recovery.json](../../verification/evidence/20260908-chat-revalidation-recovery.json)

SHA-256: `b8ec7045666620d5e1859f409548bc3a3ef00785752cddb9423550fd5e6cfea9`

Closed at 2026-09-08T16:05:57.505648+00:00.
