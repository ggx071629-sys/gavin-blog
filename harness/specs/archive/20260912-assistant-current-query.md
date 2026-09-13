---
id: archive-20260912-assistant-current-query
level: L2
summary: 让当前问题优先进入普通与 E5 检索的最终词法表达式
load_when:
  - task:20260912-assistant-current-query
author: Codex
task_id: 20260912-assistant-current-query
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录当前问题优先、最近历史后置、有限词项预算和未实现语义消解的边界。
evidence_sha256: da0853779f0155401f73c0089db52d029d5187b1abe8013900f2bf657073ad72
state_history:
---

# 20260912-assistant-current-query

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让当前问题先占用检索预算，最近历史使用剩余空间，最终精确、宽松和旧式 MATCH 保留当前问题词项。

## Acceptance criteria

- AC-1: 普通与 E5 查询在长历史、换题和指代样例中，最终三种 MATCH 都保留当前问题的有效词项；短指代问题仍可保留最近主题，真实 FTS 表可命中当前术语。
- AC-2: 字符与 E5 token 限制、超长词法降级、向量指纹失效和历史 query 不进入 checkpoint 的保护继续通过；API 文档说明有限范围。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-current-query.json](../../verification/evidence/20260912-assistant-current-query.json)

SHA-256: `da0853779f0155401f73c0089db52d029d5187b1abe8013900f2bf657073ad72`

Closed at 2026-09-12T05:58:26.532745+00:00.
