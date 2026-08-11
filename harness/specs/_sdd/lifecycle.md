---
id: sdd-lifecycle
level: L1
summary: Active spec 从创建、验证到压缩归档的状态转换
load_when:
  - spec-create
  - spec-close
author: Gavin
---

# Spec lifecycle

状态顺序：`draft → active → verified → compressed`。

- Draft：问题、目标与边界尚在收敛。
- Active：验收标准明确，可以实现。
- Verified：相关自动化 checks 已通过并产生 evidence。
- Compressed：当前工作树只保留目标、关键决策、结果和证据链接。

关闭必须使用 `python -m tools.harness close <task_id>`。任一步失败时 active spec 保持不变。

关闭前必须能从精确的 H1 或 H2 `Goal` 与 `Acceptance criteria` 章节提取非空内容；否则 close 失败并回滚，禁止以 `Not recorded` 代替关键归档信息。普通 close 记录 `spec.completed` event，但不自动生成无具体改进内容的 Evolution proposal；proposal 只由显式、带理由的 event 进入人工审阅。

## Durable references

`specs/active/` 是短生命周期工作区，spec 关闭后原路径必然消失。README、L1/L2 文档以及其他长期 Markdown 不得直接链接 active spec；需要稳定入口时链接生成的 `harness/specs/INDEX.md`，需要解释长期决策时链接 `harness/docs/decisions/`。只有 active spec 之间的临时协调引用可以直接指向 `specs/active/`。
