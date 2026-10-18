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

无 task ID 的 `verify` 只检查 Harness 完整性；带 task ID 的 `verify` 先检查文档影响契约，再按影响计划执行 spec 对应的精确测试引用或适用检查，并写入 schema v2 evidence；普通 focused/stack 不因此执行整个注册包门禁，全量 release 只用于明确发布。`required` 文档目标必须存在于 HEAD、在 spec 首次提交后有已提交变更且没有工作区漂移；检查失败时不启动产品 gate。evidence 只保存命令、退出状态、耗时、AC 覆盖、profile、文档契约与目标 blob、source tree/spec/合同/gate 配置指纹和有限失败摘要，不提交重型原始日志。close 不信任磁盘上自报 passed 的 JSON：它校验本机 HMAC ledger、exact evidence digest、同 HEAD/输入和最新 attempt 后事务归档，不执行产品 gate 或全套 collector；`close-all --dry-run` 只验证现有凭据，不改写关闭资产；单任务 `close` 没有 `--dry-run` 参数。详见 [认证续跑决策](../docs/decisions/20260905-verification-resume.md)。

全局 `metadata` check 除各生成索引作用域外，还验证 `config.toml` 中显式列出的四个项目入口／边界 README；这些文件继续由根 `AGENTS.md` 或公开入口直接路由，不为了纳入校验而复制进 Harness 生成索引。项目文档清单中的路径必须是存在的项目相对 Markdown 文件，且与索引文档共同执行必填 front matter、L1/L2、`load_when` 和全局 ID 唯一性检查。

验证 profile 的 focused/stack 依据影响计划选择测试，release 专用于明确发布；profile 不替代 AC 映射。

task 产品 gate 默认在固定到当前 HEAD 的 detached 临时 Git worktree 中运行。隔离层只链接 `config.toml` 明确允许的项目内依赖目录，gate 不得把这些依赖目录当作输出位置；测试缓存与构建产物留在临时 worktree 并随清理删除；有界诊断日志、trace、截图在清理前导出到工作树外的本机目录。隔离建立或清理失败都写为 failed check，禁止生成可关闭的 passed evidence；无 task ID 的全局 verify 不创建 worktree。

产品 gate 由监督启动：子进程进入新的进程组或会话，标准输出与错误合并后写入有界本地日志，同时保留失败摘要、测试计数与输出字节数；成功终端只显示紧凑结果。超时使用 `taskkill /T`（Windows）或进程组信号（POSIX）拆除整棵子孙进程，再返回既有 `failure.kind = timeout`，不得因残留管道阻塞 `communicate()`。evidence 仍只保存有限摘要，不提交原始日志。

注册为 `{api_python}` 的 gate 必须从当前执行根的 `apps/api/.venv` 解析解释器：Windows 使用 `Scripts/python.exe`，POSIX 使用 `bin/python`。隔离 worktree 通过受控依赖链接获得同一环境；缺失时失败关闭，不得退回启动 Harness 的全局 Python。`{python}` 只保留既有通用命令的调用者解释器语义。

schema v2 task evidence 为每个 gate 保存退出码、耗时、可识别的 Pytest／Vitest／Playwright 测试数量及结构化失败类型，并在顶层汇总 checks、总耗时、测试数和失败检查。`criteria_results` 按 active spec 的 AC 顺序，把声明覆盖该 AC 的 gate 聚合为 `passed`、`failed` 或 `not-run`；它只证明声明映射的执行结果，不证明自然语言 AC 与测试语义必然一致。close 会从 checks 重新计算并拒绝缺失、伪造、顺序或状态漂移。

非零 gate 的 `details` 第一行是净化、最长 300 字符的 `diagnostic` 锚点，随后最多保留 11 行去重尾部；结构化 failure summary 使用同一锚点。锚点优先识别 Playwright 用例、Assertion/Error/FAILED、TypeScript 和包管理器错误，完整 stdout/stderr、trace、截图和原始报告仍属于本地重型产物。有限输出提高诊断能力但不能把启发式命中当成根因证明。

## 常用入口与审查边界

以下命令均从 `harness/` 执行，以 [CLI 实现](../tools/harness.py)、[验证执行器](../tools/verification_resume.py) 和 [验证工作流](../workflows/verify.md) 为准。

| 命令 | 用途 |
| --- | --- |
| `python -m tools.harness index` | 重建配置声明的索引 |
| `python -m tools.harness verify` | 检查工作区 Harness 结构、链接、元数据、归属及完整性，不执行产品测试 |
| `python -m tools.harness plan <task> --json` | 只读解释影响计划与执行选择 |
| `python -m tools.harness status <task> --json` | 只读检查派生状态与证据适用性 |
| `python -m tools.harness verify <task> --close` | 在提交快照上验证并同进程关闭普通有测试任务 |
| `python -m tools.harness diagnose <task> --case <case>` | 执行计划中的诊断子集，不能产生关闭凭据 |

结构检查不会判断文档叙述是否符合产品行为。变更时还需人工核对实现、当前边界说明和来源时间；路径迁移更新当前文档与归属，不改写 archive、evidence、completion event 中描述历史提交的路径或摘要。

## Module verification contract

