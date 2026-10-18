---
id: archive-20260912-assistant-local-model-alias
level: L2
summary: 接受用户确认的本机DeepSeek调用别名并保留身份与累计预算保护
load_when:
  - task:20260912-assistant-local-model-alias
author: Codex
task_id: 20260912-assistant-local-model-alias
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录新别名的本机适用范围和版本声明限制。
evidence_sha256: 998737d8e9381ac43e819f4341cd9bfb4f1eb397701ff7bc93c92c36df2fddfc
state_history:
---

# 20260912-assistant-local-model-alias

Deterministic compressed record. The original active spec remains in Git history.

## Goal

本机配置合同接受用户确认的 deepseek-flash，保留旧名兼容、未知名称拒绝和新配置绑定；新别名的版本依据只作为操作者声明，不伪装供应商版本证明。

## Acceptance criteria

- AC-1: 旧别名仍兼容，新别名在本机development合同中可用且标记声明来源；实际响应模型名称仍须与请求一致；探测正常样例与既有结构化输出 supports 协议一致。
- AC-2: 未批准名称/环境拒绝，新模型改变配置摘要；已有授权不可静默改绑，累计预算与失败恢复保护不回退。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-local-model-alias.json](../../verification/evidence/20260912-assistant-local-model-alias.json)

SHA-256: `998737d8e9381ac43e819f4341cd9bfb4f1eb397701ff7bc93c92c36df2fddfc`

Closed at 2026-09-12T11:24:46.939993+00:00.
