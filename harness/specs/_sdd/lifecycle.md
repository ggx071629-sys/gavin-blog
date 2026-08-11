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

正常状态顺序：`draft → active → verified → compressed`。人工暂停可以走可选分支：`active → frozen → active`；冻结不是所有 spec 的必经状态，也不是关闭。

- Draft：问题、目标与边界尚在收敛。
- Active：验收标准明确，可以实现。
- Frozen：任务尚未关闭，但当前不推进；文件继续留在 `specs/active/`，不计入正在推进的 active 数量。
- Verified：相关自动化 checks 已通过并产生 evidence。
- Compressed：当前工作树只保留目标、关键决策、结果和证据链接。

冻结与恢复只能由人工显式执行：

- `python -m tools.harness freeze <task_id> --reason "..."`
- `python -m tools.harness resume <task_id> --reason "..."`

原因必须非空，状态转换必须严格匹配当前状态，不提供强制绕过。命令追加 UTC 状态历史并重建索引；冻结不要求完整质量门禁先通过，恢复也不自动判断外部阻塞是否解除。

冻结时 Harness 对 `Goal`、`Non-goals`、`Acceptance criteria` 和 `Verification plan` 建立确定性摘要。备注、阻塞信息和证据可以继续补充；核心契约如需改变，必须先恢复。合法冻结不会拖红无 task ID 的全局 verify 或 release 门禁，但 `verify <frozen-task-id>` 不能生成成功结论，`close <frozen-task-id>` 必须在产生归档、事件或证据前失败。

关闭必须使用 `python -m tools.harness close <task_id>`。任一步失败时 active spec 保持不变。

关闭前必须能从精确的 H1 或 H2 `Goal` 与 `Acceptance criteria` 章节提取非空内容；否则 close 失败并回滚，禁止以 `Not recorded` 代替关键归档信息。普通 close 记录 `spec.completed` event，但不自动生成无具体改进内容的 Evolution proposal；proposal 只由显式、带理由的 event 进入人工审阅。

## Durable references

`specs/active/` 是短生命周期工作区，spec 关闭后原路径必然消失。README、L1/L2 文档以及其他长期 Markdown 不得直接链接 active spec；需要稳定入口时链接生成的 `harness/specs/INDEX.md`，需要解释长期决策时链接 `harness/docs/decisions/`。只有 active spec 之间的临时协调引用可以直接指向 `specs/active/`。
