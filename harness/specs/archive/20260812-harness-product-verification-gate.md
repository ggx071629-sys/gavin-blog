---
id: archive-20260812-harness-product-verification-gate
level: L2
summary: 让 task verify 运行白名单产品门禁，并让 close 强制消费当前提交的完整验收证据
load_when:
  - task:20260812-harness-product-verification-gate
author: Codex
task_id: 20260812-harness-product-verification-gate
status: compressed
state_history:
---

# 20260812-harness-product-verification-gate

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立可执行、可审计的 task verification：active spec 显式把每项验收标准映射到配置白名单 gate，`verify <task_id>` 在已提交源码上运行这些 gate 并生成紧凑 evidence，`close <task_id>` 只在 evidence 完整、通过且对应当前 HEAD 时才允许压缩。

## Acceptance criteria

- AC-1: 新 active spec 的验收标准使用唯一 `AC-N` 标识，Verification plan 使用确定性 `gate => AC` 语法；未知 gate、重复或未覆盖验收项使 task verify 失败。
- AC-2: 产品 gate 仅来自 `config.toml` 白名单，使用参数数组和受控工作目录运行；evidence 记录命令、状态、耗时、覆盖项与当前 source commit，不保存重型原始日志。
- AC-3: task verify 在验证范围存在未提交源码、spec 未进入 Git HEAD、任务 frozen 或任一 gate 失败时返回失败，且不能生成可用于 close 的 passed evidence。
- AC-4: close 在任何写入前拒绝缺失、格式错误、失败、覆盖不全、source commit 过期或验证范围已变化的 evidence；成功 close 保留 task evidence，不用结构检查结果覆盖它。
- AC-5: 全局 `verify`、freeze/resume、历史 compressed evidence 与 frozen spec 行为保持兼容，关闭仍具备失败回滚和前后 Harness 完整性检查。
- AC-6: spec 模板、verify 工作流、生命周期与 verification policy 明确记录新的先提交 spec、提交实现、task verify、close 顺序。

## Result

Verified and closed by the harness close command.

## Evidence

[20260812-harness-product-verification-gate.json](../../verification/evidence/20260812-harness-product-verification-gate.json)

Closed at 2026-08-12T02:47:38.451754+00:00.
