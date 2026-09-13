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

持久状态顺序：`draft → active → compressed`。人工暂停可以走可选分支：`active → frozen → active`；冻结不是所有 spec 的必经状态，也不是关闭。`verified` 是由当前有效 evidence 推导出的临时状态，不写入 front matter：任何源码、spec、验证合同、profile、gate 配置或 HEAD 漂移都会让任务重新表现为 active。

- Draft：问题、目标与边界尚在收敛。
- Active：验收标准明确，可以实现。
- Frozen：任务尚未关闭，但当前不推进；文件继续留在 `specs/active/`，不计入正在推进的 active 数量。
- Verified（派生）：active spec 与实现已进入 Git HEAD，相关白名单产品 gate 和 Harness checks 已通过，最后 attempts 与清理均合格，并产生本机认证的覆盖全部 AC 且指纹仍匹配的当前提交 evidence。
- Compressed：当前工作树只保留目标、关键决策、结果和证据链接。

冻结与恢复只能由人工显式执行：

- `python -m tools.harness freeze <task_id> --reason "..."`
- `python -m tools.harness resume <task_id> --reason "..."`

原因必须非空，状态转换必须严格匹配当前状态，不提供强制绕过。命令追加 UTC 状态历史并重建索引；冻结不要求完整质量门禁先通过，恢复也不自动判断外部阻塞是否解除。

冻结时 Harness 对 `Goal`、`Non-goals`、`Acceptance criteria` 和 `Verification plan` 建立确定性摘要。备注、阻塞信息和证据可以继续补充；核心契约如需改变，必须先恢复。合法冻结不会拖红无 task ID 的全局 verify 或 release 门禁，但 `verify <frozen-task-id>` 不能生成成功结论，`close <frozen-task-id>` 必须在产生归档、事件或证据前失败。

关闭必须经过确定性 CLI 生命周期。从 `harness/` 执行；当前默认关闭复用，普通有测试任务使用 `python -m tools.harness verify <task_id> --close` 同进程完成验证与关闭。独立 `python -m tools.harness close <task_id>` 仍存在，但未登记完整安装依赖闭包时不能跨进程关闭，不能把单独运行 verify 再 close 作为通用流程。close 在任何写入前校验本机 HMAC 认证的 schema v2 task evidence，不启动产品 gate 或 collector：状态必须通过、覆盖当前 spec 全部 AC、产品 gate 必须与验证计划一致、source commit 必须等于 HEAD，且配置的验证源码范围不能存在未提交变更。任一步失败时 active spec 保持不变；close 保留 verify 产生的 evidence，不用结构检查结果覆盖产品证据。

派生 verified 还要求 evidence 的隔离执行上下文对应当前提交，且临时 Git worktree 清理状态为 passed；共享工作目录执行或残留未清理的隔离环境都不能关闭。

满足跨进程认证与输入合同前提时，批量关闭使用 `python -m tools.harness close-all`；它不绕过上述限制。该命令明确跳过 frozen spec，先统一验证所有 active evidence 和 Harness 完整性，再一次性生成归档与事件；任一变更或后验检查失败时整批回滚，不保留部分关闭结果。

关闭前可运行 `python -m tools.harness status [task_id] [--json]` 只读查看派生状态；frozen 不触发 evidence 校验。`python -m tools.harness close-all --dry-run` 复用真实批量关闭的 evidence、目标冲突和 Harness 前置检查，但不写 spec、archive、event、evidence 或索引。

关闭前必须能从精确的 H1 或 H2 `Goal` 与 `Acceptance criteria` 章节提取非空内容；否则 close 失败并回滚，禁止以 `Not recorded` 代替关键归档信息。普通 close 记录 `spec.completed` event，但不自动生成无具体改进内容的 Evolution proposal；proposal 只由显式、带理由的 event 进入人工审阅。

## Durable references

`specs/active/` 是短生命周期工作区，spec 关闭后原路径必然消失。README、L1/L2 文档以及其他长期 Markdown 不得直接链接 active spec；需要稳定入口时链接生成的 `harness/specs/INDEX.md`，需要解释长期决策时链接 `harness/docs/decisions/`。只有 active spec 之间的临时协调引用可以直接指向 `specs/active/`。
