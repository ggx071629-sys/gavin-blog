---
id: archive-20260912-markdown-line-endings
level: L2
summary: Markdown 导入兼容 CRLF 换行且不放宽既有 front matter 校验
load_when:
  - task:20260912-markdown-line-endings
author: Codex
task_id: 20260912-markdown-line-endings
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: API 文档记录了导入的批次与 front matter 校验契约，需要补充解析前统一换行的行为。
evidence_sha256: 1fcf82995ef2ce07bc08eb7225439f88d9c430c7d735b91cc7d76a12fb4973ee
state_history:
---

# 20260912-markdown-line-endings

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让同一内容的 LF 与 CRLF 文件得到一致的元数据、正文与仅创建草稿的结果，同时保持既有 front matter、YAML、编码与批次校验不变。

## Acceptance criteria

- AC-1: 同一内容的 LF/CRLF 文件导入得到一致的元数据、正文（不含 CR）与草稿状态。
- AC-2: 既有校验不放宽：缺少或未闭合 front matter、YAML 别名、非法 YAML 与非 UTF-8 仍被拒绝。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-markdown-line-endings.json](../../verification/evidence/20260912-markdown-line-endings.json)

SHA-256: `1fcf82995ef2ce07bc08eb7225439f88d9c430c7d735b91cc7d76a12fb4973ee`

Closed at 2026-09-12T04:56:40.116624+00:00.
