---
id: archive-20260912-assistant-retry-feedback
level: L2
summary: Q3-03 区分输出失败并为有界重试提供无正文反馈
load_when:
  - task:20260912-assistant-retry-feedback
task_id: 20260912-assistant-retry-feedback
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确重试反馈、失败原因及费用与隐私边界。
evidence_sha256: 631cc3b8fe8d4459fa8862e9e4b1cad0483efe4bc86068057c29544de6844f35
state_history:
---

# 20260912-assistant-retry-feedback

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为已有最多两次生成提供固定原因反馈并持久化无正文的阶段分类。

## Acceptance criteria

- AC-1: 输出校验失败的第二次请求包含固定结构化原因，反馈进入输入预算，不复制失败正文。
- AC-2: 格式/支持失败、缺证据和供应商未知可区分；未知调用不重发，重试仍最多两次且幂等恢复不新增调用。
- AC-3: 运行文档说明有限纠正能力、后台原因及累计预算不变。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-retry-feedback.json](../../verification/evidence/20260912-assistant-retry-feedback.json)

SHA-256: `631cc3b8fe8d4459fa8862e9e4b1cad0483efe4bc86068057c29544de6844f35`

Closed at 2026-09-12T13:22:24.929878+00:00.