模块验证合同以产品基线中的稳定模块 ID 为入口，为每个验证 case 建立 `module → scenario → observable expectations → exact test refs → leaf gates → task evidence` 链。scenario 描述要触发的用户或系统情境；observable expectations 必须同时容纳应当出现的结果与明确禁止出现的 `forbidden` 结果；exact test refs 指向可被对应 leaf gate 收集的精确 Pytest node ID、Vitest 测试或 Playwright project/spec/test；leaf gate 必须是实际执行测试或检查的注册 gate，不能只用带 `subsumption_contract` 的包门禁替代多条 case 的叶子归属。默认关闭的现行模块仍需覆盖关闭态及显式启用后的合同，不得按退役模块跳过。

Active spec 在 `## Verification cases` 中把每条 AC 映射到一个或多个稳定 case ID。Specify 阶段只检查 AC／模块 ID、case ID 语法、唯一性和完整覆盖，允许引用将由本任务新增的 planned case ID；task verify 才以当前提交中的模块验证合同解析全部 case ID，并核对 exact test refs、leaf gates 与 spec 的 `gate => AC` 覆盖。到 task verify 时仍未进入当前合同、引用不存在测试定义、或没有被已选 leaf gate 收集的 case 一律失败，planned 不能成为关闭时的悬空豁免。

模块引用校验直接调用 Pytest、Vitest 与 Playwright 的真实 list/collect 协议（仅限所选引用；全局结构检查不收集），并把 suite 路径绑定到 `config.toml` Gate command 及 npm script 入口；未被收集、重复、永久 skip/todo/fixme、错误 owner 或入口漂移均失败。收集清单证明测试在对应执行入口中可见，但仍不证明 scenario、required／forbidden expectations 与测试断言语义等价，单靠 collect 也不证明本次已执行每个引用；当前执行身份合同还会核对所选与实际执行的完整测试身份集合，缺失、额外或重复执行不能用总数量相等掩盖。Reviewer 在每次新增或修改 case 时必须人工逐条检查 `covers` 对应的断言与正／负预期，不能把测试名、引用存在或总测试数当作语义证明。

## Change coverage closure

`change-check` 不只要求比较区间内出现 task archive 与 schema v2 passed evidence，还要求至少一份有效 evidence 的 source commit 已包含最后一次风险修改。evidence source 到 change head 之间不得再出现 `.github/`、`apps/`、`packages/`、`scripts/`、`harness/` 或配置中关键根文件的修改；否则旧 evidence 不能覆盖后续变化，必须在最新树上重新验证。

验证后只允许该 task 的确定性生命周期产物：active spec 删除、compressed archive、task evidence、`spec.completed` event，以及由配置声明的生成索引。例外精确到 task 文件，不能用整个 archive、evidence 或 event 目录规避风险闭包。`quality:release` 只有设置可信 `HARNESS_BASE_REF` 时执行该检查；未设置时仍明确属于 local-only coverage skip，不能作为远端变更覆盖证明。

## Impact-derived selection

普通任务不再按顶层目录推导固定全量 gate。先在 `impact/ownership.json` 登记细粒度单元的源码、case 和消费者，再在 `impact/<task_id>.json` 记录每项变更以及依赖是否受到影响的理由。选中 case 必须与 spec 一致；不允许无理由追加包门禁，缺失归属、case 或消费者判断时报告具体缺口。只有明确发布 profile 执行 release。

全仓 module-coverage 只验证廉价结构，不运行 collector。普通任务的真实收集只发生在所选 runner 中。Pytest 使用精确 node ID；Vitest 和 Playwright 分文件及精确名称/config/project 选择，防止文件与名称交叉组合扩大范围。没有选择 Web 场景的 Harness 任务不调用 Node、Web build 或跨项目 collector。

复用默认关闭，`--fresh` 仍只运行受影响范围。默认不探测安装分发，普通有测试任务使用 `verify <task> --close` 同进程收尾。只有显式启用且 Harness pytest 安装输入合同完整时才按有界分发文件核对；未登记安装依赖闭包时禁止跨进程复用/close。可选复用保留 HMAC、本机账本、失败历史、输入漂移与清理检查。同进程关闭复用本次 runner 的不可变解析结果，并重新核对 HEAD、源码/计划和运行输入；单次结构校验共享同文件路径解析，下一次调用重新校验。

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

全局 `history-integrity` check 以 compressed archive 为确定性关闭集合，验证同 task 的 passed 主 evidence、lifecycle `spec.completed` event、archive 标识与 evidence 链接，并用一次 Git 查询确认原 active spec 路径仍在当前 HEAD 历史。自 `20260901-*` task 起，archive front matter 与 schema v2 completion event 必须同时保存关闭时 exact evidence SHA-256；文件字段删除、字节篡改、digest 漂移或降级成 legacy event 都会失败。更早的 schema v1 completion event 作为明确 legacy 边界只保留身份／状态检查，不追溯补造 digest。该 check 只读且不重写、补造、迁移或删除历史资产。

`plan <task>` 只读输出 gate 执行/复用与失效原因。`verify <task>` 先执行全局前检，成功后执行当前选择范围；只有显式启用复用且输入合同满足时才使用最后有效 attempt；`--fresh` 禁止复用，release 保持 fresh。`status <task>` 报告未执行、失败、失效与可复用状态。默认不复用；启用时要求同 task、同 HEAD、同规范计划及已登记的受控依赖/环境。最终测试后可同进程关闭。
