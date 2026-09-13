---
id: archive-20260831-article-slug-validation
level: L2
summary: 阻止新建文章提交无效标题或 slug，并向管理员显示可操作的字段错误
load_when:
  - task:20260831-article-slug-validation
author: Codex
task_id: 20260831-article-slug-validation
status: compressed
documentation_impact: none
documentation_reason: 本任务修复既有 ASCII slug 合同下的表单校验与错误反馈，不改变长期产品、架构、API 或运维边界。
state_history:
---

# 20260831-article-slug-validation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在保持现有后端 ASCII slug 与稳定 URL 合同不变的前提下，让新建文章页在客户端阻止无效标题或 slug，并提供明确、可访问且可操作的字段错误；合法表单仍可创建草稿。

## Acceptance criteria

- AC-1: 空标题、空 slug 或不符合小写字母/数字/单连字符规则的 slug 在客户端被阻止提交，并在对应字段附近显示可访问错误。
- AC-2: 纯中文标题自动生成空 slug 时，页面明确要求填写英文或拼音 slug，不再产生 `POST /api/v1/admin/articles` 422 请求。
- AC-3: 合法标题与 slug 仍能提交创建草稿；服务端拒绝的创建请求保留可见反馈，而不是静默失败。

## Result

Verified and closed by the harness close command.

## Evidence

[20260831-article-slug-validation.json](../../verification/evidence/20260831-article-slug-validation.json)

Closed at 2026-08-31T11:19:12.848795+00:00.
