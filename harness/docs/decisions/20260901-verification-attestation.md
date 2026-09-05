---
id: decision-verification-attestation
level: L1
summary: 原始 attestation 决策；fresh close 条款由认证续跑决策替代
load_when:
  - verification
  - task-close
  - harness-change
author: Codex
---

# Verification attestation

更新：以下 fresh close 条款和“必要成本”论断已由 [认证续跑决策](20260905-verification-resume.md) 替代；本文件保留原决策依据，exact digest 与本地信任边界仍有效。

## Decision

任务 evidence 不是自证凭据。`close` 必须重新执行当前 HEAD 的 task verify，覆盖已有 evidence，并在校验产品 Gate 的规范命令、结构化零退出结果、隔离清理和完整字段后才关闭。关闭时对 exact evidence bytes 计算 SHA-256，同时写入 compressed archive 与 schema v2 `spec.completed` event；`history-integrity` 重算并比较三者。

模块 test ref 的存在性由真实 Pytest、Vitest、Playwright collector 决定，collector suite 绑定注册 Gate command 与 npm script。源码中的测试名字符串、未收集嵌套函数、永久禁用用例或入口漂移不能满足合同。

## Trust boundary

本地仓库内代码和合同可以防止误改、普通 evidence 编辑和陈旧关闭，但不是对拥有同一提交写权限者的外部不可变签名。远端保护仍依赖 code review、required checks 与受保护分支。自然语言 expectation 和测试断言的语义一致性不可由名字自动证明，case reviewer 必须逐条审查 `covers`。

## Compatibility and cost

`20260901-*` 及之后的关闭必须使用 digest-bound schema；此前 schema v1 completion event 保持只读 legacy 兼容，不回填摘要。代价是 close 再运行一次完整 task verification；这是拒绝“编辑 JSON 后关闭”的必要成本，collector 结果只在同一进程内按测试文件状态缓存。
