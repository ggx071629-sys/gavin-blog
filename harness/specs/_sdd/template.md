---
id: sdd-template
level: L1
summary: 短生命周期 active spec 的最小模板
load_when:
  - spec-create
author: Gavin
---

# Spec template

新 spec 保存为 `active/YYYYMMDD-short-slug.md`，并包含以下字段与章节：

~~~yaml
---
id: spec-YYYYMMDD-short-slug
level: L1
summary: 一句话目标
load_when:
  - task:YYYYMMDD-short-slug
author: Gavin # optional
task_id: YYYYMMDD-short-slug
status: active
verification_profile: focused # focused | stack | release
planned_modules: # 仅在本任务先定义、后落地新模块时填写；例如 M11
  - M11
documentation_impact: required # required | none
documentation_targets: # required 时至少一个；none 时留空
  - README.md
documentation_reason: 为什么 durable 文档需要或不需要同步
state_history:
---
~~~

正文依次包含以下非空 H1 章节：`# Context`、`# Goal`、`# Non-goals`、`# Acceptance criteria`、`# Risks`、`# Verification plan`。`# Verification plan` 内还必须依次包含非空 H2 章节 `## Verification cases` 与 `## Gates`。

每项验收标准使用唯一标识，格式为 `- AC-1: 可观察结果`。验证计划只引用 `config.toml` 注册的白名单 gate，格式为 `- gate-name => AC-1, AC-2`；每项验收标准至少由一个 gate 覆盖，不能从 Markdown 填写或执行任意 shell 命令。`verification_profile` 选择 `focused`、`stack` 或 `release`，并强制包含该层级在 `config.toml` 注册的最低 gate。带 `subsumption_contract` 的 gate（当前为 `release`）是包门禁：超过一条 AC 时，每条 AC 必须至少映射一个叶子 gate，不能把全部 AC 只挂在同一个包门禁上。若计划额外选择不在风险下限内的包门禁，必须填写非空单行 `verification_escalation`。实现前可用 `python -m tools.harness spec-lint <task_id>` 做同一套合同检查，不启动产品 gate。

`## Verification cases` 每行映射一个 AC，格式为 `- AC-1 => M01-SCENARIO-01`；同一 AC 需要多个 case 时在该行使用逗号分隔。每个 AC 必须且只能出现一次并至少映射一个 case，同一 AC 内不得重复 case ID；同一 case 可以为多条相关 AC 提供共同验证责任。当前模块前缀必须来自产品 authority；本任务要先定义新模块时，必须在 front matter 的 `planned_modules` 显式声明稳定 ID（如 `M11`），不能靠任意未知前缀绕过。Specify 允许该 planned case 尚未进入变更前合同；task verify 时它必须已进入当前产品 authority 与模块验证合同，并具有 exact test refs、observable required／forbidden expectations 和与 `gate => AC` 一致的 leaf gate，否则验证失败。`## Gates` 中保存 `- gate-name => AC-1, AC-2` 映射。

spec-lint 只接受唯一的 `# Verification plan`，其内恰好按顺序出现 `## Verification cases` 与 `## Gates`。Goal 与 Acceptance criteria 缺失或为空时必须先修复 spec，close 不会删除 active 文件或生成不完整归档。

`state_history` 由 Harness 的 freeze/resume 命令维护，新 spec 初始为空。不要手工改写 `status`、冻结元数据或历史记录。

文档目标使用项目根目录相对的 POSIX Markdown 路径。不得指向 `AGENTS.md`、生成索引、active spec、evidence、event 或 proposal。`required` 的每个目标必须在 spec 首次提交之后完成并提交变更；spec 之前已有的修改不能作为本任务证据。`none` 不得包含目标，且必须用单行 `documentation_reason` 说明判断依据。

新 spec 必须先提交并存在于 Git HEAD，之后才能开始实现和运行 task verify。
