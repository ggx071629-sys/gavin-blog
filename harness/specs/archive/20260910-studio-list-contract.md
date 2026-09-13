---
id: archive-20260910-studio-list-contract
level: L2
summary: 补齐后台内容列表搜索筛选计数的真实分页契约
load_when:
  - task:20260910-studio-list-contract
task_id: 20260910-studio-list-contract
status: compressed
documentation_impact: required
documentation_targets:
  - packages/contracts/README.md
documentation_reason: 定义新增管理查询的字段、计数和分页语义。
evidence_sha256: 202c816a2221e7b6012f77e7e5c5b1c48f17f67e30754197f3d0ba3d6ebaa487
state_history:
---

# 20260910-studio-list-contract

Deterministic compressed record. The original active spec remains in Git history.

## Goal

新增已认证 query 端点与共享 Web 消费类型，查询先于分页且计数来自数据库。

## Acceptance criteria

- AC-1: 三类管理查询按标题或书名作者字面包含查询并在分页前筛选状态；计数排除删除内容且按关键词统计，非法参数拒绝，匿名不可访问。
- AC-2: 旧数组接口与公开发布快照分页保持，OpenAPI 与 Web 消费模型同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-list-contract.json](../../verification/evidence/20260910-studio-list-contract.json)

SHA-256: `202c816a2221e7b6012f77e7e5c5b1c48f17f67e30754197f3d0ba3d6ebaa487`

Closed at 2026-09-10T08:13:29.874032+00:00.
