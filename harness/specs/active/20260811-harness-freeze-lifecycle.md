---
id: spec-20260811-harness-freeze-lifecycle
level: L1
summary: 将人工冻结与恢复固化为可审计且受门禁约束的 Harness 生命周期
load_when:
  - task:20260811-harness-freeze-lifecycle
author: Codex
task_id: 20260811-harness-freeze-lifecycle
status: active
state_history:
  - {"action":"freeze","at":"2026-08-11T12:47:09.983301+00:00","reason":"Self-test the enforced frozen task gate before release verification.","scope_sha256":"e5593942d7d068e079d81b352caa54d420ce136081962ae11b45c5b7d597125e"}
  - {"action":"resume","at":"2026-08-11T12:47:54.896783+00:00","reason":"The frozen verify and close gates passed their self-test."}
---

# Context

Harness 中已有两份通过 `status: frozen`、`frozen_at` 和 `freeze_reason` 手工冻结的 active spec，也有对应的持久决策，但当前生命周期、CLI、索引和校验器都不理解冻结语义。冻结任务仍可被任务级验证写成通过证据，也可能进入关闭流程；索引无法区分正在推进与冻结中的任务，核心验收契约也没有可执行的完整性保护。

本次需求已通过逐项确认收敛。冻结是人工选择的可选暂停状态，不是每个 spec 的必经阶段，也不是全局质量失败。实现需要改变 Harness 生命周期行为和质量门槛，因此按 SDD 管理。

# Goal

为 active spec 建立确定性的 `active → frozen → active` 可选生命周期：人工命令负责冻结与恢复、追加完整状态历史并更新索引；冻结任务不能取得任务级验证成功或被关闭，但不拖红全局门禁；冻结期间核心目标、边界、验收标准和验证计划由摘要保护，历史手工冻结任务以明确的迁移基线纳入新机制。

# Non-goals

- 不让所有 spec 必须经过冻结状态。
- 不根据测试失败、依赖缺失、超时或外部系统状态自动冻结或恢复。
- 不阻止创建和推进与冻结范围无关的独立 spec。
- 不声称 Harness 能可靠识别所有代码修改属于哪个 spec。
- 不提供 `--force` 或其他绕过冻结直接验证、关闭的后门。
- 不部署、不推送，也不修改应用业务代码。

# Acceptance criteria

1. CLI 提供 `freeze <task_id> --reason ...` 与 `resume <task_id> --reason ...`；原因非空，只有 `active → frozen` 和 `frozen → active` 合法，重复或非法转换明确失败。
2. 冻结与恢复均由人工显式执行，不要求完整质量门禁预先通过，也不自动判断外部阻塞是否解除；命令原子更新 spec、追加 UTC 状态历史并重建索引，失败时不留下部分修改。
3. 冻结时记录 `Goal`、`Non-goals`、`Acceptance criteria` 与 `Verification plan` 的确定性 SHA-256 摘要；全局校验允许合法冻结存在，但核心契约被改写、状态与历史不一致或冻结元数据不完整时失败。
4. `verify <frozen-task-id>` 明确以非零状态报告任务被冻结，且不得生成成功证据；无 task ID 的全局 `verify` 仍可在所有冻结不变量合法时通过。
5. `close <frozen-task-id>` 在任何归档、事件或证据写入前失败；不存在强制绕过。需要修改核心契约或继续验收时必须先恢复。
6. Specification Index 单独显示状态与 active/frozen 数量；冻结 spec 保留在 `specs/active/`，但不计入正在推进的 active 数量。
7. `20260807-github-source-crawler` 与 `20260807-github-discovery-ingestion` 保持冻结，保留原冻结日期和原因；迁移记录明确标记摘要是在迁移时建立，不能伪称具备历史完整性证明。
8. 生命周期政策、模板和持久决策描述命令、门禁、恢复及迁移语义；现有关闭行为、Evolution 事件分离和索引确定性不回退。

# Risks

- 前置元数据解析器只支持简单标量与列表；状态历史格式必须保持确定性并能被现有工具安全读取。
- 若摘要覆盖范围过宽，会阻止合法补充备注和证据；过窄则无法保护验收基线。
- 冻结命令的多文件更新若中途失败，可能造成 spec 与索引不一致，必须回滚源文件并重建索引。
- 两份历史 spec 没有冻结时摘要，只能建立迁移时基线，必须避免伪造追溯能力。

# Verification plan

1. 为合法转换、非法转换、原因校验、追加历史、核心摘要、冻结任务 verify/close 拒绝和命令回滚添加生命周期单元测试。
2. 为合法冻结、缺失元数据、历史不一致、核心内容漂移及 active 状态残留冻结字段添加元数据检查测试。
3. 验证 Specification Index 的状态列和 active/frozen 统计确定性。
4. 运行 `python -m pytest verification/tests -q`、`python -m tools.harness index`、`python -m tools.harness verify 20260811-harness-freeze-lifecycle`。
5. 运行项目完整 `quality:release`；通过后提交 active spec 与实现，再使用确定性 close 命令关闭并复跑最终 Harness 门禁。
