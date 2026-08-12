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
- Task verify：`python -m tools.harness verify <task_id>` 解析 spec 的 `gate => AC` 映射，只运行 `config.toml` 白名单 gate；未知 gate、缺少 profile 最低 gate、失败 gate 或未覆盖 AC 均失败。
- Profiles：`focused` 由 spec 选择相关 gate；`stack` 至少覆盖 API lint、API tests 与 Web quality；`release` 必须运行完整 release gate。
- Isolation：task verify 默认把当前 HEAD 检出到 detached 临时 Git worktree，受控链接本地 `node_modules` 与 API `.venv` 后运行 gate；不安装依赖，也不在隔离失败时退回共享工作目录。成功、失败或超时后都先移除链接再注销 worktree，清理失败会让 evidence 失败。
- Complete when：passed evidence 对应当前 HEAD，且 source tree、active spec、规范化验证合同、profile/gate 配置指纹仍匹配；此时任务派生为 verified，否则仍是 active 并明确报告失败。
