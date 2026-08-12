---
id: spec-20260812-verification-reporting-operations
level: L1
summary: 结构化采集验证结果并提供只读 task status 与批量关闭预检
load_when:
  - task:20260812-verification-reporting-operations
author: Codex
task_id: 20260812-verification-reporting-operations
status: active
verification_profile: focused
state_history:
---

# Context

隔离 task verify 已能生成可信 evidence，但成功结果只记录状态与耗时，失败主要依赖有限日志尾部；测试数量不能稳定汇总。操作者也缺少只读命令查看 active／verified／frozen／compressed 状态，`close-all` 没有与真实关闭共享预检逻辑的 dry-run，容易在准备不足时才发现 evidence 或目标冲突。

# Goal

为 gate 和 task evidence 增加紧凑、结构化的测试数量、总耗时和失败摘要，并提供不改变仓库的 `status` 与 `close-all --dry-run`，让关闭前状态和阻断可机器读取、可人工复核。

# Non-goals

- 不修改博客应用、公开信息、文章内容、API 或数据库。
- 不修改、恢复、验证或关闭两个 frozen spec。
- 不提交完整 stdout/stderr、Playwright trace、截图、Lighthouse 原始报告或其他重型产物。
- 不保证从任意第三方测试框架输出中推断数量；只支持项目注册的 Pytest、Vitest、Playwright 和组合门禁格式。
- 不接入远端 CI、通知或仪表盘。

# Acceptance criteria

- AC-1: gate 结果记录 exit code、耗时与可用的 passed／failed／skipped test counts；Pytest、Vitest、Playwright 及组合 release 输出不会把 test files、重复标题或非汇总行误计为测试。
- AC-2: 失败 gate 记录稳定 failure kind 与单条有限摘要，超时、可执行文件缺失、非零退出和隔离失败可区分；evidence 不保存完整日志或临时绝对路径。
- AC-3: task evidence 顶层汇总 checks 总数/通过/失败、总耗时、测试数量与失败检查列表；汇总可由 checks 重算且 close 校验一致性，手工篡改或漂移使 evidence 无效。
- AC-4: `status` 无参数时按 task ID 列出当前 active/verified/frozen，指定 task 时还能报告 compressed 或 missing；`--json` 输出稳定机器对象，且 frozen 状态不触发 task verify/evidence 校验。
- AC-5: `close-all --dry-run` 与真实关闭共享 active 排序、frozen skip、evidence、目标 archive/event 冲突和 Harness 前置检查；只读预检成功或失败均不写 archive、event、evidence、索引或 spec。
- AC-6: status 与 dry-run 使用明确退出码：可执行且状态可读返回 0，指定 missing task 或任何 active 关闭阻断返回 1；没有 active spec 时 dry-run 返回 0。
- AC-7: 无 task ID 全局 verify、task verify、单任务 close、真实 close-all、freeze/resume、隔离清理与历史 compressed evidence 保持兼容。
- AC-8: verification policy、verify workflow 与生命周期说明结构化 evidence、status 和 dry-run 的用途与边界。

# Risks

- ANSI 颜色和不同测试运行器版本会改变输出；解析器必须先净化 ANSI，并只匹配明确汇总行。
- release 输出包含多种嵌套测试框架；聚合必须避免 Vitest 的 Test Files 与 Tests 双计数。
- status 推导 verified 会读取 evidence 和 Git 状态，但不得写 evidence 或运行 gate。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
- harness-integrity => AC-3, AC-4, AC-5, AC-7, AC-8
