---
id: spec-20260831-document-drift-remediation
level: L1
summary: 修复当前权威文档漂移并补齐根与边界文档的自动防漂移门禁
load_when:
  - task:20260831-document-drift-remediation
author: Codex
task_id: 20260831-document-drift-remediation
status: active
verification_profile: release
verification_escalation: 本任务将修改唯一 L0、Harness 风险路由与 metadata check；即使初始 spec 提交尚未触发路径下限，也必须用完整 release 证明控制面与产品门禁仍可组合执行。
documentation_impact: required
documentation_targets:
  - README.md
  - apps/web/README.md
  - apps/api/README.md
  - harness/docs/product/brief.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/20260829-public-qa-runtime-integrity-remediation.md
  - harness/docs/operations/release-readiness.md
  - harness/verification/README.md
documentation_reason: 本任务修复公开入口、API 配置边界、产品责任引用和生产资格操作手册的当前事实，并建立持续防漂移门禁。
state_history:
---

# Context

全局 Harness 结构检查、链接检查和现有单测均通过，但语义复核发现当前权威文档仍存在未被门禁捕获的漂移：根 `AGENTS.md` 把工作目录与索引路由规则写得过宽；根 `README.md` 未进入风险路由或 change enforcement；根与应用边界 README 的 front matter 不受 metadata check；Web README 漏写助手 E2E 的独立端口；API `.env.example` 与 Settings 字段不一致；API README 合并了两个不同的管理路由，并把已经交付但默认关闭的问答代码写成未交付；生产资格文档遗漏已实现 runner 的精确命令、操作者输入合同及仓库必须保存的非秘密输入；根文档把助手 runtime SQLite 与内容事实库混称；产品基线和早期决策缺少可解析的后续决策链。规格提交后的独立复核还确认冻结的生产资格 AC-7 与当前实现、回归测试及架构边界矛盾；本任务必须按 freeze/resume 生命周期做一次可审计的窄修正，但不启动任何真实生产资格动作。

# Goal

以当前代码、配置、CLI 和仓库状态为唯一依据，修复所有已确认的当前文档漂移，纠正冻结规格中与已交付 checkpoint 合同冲突的单句验收条件，并让根 README 与三个应用边界 README 的元数据、根 README 的风险变更和文档链接继续受到可执行门禁保护。

# Non-goals

- 不改变博客产品行为、公开 API、数据模型、生产资格状态或默认关闭的助手开关。
- 不恢复、改写或重新解释历史 archive、evidence、review 和已外置的冷存档。
- 不选择尚未由管理员确定的部署平台、供应商、域名、路径、秘密或阈值。
- 不把测试专用内部开关包装成面向操作者的生产配置。
- 不执行生产资格 case、调用真实供应商、创建部署资产或改变冻结任务仍在等待管理员生产选择的状态。

# Acceptance criteria

- AC-1: 根 `AGENTS.md` 明确区分 Harness、根 npm 与 API uv/Alembic 命令的工作目录，区分索引文档与 L0 直接映射的项目文档，并继续满足唯一 L0 与 60–80 行约束。
- AC-2: 根 README、Web README、API README、架构边界与 `.env.example` 对当前内容主路径、REST/SSE 访问边界、两套 E2E 端口、默认关闭但已进入当前代码的助手拓扑、精确管理路由、数据边界和面向操作者的配置边界陈述一致；任何测试内部配置均明确排除，不再宣称示例覆盖全部 Settings 字段。
- AC-3: 发布准备文档给出已有 profile/provider、目标 runner、签名/验证及本地备份恢复 CLI 的实际参数合同，明确 runner 只登记已复核观测，并描述 case observation、summary 与签名 key 的输入约束，但不猜测真实路径、秘密值或尚未选择的生产事实。
- AC-4: 产品基线中的助手长期边界引用解析为明确的 durable decision 链接；早期 durable decision 保留当时状态并明确链接后续已交付决策；冻结生产资格 AC-7 经可审计 resume/freeze 只禁止历史问答、证据正文、provider payload 与 query vector 进入 State/checkpoint，同时保留 current question 作为必要恢复状态，不再把历史状态或错误合同冒充当前事实。
- AC-5: 根 README 进入 change enforcement 与至少一个风险路由；根 README、Web README、API README 和 Contracts README 的 front matter 由 metadata check 验证，并有回归测试证明缺失元数据或根 README 漂移会失败。
- AC-6: 全量复核未发现其他未修复的当前态文档矛盾；历史快照保持原样，生成索引、Harness checks、OpenAPI/lock 合同和适用 release gate 全部通过；本任务拥有的路径最终无未提交漂移，同期出现的无关用户改动保持原样并单独报告。

# Risks

- 过度扩张 metadata 扫描范围可能把历史或非路由 Markdown 错当当前文档；新增范围必须只列四个明确权威 README。
- 把根 README 路由到过重或无关的产品 gate 会增加纯文档成本；最低门禁只需保护 Harness 一致性，`AGENTS.md` 与控制面代码仍按既有 release 路由处理。
- 资格 runbook 中的占位路径若写成真实选择会制造新的生产漂移；命令必须使用语义占位符并明确由已批准 profile 提供。
- `.env.example` 中加入本地嵌入式 Qdrant 路径时必须保留 production 禁止该模式的边界，测试 bootstrap 仍保持内部专用。
- 修正冻结规格前必须先显式 resume，修正后必须以仍等待管理员生产选择的原因重新 freeze；手工改状态或顺带改变其他资格边界都会破坏可审计基线。
- 同期无关依赖或 skill 改动会触发 clean-source；验证时只能精确、临时搁置并在结束后原样恢复，不能混入本任务提交或以“清理”为名删除。

# Verification plan

- api-lint => AC-2
- api-tests => AC-2
- harness-tests => AC-1, AC-5, AC-6
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
