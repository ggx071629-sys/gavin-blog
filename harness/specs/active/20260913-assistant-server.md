---
id: spec-20260913-assistant-server
level: L1
summary: 在现有博客服务器执行明确接受缺项的问答有限验证部署
load_when:
  - task:20260913-assistant-server
task_id: 20260913-assistant-server
status: active
verification_profile: focused
planned_modules:
  - M11
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 新增显式有限验证 profile，记录实际资源与未配置运营能力，不能混同完整生产资格。
state_history:
---

# Context

用户要求保留现有 Ubuntu 博客和数据并启用问答；实际内存 3655 MiB，无 Swap。用户已明确允许放宽旧准入要求、使用有限验证部署并记录缺项，不做长期压测。真实 Chat 延续累计 2 元，基线已用 0.027518 元。秘密及数据不得进入 GitHub。

# Goal

以独立 schema 4 明示有限验证与接受的缺项，保留 schema 2/3 的完整要求和摘要兼容性。复用发布制品，备份并验证恢复，启动 E5/Qdrant/Worker、生产 API 与问答入口。

# Non-goals

不执行长期压测，不宣称完整生产资格，不覆盖既有数据，不上传私密部署配置和业务数据。

# Acceptance criteria

- AC-1: 新 profile 如实记录内存及缺项，旧 profile 仍拒绝相同放宽，预算、鉴权、服务绑定不被绕过。
- AC-2: 空媒体库可形成一致快照并通过隔离恢复，运行时不进入长期备份。
- AC-3: 目标五服务运行，通过短时 HTTPS/SSE 与引用验证，保存费用、资源和回滚记录。

# Verification plan

## Verification cases

- AC-1 => M11-SERVER-PROFILE-01
- AC-2 => M11-SERVER-BACKUP-01
- AC-3 => M11-SERVER-SMOKE-01

## Gates

- focused-profile-tests => AC-1
- backup-restore-tests => AC-2
- target-bounded-smoke => AC-3
