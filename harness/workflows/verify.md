---
id: workflow-verify
level: L1
summary: 用 VDD 与机器证据验证变更，而非依赖自然语言自证
load_when:
  - verification
  - implementation
author: Gavin
---

# Verify

- Input：实现、验收标准与相关 VDD 指南。
- Preconditions：active spec 与实现已提交；验证范围没有未提交源码；检查命令可重复执行。
- Output：checks 结果与 schema v2 紧凑 task evidence。
- Checks：TDD、Contract、Integration、E2E、Quality 中与风险相关的部分。
- Frozen：全局门禁校验冻结不变量但不因合法冻结失败；任务级 verify 必须先恢复该 spec。
- Task verify：`python -m tools.harness verify <task_id>` 解析 spec 的 `gate => AC` 映射，只运行 `config.toml` 白名单 gate；未知 gate、失败 gate 或未覆盖 AC 均失败。
- Complete when：passed evidence 对应当前 HEAD，且证据支持每项验收标准；否则明确报告失败。
