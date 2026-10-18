---
id: archive-20261018-session-clock-consistency
level: L2
summary: 修复登录会话初始时间一致性并按真实时间校验列表顺序
load_when:
  - task:20261018-session-clock-consistency
task_id: 20261018-session-clock-consistency
status: compressed
documentation_impact: none
documentation_reason: 修复既有 UTC-aware 时间语义和会话列表时间不变量；响应字段、允许的 ISO 表示、认证与撤销规则、TTL、存储迁移和运维步骤均不改变。现行 UTC 决策及 API README 已说明 Z 与 UTC 偏移表示合法，无新增永久接口或操作合同。
evidence_sha256: bfa9094de4dd20170646b67cd73ac75f976dcf0d94f87d96fc3fbbcc1b715a25
state_history:
---

# 20261018-session-clock-consistency

Deterministic compressed record. The original active spec remains in Git history.

## Goal

成功登录创建会话时读取同一个 UTC-aware 瞬间，显式赋给 created_at 与 last_seen_at。保留 expires_at(settings) 的既有独立调用与过期规则。原会话列表测试使用每次递增 1 微秒的受控时钟，验证初始一致性；解析带时区的返回时间后校验活动时间不早于创建时间，覆盖整秒与小数秒表示。所有验证使用本地隔离 fixture；沿用 GitHub 上传与纯检查 CI 授权。

## Acceptance criteria

- AC-1: 受控递增时钟下，新登录会话的 created_at 与初始 last_seen_at 表示同一个 UTC-aware 瞬间；API 列表的时间按解析后的带时区 datetime 严格校验先后，合法整秒/小数表示不再被字典序误判，真正倒序仍失败；原当前会话标记、敏感字段排除、CSRF、单个/其他会话撤销及并发旧登录失效断言完整保留并通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20261018-session-clock-consistency.json](../../verification/evidence/20261018-session-clock-consistency.json)

SHA-256: `bfa9094de4dd20170646b67cd73ac75f976dcf0d94f87d96fc3fbbcc1b715a25`

Closed at 2026-10-18T08:11:34.009055+00:00.
