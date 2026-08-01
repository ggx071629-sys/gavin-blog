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

