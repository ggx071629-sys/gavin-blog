---
id: archive-20260811-incubator-batch-lifecycle
level: L2
summary: 为知识孵化三池补齐批量丢弃、安全恢复与概览层级
load_when:
  - task:20260811-incubator-batch-lifecycle
author: Codex
task_id: 20260811-incubator-batch-lifecycle
status: compressed
state_history:
---

# 20260811-incubator-batch-lifecycle

Deterministic compressed record. The original active spec remains in Git history.

## Goal

重排工作台信息层级，并为待处理、审计报告和孵化草稿建立一致、可恢复、部分成功的当前页批量丢弃闭环。

## Acceptance criteria

- 概览按异常与操作、摄入与池状态、健康和历史观察信息分层。
- 移动端五个工作台入口以两行完整呈现，不依赖横向滚动。
- 三池列表使用一致的批量操作栏，只操作当前页明确勾选项；查询、换页或刷新收敛选择。
- 运行中审计、生成或发布项目不可勾选丢弃。
- 批量丢弃二次确认，保存默认原因与可选说明，返回成功数、失败数和逐项失败原因；允许部分成功。
- 已丢弃来源、审计和草稿可逐条恢复。审计和草稿恢复前验证依赖；依赖失效时保持不可继续流转的 stale 状态。
- 永久删除规则保持逐条执行且不扩张。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-incubator-batch-lifecycle.json](../../verification/evidence/20260811-incubator-batch-lifecycle.json)

Closed at 2026-08-12T02:23:00.686167+00:00.
