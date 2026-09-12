---
id: archive-20260912-assistant-retrieval-io
level: L2
summary: 将在线同步查询 Embedding 与检索隔离到有界执行器
load_when:
  - task:20260912-assistant-retrieval-io
author: Codex
task_id: 20260912-assistant-retrieval-io
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录检索线程容量、取消后的结算和关闭等待边界，区分合成延迟与生产性能。
evidence_sha256: 76561cb02dceb9c72c52c7eba4e03e439955869b26f96b0e07c470d7669ba962
state_history:
---

# 20260912-assistant-retrieval-io

Deterministic compressed record. The original active spec remains in Git history.

## Goal

慢检索期间事件循环及其他会话可继续运行；执行器容量有界，取消不提前释放正在工作的线程槽，停止运行时先等待迟到结算再关闭控制数据库和 owner lock。

## Acceptance criteria

- AC-1: 受控慢 Embedding 和检索期间，实际应用事件循环、会话读取及心跳可运行；正常回答保持可用，工作线程不超过现有 Embedding 并发配置。
- AC-2: 排队取消不发请求；执行中取消不提前释放线程槽；关闭等待已发送工作完成并拒绝新工作。删除会话后迟到 Embedding 不写正文、向量、历史或 checkpoint，不重复结算或调用聊天。
- AC-3: 原始身份围栏、供应商迟到结果和状态 descriptor 边界通过适用回归；文档明确容量及关闭等待限制。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-retrieval-io.json](../../verification/evidence/20260912-assistant-retrieval-io.json)

SHA-256: `76561cb02dceb9c72c52c7eba4e03e439955869b26f96b0e07c470d7669ba962`

Closed at 2026-09-12T12:38:58.638325+00:00.
