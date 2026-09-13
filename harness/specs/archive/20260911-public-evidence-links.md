---
id: archive-20260911-public-evidence-links
level: L2
summary: 修复公开教程的凭据管理链接被误判导致证据遗漏
load_when:
  - task:20260911-public-evidence-links
task_id: 20260911-public-evidence-links
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明完整收录与证据隔离边界及公开文档链接的处理。
evidence_sha256: af393a7c6d654b5a8f5fa2ace1f3f44dbfb04166b7902e6bea88e37137e759de
state_history:
---

# 20260911-public-evidence-links

Deterministic compressed record. The original active spec remains in Git history.

## Goal

证据扫描允许普通HTTP(S)文档链接路径中的凭据名称，保留实际凭据值、指令注入及泄密指令拦截；用户问题规则保持原样。

## Acceptance criteria

- AC-1: 普通凭据管理文档链接不隔离正文，真实检索可返回原被隔离配置步骤。
- AC-2: 链接内外的实际密钥和泄密指令仍被隔离，用户输入的原有拒绝行为保持。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-public-evidence-links.json](../../verification/evidence/20260911-public-evidence-links.json)

SHA-256: `af393a7c6d654b5a8f5fa2ace1f3f44dbfb04166b7902e6bea88e37137e759de`

Closed at 2026-09-11T04:17:45.158248+00:00.
