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

应用层 Pytest、Vitest、Playwright、类型检查和 Lighthouse 命令未来注册到 `config.toml`，不复制进 Harness checks。

