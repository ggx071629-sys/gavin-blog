---
id: spec-20260911-index-integrity
level: L1
summary: 修复多代 FTS 相互删除，增加逐层一致性门禁并定向补齐本机索引
load_when:
  - task:20260911-index-integrity
author: Gavin
task_id: 20260911-index-integrity
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录跨代 FTS 隔离、完整性审计与受控修复入口及验收边界。
state_history:
---

# Context

真实内容库 active 第14代有25个规范切片及向量，但FTS仅9条；缺失16条在第15代具有同ID和正文。fts.py 按不含 generation 的稳定 chunk_id 删除，导致 staging 写入覆盖 active FTS。此前清理任务将其列遗留后关闭，不能作为完整性证据。用户已授权修复、从现存数据补齐并完整验收。

# Goal

按代次隔离所有 FTS 更新/删除；从当前公开投影及原切片规则独立推导应收录集合，逐条比对规范切片、FTS和Qdrant绑定/向量。实际启动验收、构建完成及切换前遇到不一致必须失败。提供默认只读审计与显式有备份、持内容写围栏的FTS定向修复，完成本机数据对账和检索验收。

# Non-goals

不重新计算/写入向量，不调用付费Chat，不创建/切换generation，不修改内容、历史任务、费用或预算，不把有限回答覆盖等同全部资料收录，不部署。不得以同数量、retrieve.status=ok 或旧证据替代逐条完整性。

# Acceptance criteria

- AC-1: 对相同chunk_id的多代构建、更新、删除和代次清理互不破坏；旧代FTS关键词仍能检索，永久删除的现有跨代调用边界保留。
- AC-2: 审计独立枚举当前公开来源并重算切片身份/正文，检测缺失、额外、重复、错版本、错正文及向量ID/payload/维度/有限值；FTS与Qdrant查询失败不得视为通过。本机真实启动、rebuild ready及finalize以审计失败阻断。
- AC-3: 显式FTS补齐仅在规范切片与向量完整、备份成功且持有写围栏时事务执行，失败回滚；不改变内容、代次、其他代FTS、向量与费用，重复修复无新增变化。真实库补齐后逐层零差异，真实检索/引用/PDF和GSAP验收通过，原遗留记录补充解决结果并确定性归档。

# Risks

数量相同仍可能身份错配；跨代相同ID是合法情况。不能使用usable_version导致的索引依赖隐藏缺失简历，预期来源必须来自公开事实。审计需要固定内容快照，向量读失败要fail closed；在线请求不能逐次全库扫描。维护过程保留真实库、Qdrant摘要及备份，不清账本或重试旧任务。

# Verification plan

## Verification cases

- AC-1 => M10-UNIT-INDEX-INTEGRITY-01, M10-UNIT-ASSISTANT-INDEX-01, M10-RESUME-INDEX-01, M10-VECTOR-REUSE-01, M10-VECTOR-REUSE-02
- AC-2 => M10-UNIT-INDEX-INTEGRITY-01, M09-READINESS-AGE-01, M10-E5-LOCAL-01, M10-EVAL-ISOLATION-01, M10-CAPACITY-ISOLATION-01
- AC-3 => M10-UNIT-INDEX-INTEGRITY-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
