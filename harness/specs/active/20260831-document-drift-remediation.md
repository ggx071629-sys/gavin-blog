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
  - apps/api/README.md
  - harness/docs/product/brief.md
  - harness/docs/operations/release-readiness.md
documentation_reason: 本任务修复公开入口、API 配置边界、产品责任引用和生产资格操作手册的当前事实，并建立持续防漂移门禁。
state_history:
---

# Context

全局 Harness 结构检查、链接检查和现有单测均通过，但语义复核发现当前权威文档仍存在未被门禁捕获的漂移：根 `AGENTS.md` 把工作目录规则写得过宽；根 `README.md` 未进入风险路由或 change enforcement；根与应用边界 README 的 front matter 不受 metadata check；API `.env.example` 与 Settings 字段不一致；生产资格文档没有给出已经实现的 evidence runner 命令；根架构图没有标明它只描述内容主路径；产品基线还保留无法解析的“本决策”引用。当前冻结的生产资格任务保持不变，本任务只修复现行文档事实与控制面。

# Goal

以当前代码、配置、CLI 和仓库状态为唯一依据，修复所有已确认的当前文档漂移，并让根 README 与三个应用边界 README 的元数据、根 README 的风险变更和文档链接继续受到可执行门禁保护。

# Non-goals

- 不改变博客产品行为、公开 API、数据模型、生产资格状态或默认关闭的助手开关。
- 不恢复、改写或重新解释历史 archive、evidence、review 和已外置的冷存档。
- 不选择尚未由管理员确定的部署平台、供应商、域名、路径、秘密或阈值。
- 不把测试专用内部开关包装成面向操作者的生产配置。

# Acceptance criteria

- AC-1: 根 `AGENTS.md` 明确区分 Harness、根 npm 与 API uv/Alembic 命令的工作目录，并继续满足唯一 L0 与 60–80 行约束。
- AC-2: 根 README、API README 与 `.env.example` 对当前内容主路径、默认关闭的助手拓扑和面向操作者的配置边界陈述一致；任何测试内部配置均明确排除，不再宣称示例覆盖全部 Settings 字段。
- AC-3: 发布准备文档给出已有资格 runner 的初始化、逐 case 记录、组装、签名和验证命令合同，包括 CLI 已要求的参数，但不猜测真实路径、秘密值或尚未选择的生产事实。
- AC-4: 产品基线中的助手长期边界引用解析为明确的 durable decision 链接，不再使用无指向的“本决策”或模糊阶段名称。
- AC-5: 根 README 进入 change enforcement 与至少一个风险路由；根 README、Web README、API README 和 Contracts README 的 front matter 由 metadata check 验证，并有回归测试证明缺失元数据或根 README 漂移会失败。
- AC-6: 全量复核未发现其他未修复的当前态文档矛盾；历史快照保持原样，生成索引、Harness checks、OpenAPI/lock 合同和适用 release gate 全部通过，工作树最终干净。

# Risks

- 过度扩张 metadata 扫描范围可能把历史或非路由 Markdown 错当当前文档；新增范围必须只列四个明确权威 README。
- 把根 README 路由到过重或无关的产品 gate 会增加纯文档成本；最低门禁只需保护 Harness 一致性，`AGENTS.md` 与控制面代码仍按既有 release 路由处理。
- 资格 runbook 中的占位路径若写成真实选择会制造新的生产漂移；命令必须使用语义占位符并明确由已批准 profile 提供。
- `.env.example` 中加入本地嵌入式 Qdrant 路径时必须保留 production 禁止该模式的边界，测试 bootstrap 仍保持内部专用。

# Verification plan

- api-lint => AC-2
- api-tests => AC-2
- harness-tests => AC-1, AC-5, AC-6
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
