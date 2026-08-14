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
- Preconditions：active spec 与实现已提交；验证范围和已声明文档目标没有未提交修改；检查命令可重复执行。
- Output：checks 结果与 schema v2 紧凑 task evidence。
- Checks：TDD、Contract、Integration、E2E、Quality 中与风险相关的部分。
- Frozen：全局门禁校验冻结不变量但不因合法冻结失败；任务级 verify 必须先恢复该 spec。
- Documentation：非冻结 active spec 必须声明 `documentation_impact` 与理由。`required` 的每个安全 Markdown 目标必须存在于 HEAD，并在 spec 首次提交之后有已提交变更；`none` 不得列目标。检查失败时不启动产品 gate，也不能产生可关闭的 passed evidence。
- Task verify：`python -m tools.harness verify <task_id>` 先验证文档影响契约与映射政策，再解析 spec 的 `gate => AC` 映射并只运行 `config.toml` 白名单 gate；系统同时从 spec 首次提交后的已提交路径推导最低 gate，spec 可以增加但不能降低该下限。多条 AC 不能只映射到 `release` 一类包门禁；高于下限的包门禁需要 `verification_escalation`。未知 gate、缺少 profile 或风险路由最低 gate、失败 gate 或未覆盖 AC 均失败。失败且本地已有两个 failed run 时打印 `emit-event` 命令，不自动写 Evolution。
- Profiles：`focused` 由 spec 选择相关 gate；`stack` 至少覆盖 API lint、API tests 与 Web quality；`release` 必须运行完整 release gate。
- Isolation：task verify 默认把当前 HEAD 检出到 detached 临时 Git worktree，受控链接本地 `node_modules` 与 API `.venv` 后运行 gate；不安装依赖，也不在隔离失败时退回共享工作目录。成功、失败或超时后都先移除链接再注销 worktree，清理失败会让 evidence 失败。
- Reporting：gate evidence 结构化记录退出码、耗时、可识别测试数量与失败类型；顶层 summary 可由 checks 重算。失败日志只保留一条有限净化摘要。
- Complete when：passed evidence 对应当前 HEAD，且 source tree、active spec、规范化验证合同、文档契约与目标 blob、profile/gate 配置指纹仍匹配；此时任务派生为 verified，否则仍是 active 并明确报告失败。
