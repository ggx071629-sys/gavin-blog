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

产品 gate 由监督启动：子进程进入新的进程组或会话，标准输出与错误合并后边产生边写到 verify 终端，同时保留给失败摘要和测试计数。超时使用 `taskkill /T`（Windows）或进程组信号（POSIX）拆除整棵子孙进程，再返回既有 `failure.kind = timeout`，不得因残留管道阻塞 `communicate()`。evidence 仍只保存有限摘要，不提交原始日志。

注册为 `{api_python}` 的 gate 必须从当前执行根的 `apps/api/.venv` 解析解释器：Windows 使用 `Scripts/python.exe`，POSIX 使用 `bin/python`。隔离 worktree 通过受控依赖链接获得同一环境；缺失时失败关闭，不得退回启动 Harness 的全局 Python。`{python}` 只保留既有通用命令的调用者解释器语义。

schema v2 task evidence 为每个 gate 保存退出码、耗时、可识别的 Pytest／Vitest／Playwright 测试数量及结构化失败类型，并在顶层汇总 checks、总耗时、测试数和失败检查。`criteria_results` 按 active spec 的 AC 顺序，把声明覆盖该 AC 的 gate 聚合为 `passed`、`failed` 或 `not-run`；它只证明声明映射的执行结果，不证明自然语言 AC 与测试语义必然一致。close 会从 checks 重新计算并拒绝缺失、伪造、顺序或状态漂移。

非零 gate 的 `details` 第一行是净化、最长 300 字符的 `diagnostic` 锚点，随后最多保留 11 行去重尾部；结构化 failure summary 使用同一锚点。锚点优先识别 Playwright 用例、Assertion/Error/FAILED、TypeScript 和包管理器错误，完整 stdout/stderr、trace、截图和原始报告仍属于本地重型产物。有限输出提高诊断能力但不能把启发式命中当成根因证明。

## Change coverage closure

`change-check` 不只要求比较区间内出现 task archive 与 schema v2 passed evidence，还要求至少一份有效 evidence 的 source commit 已包含最后一次风险修改。evidence source 到 change head 之间不得再出现 `.github/`、`apps/`、`packages/`、`scripts/`、`harness/` 或配置中关键根文件的修改；否则旧 evidence 不能覆盖后续变化，必须在最新树上重新验证。

验证后只允许该 task 的确定性生命周期产物：active spec 删除、compressed archive、task evidence、`spec.completed` event，以及由配置声明的生成索引。例外精确到 task 文件，不能用整个 archive、evidence 或 event 目录规避风险闭包。`quality:release` 只有设置可信 `HARNESS_BASE_REF` 时执行该检查；未设置时仍明确属于 local-only coverage skip，不能作为远端变更覆盖证明。

## Risk-derived gate floor

task verify 以 active spec 首次提交为基线，读取其后到当前 HEAD 的已提交路径，并按 `config.toml` 中有序的 `verification.risk_routes` 聚合最低 gate。API、Web 与跨栈契约保持原路由；Harness 文档走 `harness-docs`（`harness-integrity`），Harness 工具/检查/测试/SDD 走 `harness-control`（`harness-tests` 与 `harness-integrity`），CI、脚本、`config.toml`、锁文件与 `AGENTS.md` 走 `release-control`（`release`）。重叠 route 的 gate 稳定去重。spec 的 verification plan 必须直接映射推导 gate，或映射一个具有有效直接 subsumption proof 的上层 gate；未证明或传递式包含不能满足下限，也不能通过选择较低 profile 绕过。

超过一条 AC 时，每条 AC 必须至少映射一个叶子 gate。带 `subsumption_contract` 的包门禁不能成为全部 AC 的唯一映射。额外选择不在风险下限内的包门禁时，spec 必须声明非空单行 `verification_escalation`。`python -m tools.harness spec-lint [task_id]` 复用该合同检查但不启动产品 gate。task verify 失败且本地 JSONL 已有同一 task 至少两个 failed run 时，打印可复制的 `emit-event verification.repeated_failure` 命令；提示不写 Evolution 文件，也不改变退出码。

