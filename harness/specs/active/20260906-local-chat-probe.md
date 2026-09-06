---
id: spec-20260906-local-chat-probe
level: L1
summary: 复用现有资格探测与预算账本执行有界本机 Chat 验证
load_when:
  - task:20260906-local-chat-probe
task_id: 20260906-local-chat-probe
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录显式本机探测命令、既有预算复用及与生产资格隔离。
state_history:
---

# Context

阶段 E 适配已经通过隔离测试。本机 .env 只配置了连接信息；用户已确认本轮 E/F 总计最多1元、Chat日上限2元。现有 provider_probe 只接受完整生产profile，不能通过伪造生产资料做本机联调。

# Goal

在既有 provider_probe 中增加显式 development-only Chat 探测入口，复用原 _chat_probe、预留/结算及同一账本实现。用独立本机预算绑定替代不相关的生产部署资料，绝不产生生产资格证明。填充经官方文档核对的非秘密本机配置并执行有界真实验证。

# Non-goals

不新建平行客户端、探测模块或账本实现；不签发readiness、不启用在线问答、不开启生产gate。F完整真实问答与资源实验仍在主计划追踪。

# Acceptance criteria

- AC-1: 只有development、官方DeepSeek端点、非空版本及明确的token/price/timeout/budget配置允许本机探测；失败前置条件不发请求。本机结果明确scope且不能通过生产artifact校验。
- AC-2: 本机探测复用既有文件锁、原子预留与结算，输入schema指令计入预算，未知usage保守结算；预算或配置漂移/额度耗尽不再发送请求。JSON应用schema与供应商strict_schema分别记录，模型不匹配不得通过。
- AC-3: 既有生产探测继续要求production/profile绑定，保持严格schema协议、usage与版本合同及原有预算测试通过；脱敏manifest无Key或原始响应。

# Risks

版本只能依据官方可核验声明，响应别名不证明权重版本。按高峰未缓存价预留及计量是保守估算，不是供应商账单精确对账。真实测试费用必须从整个1元上限扣减后再进入F。

# Verification plan

## Verification cases

- AC-1 => M10-LOCAL-CHAT-PROBE-01
- AC-2 => M10-LOCAL-CHAT-BUDGET-01
- AC-3 => M10-LOCAL-CHAT-ISOLATION-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
