---
id: archive-20260908-chat-readiness-age
level: L2
summary: 本机成功 Chat 验证记录年龄只作提示，保持运行与重启边界
load_when:
  - task:20260908-chat-readiness-age
task_id: 20260908-chat-readiness-age
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
  - harness/docs/operations/local-real-qa.md
documentation_reason: 同步本机启动与签发的年龄提示、无效证据拒绝及无隐式费用语义
evidence_sha256: de2445f7fc632ecec76df748aa3f5c029dedc83ff39259e84c4e66ac9268c209
state_history:
---

# 20260908-chat-readiness-age

Deterministic compressed record. The original active spec remains in Git history.

## Goal

仅在显式本机 development 范围接受任意年龄的有效成功证据，年龄提示显示最后验证时间；正常运行和重启不自动付费。

## Acceptance criteria

- AC-1: 有效成功本机证据在24小时边界及多年后仍可校验、构建和签发；持续运行跨原到期点及重启不增加 Chat 调用或清空预算。
- AC-2: 缺失、畸形、签名异常、失败、未来/无时区时间、配置漂移仍拒绝；生产入口不能使用本机证据。
- AC-3: 启动成功显示最后验证时间并将旧年龄作为建议；错误不从未认证时间推断过期，重复轮询不重复输出失败提示，无自动刷新。

## Result

Verified and closed by the harness close command.

## Evidence

[20260908-chat-readiness-age.json](../../verification/evidence/20260908-chat-readiness-age.json)

SHA-256: `de2445f7fc632ecec76df748aa3f5c029dedc83ff39259e84c4e66ac9268c209`

Closed at 2026-09-08T15:42:20.950367+00:00.
