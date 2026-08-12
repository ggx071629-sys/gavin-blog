---
id: verification-policy
level: L1
summary: VDD 定义方法，checks 执行验证，evidence 保存紧凑结果
load_when:
  - verification
  - harness-change
author: Gavin
---

# Verification policy

`vdd/` 回答依据什么验证，`checks/` 回答执行什么验证，`evidence/` 回答验证结果是什么。三者保持独立。

应用层 Pytest、Vitest、Playwright、类型检查和 Lighthouse 命令注册在 `config.toml` 的白名单 gate 中，不复制进 Harness checks，也不从 spec 执行任意 shell 文本。active spec 用 `gate => AC` 映射声明适用门禁。

无 task ID 的 `verify` 只检查 Harness 完整性；带 task ID 的 `verify` 先检查文档影响契约，再运行 spec 声明的产品 gate，并写入 schema v2 evidence。`required` 文档目标必须存在于 HEAD、在 spec 首次提交后有已提交变更且没有工作区漂移；检查失败时不启动产品 gate。evidence 只保存命令、退出状态、耗时、AC 覆盖、profile、文档契约与目标 blob、source tree/spec/合同/gate 配置指纹和有限失败摘要，不提交重型原始日志。close 只消费并保留对应当前验证输入的 passed task evidence。

验证 profile 提供最低风险门槛：`focused` 允许任务选择局部 gate，`stack` 强制 API lint、API tests 与 Web quality，`release` 强制完整 release gate。profile 不替代 AC 映射。

task 产品 gate 默认在固定到当前 HEAD 的 detached 临时 Git worktree 中运行。隔离层只链接 `config.toml` 明确允许的项目内依赖目录，gate 不得把这些依赖目录当作输出位置；测试产生的缓存、日志、截图和构建产物应留在临时 worktree 并随清理删除。隔离建立或清理失败都写为 failed check，禁止生成可关闭的 passed evidence；无 task ID 的全局 verify 不创建 worktree。

schema v2 task evidence 为每个 gate 保存退出码、耗时、可识别的 Pytest／Vitest／Playwright测试数量及结构化失败类型，并在顶层汇总 checks、总耗时、测试数和失败检查。只保留一条净化后的有限失败摘要；完整 stdout/stderr、trace、截图和原始报告仍属于本地重型产物。
