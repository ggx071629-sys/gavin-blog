---
id: archive-20260906-local-chat-probe
level: L2
summary: 复用现有资格探测与预算账本执行有界本机 Chat 验证
load_when:
  - task:20260906-local-chat-probe
task_id: 20260906-local-chat-probe
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录显式本机探测命令、既有预算复用及与生产资格隔离。
evidence_sha256: badc4e23f52fcf8cc3f6e71a55702192657bef24d1360d9d2876f11216268f39
state_history:
---

# 20260906-local-chat-probe

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在既有 provider_probe 中增加显式 development-only Chat 探测入口，复用原 _chat_probe、预留/结算及同一账本实现。用独立本机预算绑定替代不相关的生产部署资料，绝不产生生产资格证明。填充经官方文档核对的非秘密本机配置并执行有界真实验证。

## Acceptance criteria

- AC-1: 只有development、官方DeepSeek端点、非空版本及明确的token/price/timeout/budget配置允许本机探测；失败前置条件不发请求。本机结果明确scope且不能通过生产artifact校验。
- AC-2: 本机探测复用既有文件锁、原子预留与结算，输入schema指令计入预算，未知usage保守结算；预算或配置漂移/额度耗尽不再发送请求。JSON应用schema与供应商strict_schema分别记录，模型不匹配不得通过。
- AC-3: 既有生产探测继续要求production/profile绑定，保持严格schema协议、usage与版本合同及原有预算测试通过；脱敏manifest无Key或原始响应。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-local-chat-probe.json](../../verification/evidence/20260906-local-chat-probe.json)

SHA-256: `badc4e23f52fcf8cc3f6e71a55702192657bef24d1360d9d2876f11216268f39`

Closed at 2026-09-06T11:47:01.066538+00:00.
