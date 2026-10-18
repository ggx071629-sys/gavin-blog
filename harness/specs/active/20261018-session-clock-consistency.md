---
id: spec-20261018-session-clock-consistency
level: L1
summary: 修复登录会话初始时间一致性并按真实时间校验列表顺序
load_when:
  - task:20261018-session-clock-consistency
task_id: 20261018-session-clock-consistency
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 修复既有 UTC-aware 时间语义和会话列表时间不变量；响应字段、允许的 ISO 表示、认证与撤销规则、TTL、存储迁移和运维步骤均不改变。现行 UTC 决策及 API README 已说明 Z 与 UTC 偏移表示合法，无新增永久接口或操作合同。
state_history:
---

# Context

前一任务 20261018-harness-completion 已正常关闭并随 f58fbc13 上传，历史 archive、evidence 和 completion event 保持不变。首次实际 CI 在会话列表时间断言失败；确定性本地复现确认两个问题：AdminSession 的两个独立默认时钟可能先生成 last_seen_at 再生成 created_at；合法 ISO 时间的小数精度或时区表示不同时，字符串字典序也不能代表真实先后。

# Goal

成功登录创建会话时读取同一个 UTC-aware 瞬间，显式赋给 created_at 与 last_seen_at。保留 expires_at(settings) 的既有独立调用与过期规则。原会话列表测试使用每次递增 1 微秒的受控时钟，验证初始一致性；解析带时区的返回时间后校验活动时间不早于创建时间，覆盖整秒与小数秒表示。所有验证使用本地隔离 fixture；沿用 GitHub 上传与纯检查 CI 授权。

# Non-goals

不改变认证、限流、Cookie、CSRF、会话撤销、并发改密或 TTL 规则，不修改数据库结构或历史会话记录，不放宽时间及安全断言，不连接、操作或部署实际应用服务器，不重写前一任务的关闭资产。

# Acceptance criteria

- AC-1: 受控递增时钟下，新登录会话的 created_at 与初始 last_seen_at 表示同一个 UTC-aware 瞬间；API 列表的时间按解析后的带时区 datetime 严格校验先后，合法整秒/小数表示不再被字典序误判，真正倒序仍失败；原当前会话标记、敏感字段排除、CSRF、单个/其他会话撤销及并发旧登录失效断言完整保留并通过。

# Verification plan

## Verification cases

- AC-1 => M06-ACCOUNT-SESSION-01

## Gates

- api-tests => AC-1
- harness-integrity => AC-1
