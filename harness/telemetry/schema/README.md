---
id: telemetry-schema
level: L2
summary: 原始 observation-only JSONL 事件的结构定义
load_when:
  - telemetry-implementation
  - telemetry-schema-change
author: Gavin
---

# Telemetry schema

每行必须符合 [telemetry.schema.json](telemetry.schema.json)。Schema 刻意不包含动作建议或决策字段，以维持 observation-only 边界。

当前运行事件约定：

- `task.verification`：`value` 包含 `run_id`、`status`、`duration_ms`、`checks`、可选 `test_counts`、`failure_kinds`、`verification_profile`、`source_commit` 与 `isolation_cleanup`。
- `release.stage`：`value` 包含 `run_id`、稳定 `stage`、`status`、`duration_ms`、`exit_code` 与 `change_coverage`。
- `release.run`：`value` 包含 `run_id`、终态、总耗时、退出码、阶段数与 change coverage 模式。

`status` 使用 `passed`、`failed` 或 `skipped`；`duration_ms` 是非负数。事件生产者不得扩展为日志载体，也不得写入动作或建议字段。通用 JSON schema 保留 `value` 的开放性供未来 observation kind 使用，具体 kind 的稳定字段由本文件约束并由 Harness 测试覆盖。
