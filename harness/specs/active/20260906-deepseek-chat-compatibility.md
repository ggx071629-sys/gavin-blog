---
id: spec-20260906-deepseek-chat-compatibility
level: L1
summary: 本机 DeepSeek Chat JSON 输出适配与严格应用校验
load_when:
  - task:20260906-deepseek-chat-compatibility
task_id: 20260906-deepseek-chat-compatibility
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明本机 DeepSeek 请求协议、应用校验保证及生产资格边界。
state_history:
---

# Context

build-qa.md 阶段 E 的普通调用成功，但现有 json_schema/strict 请求返回 400。2026-09-06 官方 Chat Completions 文档仅列出 text/json_object，输出参数为 max_tokens；默认 thinking enabled。本机仅填写连接信息，版本、价格、限额与真实测试预算仍需确认。

# Goal

复用既有 LangChain ChatOpenAI、结构化回答链、引用校验及结算，实现 development 官方 DeepSeek 端点的 JSON 模式适配并用传输边界和应用回归验证。

# Non-goals

不新增平行客户端、探测器或预算账本；不启用生产、不伪造 qualification profile、不执行未经确认预算的真实调用。完整 E/F 真实问答验收继续由主计划追踪，不以离线测试替代。

# Acceptance criteria

- AC-1: development 官方 DeepSeek 请求使用 json_object、max_tokens 与显式 disabled thinking，自动重试关闭；其他端点与生产环境保留原有严格 schema 协议，无静默降级。
- AC-2: JSON 模式保留 raw metadata；严格解析完整 JSON，拒绝缺字段、额外字段、错误类型、尾部垃圾、截断及空响应；引用与 finish_reason 校验保持有效，未知 usage 保守结算。
- AC-3: schema 指令在发送前计入完整输入预算；输入不适配时不调用模型，现有在线链复用同一适配，无新增客户端或生产 probe 旁路。

# Risks

JSON 模式没有供应商端 schema 保证。等价保证仅指应用接受并发布的回答必须通过 schema 与引用校验，不保证生成成功率。模型版本声明不能冒充响应身份，真实费用与窗口必须独立核实。仅匹配官方 HTTPS 根与 /v1 端点，避免把供应商策略误用于任意兼容代理。

# Verification plan

## Verification cases

- AC-1 => M09-DEEPSEEK-TRANSPORT-01
- AC-2 => M09-DEEPSEEK-VALIDATION-01
- AC-3 => M09-DEEPSEEK-BUDGET-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
