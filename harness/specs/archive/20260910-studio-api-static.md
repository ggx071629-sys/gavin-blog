---
id: archive-20260910-studio-api-static
level: L2
summary: 补齐列表查询的类型和格式静态检查
load_when:
  - task:20260910-studio-api-static
task_id: 20260910-studio-api-static
status: compressed
documentation_impact: none
documentation_reason: 仅排序导入、格式化既有表达式和显式解包 SQLAlchemy Row，不改变持久产品契约；阶段归档记录验收事实。
evidence_sha256: 48e4f7e00e215c6c394afd40c4ab687e5e0eb04f5daeb9382534541015695f84
state_history:
---

# 20260910-studio-api-static

Deterministic compressed record. The original active spec remains in Git history.

## Goal

恢复 API 全量 Ruff 与 Mypy，通过实际查询回归证明等价修复。

## Acceptance criteria

- AC-1: 三类后台查询保留鉴权、查询后计数、转义搜索、稳定分页和公开边界，静态修复不改变用户可见结果。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-api-static.json](../../verification/evidence/20260910-studio-api-static.json)

SHA-256: `48e4f7e00e215c6c394afd40c4ab687e5e0eb04f5daeb9382534541015695f84`

Closed at 2026-09-10T13:22:36.149380+00:00.
