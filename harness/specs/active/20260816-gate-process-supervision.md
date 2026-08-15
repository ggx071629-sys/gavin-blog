---
id: spec-20260816-gate-process-supervision
level: L1
summary: 让 task verify 的产品 gate 超时杀整棵进程树，并把子进程输出实时写到终端
load_when:
  - task:20260816-gate-process-supervision
author: Gavin
task_id: 20260816-gate-process-supervision
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
documentation_reason: 门禁监督与超时杀树改变了 verify 的可观察执行合同，需要写进验证政策。
state_history:
---

# Context

当前主干的 task verify 用 `subprocess.run(capture_output=True, timeout=…)` 跑产品 gate。gate 结束前终端没有任何子进程输出，闭环看起来像空转。Windows 上超时往往只杀最外层 `npm.CMD`，Playwright 与 `nuxi` 继续占管道，父进程堵在 `communicate()`，evidence 写不出来。`agent/20260815-gate-process-supervision` 已在旁支关闭同一合同，但未进入本 HEAD。

# Goal

产品 gate 在独立进程组中运行；超时拆除整棵子孙进程并返回既有 timeout 失败形状；子进程输出边产生边写到 verify 终端，同时仍被采集进 evidence 摘要。

# Non-goals

- 不改 isolation worktree、gate 白名单、AC 映射或 evidence schema。
- 不改 Playwright、Nuxt 或 `NUXT_TYPECHECK` 产品配置。
- 不把完整原始日志提交进 evidence。
- 不引入 Job Object 之外的部署或 CI 拓扑。
- 不恢复或修改两条 GitHub frozen spec。

# Acceptance criteria

- AC-1: 监督启动的 gate 子进程在超时后整棵进程树不再存活；runner 返回 `failure.kind = timeout`，不再因残留管道而挂起。
- AC-2: gate 的标准输出在运行中写到 verify 进程的 stdout，并仍进入现有失败摘要与测试计数解析。
- AC-3: 非零退出、超时、执行错误的结构化 result 形状保持不变；Harness 测试覆盖监督启动与超时杀树。

# Risks

- 只杀父 PID 会留下 nuxi/Playwright；必须按进程树杀。
- 实时打印可能混入隔离路径；失败摘要仍要做既有 redaction。
- 测试若继续 mock `subprocess.run` 会绕过监督器；产品路径必须走单一监督入口。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
