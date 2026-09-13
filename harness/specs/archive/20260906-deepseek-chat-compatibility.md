---
id: archive-20260906-deepseek-chat-compatibility
level: L2
summary: 本机 DeepSeek Chat JSON 输出适配与严格应用校验
load_when:
  - task:20260906-deepseek-chat-compatibility
task_id: 20260906-deepseek-chat-compatibility
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明本机 DeepSeek 请求协议、应用校验保证及生产资格边界。
evidence_sha256: df4169121effd6916caa787f8a61abfbee69029cfccf3f286eba44e02ea03e29
state_history:
---

# 20260906-deepseek-chat-compatibility

Deterministic compressed record. The original active spec remains in Git history.

## Goal

复用既有 LangChain ChatOpenAI、结构化回答链、引用校验及结算，实现 development 官方 DeepSeek 端点的 JSON 模式适配并用传输边界和应用回归验证。

## Acceptance criteria

- AC-1: development 官方 DeepSeek 请求使用 json_object、max_tokens 与显式 disabled thinking，自动重试关闭；其他端点与生产环境保留原有严格 schema 协议，无静默降级。
- AC-2: JSON 模式保留 raw metadata；严格解析完整 JSON，拒绝缺字段、额外字段、错误类型、尾部垃圾、截断及空响应；引用与 finish_reason 校验保持有效，未知 usage 保守结算。
- AC-3: schema 指令在发送前计入完整输入预算；输入不适配时不调用模型，现有在线链复用同一适配，无新增客户端或生产 probe 旁路。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-deepseek-chat-compatibility.json](../../verification/evidence/20260906-deepseek-chat-compatibility.json)

SHA-256: `df4169121effd6916caa787f8a61abfbee69029cfccf3f286eba44e02ea03e29`

Closed at 2026-09-06T11:39:59.531405+00:00.
