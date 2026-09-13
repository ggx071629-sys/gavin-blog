---
id: archive-20260811-harness-freeze-lifecycle
level: L2
summary: 将人工冻结与恢复固化为可审计且受门禁约束的 Harness 生命周期
load_when:
  - task:20260811-harness-freeze-lifecycle
author: Codex
task_id: 20260811-harness-freeze-lifecycle
status: compressed
state_history:
  - {"action":"freeze","at":"2026-08-11T12:47:09.983301+00:00","reason":"Self-test the enforced frozen task gate before release verification.","scope_sha256":"e5593942d7d068e079d81b352caa54d420ce136081962ae11b45c5b7d597125e"}
  - {"action":"resume","at":"2026-08-11T12:47:54.896783+00:00","reason":"The frozen verify and close gates passed their self-test."}
---

# 20260811-harness-freeze-lifecycle

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为 active spec 建立确定性的 `active → frozen → active` 可选生命周期：人工命令负责冻结与恢复、追加完整状态历史并更新索引；冻结任务不能取得任务级验证成功或被关闭，但不拖红全局门禁；冻结期间核心目标、边界、验收标准和验证计划由摘要保护，历史手工冻结任务以明确的迁移基线纳入新机制。

## Acceptance criteria

1. CLI 提供 `freeze <task_id> --reason ...` 与 `resume <task_id> --reason ...`；原因非空，只有 `active → frozen` 和 `frozen → active` 合法，重复或非法转换明确失败。
2. 冻结与恢复均由人工显式执行，不要求完整质量门禁预先通过，也不自动判断外部阻塞是否解除；命令原子更新 spec、追加 UTC 状态历史并重建索引，失败时不留下部分修改。
3. 冻结时记录 `Goal`、`Non-goals`、`Acceptance criteria` 与 `Verification plan` 的确定性 SHA-256 摘要；全局校验允许合法冻结存在，但核心契约被改写、状态与历史不一致或冻结元数据不完整时失败。
4. `verify <frozen-task-id>` 明确以非零状态报告任务被冻结，且不得生成成功证据；无 task ID 的全局 `verify` 仍可在所有冻结不变量合法时通过。
5. `close <frozen-task-id>` 在任何归档、事件或证据写入前失败；不存在强制绕过。需要修改核心契约或继续验收时必须先恢复。
6. Specification Index 单独显示状态与 active/frozen 数量；冻结 spec 保留在 `specs/active/`，但不计入正在推进的 active 数量。
7. `20260807-github-source-crawler` 与 `20260807-github-discovery-ingestion` 保持冻结，保留原冻结日期和原因；迁移记录明确标记摘要是在迁移时建立，不能伪称具备历史完整性证明。
8. 生命周期政策、模板和持久决策描述命令、门禁、恢复及迁移语义；现有关闭行为、Evolution 事件分离和索引确定性不回退。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-harness-freeze-lifecycle.json](../../verification/evidence/20260811-harness-freeze-lifecycle.json)

Closed at 2026-08-11T13:02:46.599267+00:00.
