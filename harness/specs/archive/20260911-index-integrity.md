---
id: archive-20260911-index-integrity
level: L2
summary: 修复多代 FTS 相互删除，增加逐层一致性门禁并定向补齐本机索引
load_when:
  - task:20260911-index-integrity
author: Gavin
task_id: 20260911-index-integrity
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录跨代 FTS 隔离、完整性审计与受控修复入口及验收边界。
evidence_sha256: c2bad8e9f359c246c7bdf46cc7e53dfed89b652570c32e634965caa4596ccb49
state_history:
---

# 20260911-index-integrity

Deterministic compressed record. The original active spec remains in Git history.

## Goal

按代次隔离所有 FTS 更新/删除；从当前公开投影及原切片规则独立推导应收录集合，逐条比对规范切片、FTS和Qdrant绑定/向量。实际启动验收、构建完成及切换前遇到不一致必须失败。提供默认只读审计与显式有备份、持内容写围栏的FTS定向修复，完成本机数据对账和检索验收。

## Acceptance criteria

- AC-1: 对相同chunk_id的多代构建、更新、删除和代次清理互不破坏；旧代FTS关键词仍能检索，永久删除的现有跨代调用边界保留。
- AC-2: 审计独立枚举当前公开来源并重算切片身份/正文，检测缺失、额外、重复、错版本、错正文及向量ID/payload/维度/有限值；FTS与Qdrant查询失败不得视为通过。本机真实启动、rebuild ready及finalize以审计失败阻断。
- AC-3: 显式FTS补齐仅在规范切片与向量完整、备份成功且持有写围栏时事务执行，失败回滚；不改变内容、代次、其他代FTS、向量与费用，重复修复无新增变化。真实库补齐后逐层零差异，真实检索/引用/PDF和GSAP验收通过，原遗留记录补充解决结果并确定性归档。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-index-integrity.json](../../verification/evidence/20260911-index-integrity.json)

SHA-256: `c2bad8e9f359c246c7bdf46cc7e53dfed89b652570c32e634965caa4596ccb49`

Closed at 2026-09-11T13:02:54.853305+00:00.
