---
id: archive-20260912-assistant-reference-context
level: L2
summary: Q4-03 有限来源指代、换题隔离和专用澄清
load_when:
  - task:20260912-assistant-reference-context
author: Codex
task_id: 20260912-assistant-reference-context
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 说明有限来源指代、专用澄清、历史不作为事实及未覆盖语言。
evidence_sha256: 4dc7b7103035513e1a3bc86dbd345a58b24dfa23e6c4a02c7a777ee5232b19d6
state_history:
---

# 20260912-assistant-reference-context

Deterministic compressed record. The original active spec remains in Git history.

## Goal

仅将上一有效回答唯一且当前可用的公开来源用作对象线索；重新检索，未知对象先澄清，换题不带旧问答。

## Acceptance criteria

- AC-1: 有限中英指代可由上一回答唯一公开来源辅助检索与提示，当前问题保留；旧问答正文不进入新提示，旧来源撤销不能继续被解析。
- AC-2: 缺少、多个、序号或TTL失效对象返回 clarification_required 专用终态，零Chat/Embedding调用；换题只查当前问题。
- AC-3: 浏览器独立显示并恢复澄清提示，不显示证据不足或操作失败；已有多编号场景按已实施的逐卡定位预期回归。
- AC-4: 记录有限范围与残余限制，不声称通用多轮成功或生产资格。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-reference-context.json](../../verification/evidence/20260912-assistant-reference-context.json)

SHA-256: `4dc7b7103035513e1a3bc86dbd345a58b24dfa23e6c4a02c7a777ee5232b19d6`

Closed at 2026-09-12T15:03:25.343279+00:00.
