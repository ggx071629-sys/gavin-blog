---
id: spec-20260913-assistant-live-closure
level: L1
summary: 修复剩余回答表达并以同一签名预算跑通本地真实问答链路
load_when:
  - task:20260913-assistant-live-closure
author: Codex
task_id: 20260913-assistant-live-closure
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录本地真实调用计账边界与实际链路结果，不恢复取消范围。
state_history:
---

# Context

用户已批准恢复unknown并实施三项功能收敛工作。原累计145次1.307289元保留。启动器旧probe与当前模型配置不匹配，页面真实调用尚未接入累计评测账本。

# Goal

本地真实调用逐次纳入同一签名账本，正常在线预算继续生效；针对原始引文、简历完整事实与语言失败进行必要修复，并真实运行问答、追问、换题和恢复。用户随后明确将累计上限扩充为250次4元，原176次1.922580元及历史保留。

# Non-goals

不改变公开API、SSE或持久化schema，不新增在线判官、授权或生产部署；实体手机、读屏及Q6已取消。

# Acceptance criteria

- AC-1: 本地专用预算包装在每次实际请求前预留、已知响应结算、未知保守结算并阻止后续请求，取消不释放已发请求预算；生产及默认调用不受影响。
- AC-2: 回答提示鼓励精确连续引文与完整简历事实，映射、数字、否定、主体和限定反例保留；真实回归及页面结果如实记录。
- AC-3: 本地模型可选择服务端原文片段编号，由请求内映射恢复精确quote后仍执行原始校验；拒绝不存在或跨别名的编号，用户文本不能提供映射，不改公开API或会话schema。

# Risks

双层账本不能互相替代；预留失败不得发送，未知不得自动重试。预算不足时保留未完成范围。

# Verification plan

## Verification cases

- AC-1 => M09-LIVE-LEDGER-01, M09-CURRENT-BUDGET-01
- AC-2 => M09-FACT-ALIGNMENT-01, M09-CURRENT-PROMPT-01, M09-GROUNDING-01, M08-DOCS-01
- AC-3 => M09-LIVE-LEDGER-01, M09-FACT-ALIGNMENT-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-2
