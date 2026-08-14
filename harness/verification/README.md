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

## Change coverage closure

`change-check` 不只要求比较区间内出现 task archive 与 schema v2 passed evidence，还要求至少一份有效 evidence 的 source commit 已包含最后一次风险修改。evidence source 到 change head 之间不得再出现 `.github/`、`apps/`、`packages/`、`scripts/`、`harness/` 或配置中关键根文件的修改；否则旧 evidence 不能覆盖后续变化，必须在最新树上重新验证。

验证后只允许该 task 的确定性生命周期产物：active spec 删除、compressed archive、task evidence、`spec.completed` event，以及由配置声明的生成索引。例外精确到 task 文件，不能用整个 archive、evidence 或 event 目录规避风险闭包。`quality:release` 只有设置可信 `HARNESS_BASE_REF` 时执行该检查；未设置时仍明确属于 local-only coverage skip，不能作为远端变更覆盖证明。

## Historical assurance

从 `harness/` 运行 `python -m tools.harness evidence-inventory [--json]` 可只读盘点主 evidence。该命令不重新执行历史 gate，只按已保存结构保守分类：

- `v2-product-verified`：schema v2、passed、包含全部 passed checks、至少一个 product gate，并记录已清理的隔离 Git worktree。
- `legacy-product-reported`：schema v1，主记录包含非结构产品检查，或存在 passed 的 `.application.json` 辅助报告；这是历史人工报告，不具有 v2 指纹、当前 HEAD 和隔离闭包保证。
- `legacy-structure-only`：schema v1 只保存 indexes、L0、links、metadata、structure 等 Harness 结构检查，不能证明产品行为通过。
- `invalid`：无法解析、未知 schema、非 passed，或声称 v2 但缺少隔离/product/check 完整结构。

`.benchmark.json` 和 `.application.json` 作为辅助资产列入 inventory，但不计作独立 task。任何 assurance 标签都只描述文件中可证事实，不能替代重新验证，也不能自动触发 Evolution。
