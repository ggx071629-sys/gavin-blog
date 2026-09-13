---
id: archive-20260911-assistant-about-citations
level: L2
summary: Q2-04 开放关于页安全引用并明确自述与冲突提示规则
load_when:
  - task:20260911-assistant-about-citations
task_id: 20260911-assistant-about-citations
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
documentation_reason: 同步关于页引用白名单、个人事实与冲突处理边界。
evidence_sha256: 4a12c79be0b35f978cae5fc258d59816f5834677e3f820ddcdc180696dd147ed
state_history:
---

# 20260911-assistant-about-citations

Deterministic compressed record. The original active spec remains in Git history.

## Goal

只开放 /about 精确引用路径，在公开问答和管理试问可点击；明确关于页自述及资料冲突规则。

## Acceptance criteria

- AC-1: 公开回答和管理试问显示“关于 Gavin”并可打开 /about，错误外部路径仍拒绝。
- AC-2: 提示词允许关于页明确自述，保留文章主题不得冒充能力与不夸大规则；矛盾事实要求引用双方，引用仍只由 evidence alias 生成。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-about-citations.json](../../verification/evidence/20260911-assistant-about-citations.json)

SHA-256: `4a12c79be0b35f978cae5fc258d59816f5834677e3f820ddcdc180696dd147ed`

Closed at 2026-09-10T17:24:00.585180+00:00.
