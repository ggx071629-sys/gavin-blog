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

无 task ID 的 `verify` 只检查 Harness 完整性；带 task ID 的 `verify` 还会运行 spec 声明的产品 gate，并写入 schema v2 evidence。evidence 只保存命令、退出状态、耗时、AC 覆盖、profile、source tree/spec/合同/gate 配置指纹和有限失败摘要，不提交重型原始日志。close 只消费并保留对应当前验证输入的 passed task evidence。

验证 profile 提供最低风险门槛：`focused` 允许任务选择局部 gate，`stack` 强制 API lint、API tests 与 Web quality，`release` 强制完整 release gate。profile 不替代 AC 映射。
