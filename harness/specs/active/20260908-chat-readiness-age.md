---
id: spec-20260908-chat-readiness-age
level: L1
summary: 本机成功 Chat 验证记录年龄只作提示，保持运行与重启边界
load_when:
  - task:20260908-chat-readiness-age
task_id: 20260908-chat-readiness-age
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
  - harness/docs/operations/local-real-qa.md
documentation_reason: 同步本机启动与签发的年龄提示、无效证据拒绝及无隐式费用语义
state_history:
---
# Context
用户授权阶段1实施。当前 local artifact validator 将超过86400秒与签名/配置错误合并拒绝；build、lifespan、local write_receipt 共用它。运行时 operational/service 通过 verify_receipt 校验签名及绑定，不检查年龄。快捷启动错误提示却从未认证时间推断必须付费刷新。
# Goal
仅在显式本机 development 范围接受任意年龄的有效成功证据，年龄提示显示最后验证时间；正常运行和重启不自动付费。
# Non-goals
不部署、不调用真实供应商、不改费用授权/账本/生产资格。保留价格、预算、token、凭据、模型和超时绑定，阶段2另行处理复验及账本恢复。不关闭其他 active spec。
# Acceptance criteria
- AC-1: 有效成功本机证据在24小时边界及多年后仍可校验、构建和签发；持续运行跨原到期点及重启不增加 Chat 调用或清空预算。
- AC-2: 缺失、畸形、签名异常、失败、未来/无时区时间、配置漂移仍拒绝；生产入口不能使用本机证据。
- AC-3: 启动成功显示最后验证时间并将旧年龄作为建议；错误不从未认证时间推断过期，重复轮询不重复输出失败提示，无自动刷新。
# Risks
旧证据不证明供应商此刻可用，实际问答仍受现有输出、费用、熔断控制。缺失证据需显式授权探测，不能通过改时间或删账本恢复。旧 launcher-feedback spec 的过期说明已由本任务新行为替代，保留其未关闭状态。
# Verification plan
## Verification cases
- AC-1 => M09-READINESS-AGE-01
- AC-2 => M09-READINESS-INVALID-01
- AC-3 => M09-READINESS-HINT-01
## Gates
- api-tests => AC-1, AC-2, AC-3