推导范围、匹配 route、触发路径和最低 gate 进入 evidence 的 gate 配置指纹。风险路由配置、实现提交或 verification plan 发生漂移时，旧 evidence 失效。纯文档、生成索引与生命周期 close 产物不命中产品 route；未提交的验证源码仍由 clean-source 前置条件拒绝。

## Gate subsumption

`release` 可通过 `scripts/release-stage-contract.json` 直接满足其实际执行的已注册子 gate。合同逐项绑定 gate、release stage、cwd 与 argv，并必须与 `config.toml` 完全一致；全局 `gate-subsumption` check 在普通 verify 和 release 尾部都校验该关系。runner 从同一合同执行每个子 gate 恰好一次，完成 OpenAPI consistency 等非合同阶段后，才输出包含合同 SHA-256 和有序完成阶段的唯一终态 proof。

task gate 只有退出 0 且 proof 唯一、可解析、hash 当前、阶段完整时才通过；最小 verified subsumption 保存到 product check result，合同内容、profile/risk 满足关系进入 gate 指纹，close 会重新计算并拒绝漂移。subsumption 只消除 plan 同时选择子 gate 与完整 release 时的重复调用，不减少 `quality:release` 内部实际阶段，也不允许多跳推导。

## Supply-chain baseline

每次全局与 task verify 都执行独立 `supply-chain` check。它只读遍历全部 GitHub workflow，要求外部 action 固定完整 40 字符提交 SHA、显式权限精确为顶层 `contents: read`、禁用 `pull_request_target`，并拒绝 CI 中的 `npm install`、`pip install` 与未带 `--locked` 的 `uv sync`。本地 action 由同一提交内容寻址；container action 必须固定 `sha256`。

同一 check 还要求 Node lockfile v3 的 registry 记录具有 SHA-512 integrity，并验证 `apps/api/uv.lock` 为 uv version 1 revision 3、registry 唯一为官方 PyPI，且每个 registry 包的全部 distribution artifact 带 SHA-256。它不访问网络、不修改 lock，也不查询实时漏洞库；`uv sync --locked` 在 CI 中负责拒绝 pyproject 与 lock 漂移。仓库内 check 可以防误改并提高审查可见性，但不是不可变信任根：没有 GitHub required review/ruleset 时，拥有写权限的人仍能在同一提交修改 workflow 与 check。

## Historical assurance

从 `harness/` 运行 `python -m tools.harness evidence-inventory [--json]` 可只读盘点主 evidence。该命令不重新执行历史 gate，只按已保存结构保守分类：

- `v2-product-verified`：schema v2、passed、包含全部 passed checks、至少一个 product gate，并记录已清理的隔离 Git worktree。
- `v2-transitional-product-reported`：schema v2 过渡期记录，全部 checks passed 且包含 product gate，但产生于隔离 execution 字段落地前；只保留当时报告，不能宣称当前隔离闭包。
- `legacy-product-reported`：schema v1，主记录包含非结构产品检查，或存在 passed 的 `.application.json` 辅助报告；这是历史人工报告，不具有 v2 指纹、当前 HEAD 和隔离闭包保证。
- `legacy-structure-only`：schema v1 只保存 indexes、L0、links、metadata、structure、gate-subsumption、history-integrity、supply-chain 等 Harness 结构或控制面检查，不能证明产品行为通过。
- `invalid`：无法解析、未知 schema、非 passed、有畸形 execution，或缺少可信 product/check 结构。

`.benchmark.json` 和 `.application.json` 作为辅助资产列入 inventory，但不计作独立 task。任何 assurance 标签都只描述文件中可证事实，不能替代重新验证，也不能自动触发 Evolution。

全局 `history-integrity` check 以 compressed archive 为确定性关闭集合，验证同 task 的 passed 主 evidence、lifecycle `spec.completed` event、archive 标识与 evidence 链接，并用一次 Git 查询确认原 active spec 路径仍在当前 HEAD 历史。active/closed 重叠、三件套缺失或错配、历史缺口都会失败关闭；没有 completion event 的既有独立 evidence 仍只由 inventory 报告。该 check 只读且不重写、补造、迁移或删除历史资产。
