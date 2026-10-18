---
id: archive-20260831-document-drift-remediation
level: L2
summary: 修复当前权威文档漂移并补齐根与边界文档的自动防漂移门禁
load_when:
  - task:20260831-document-drift-remediation
author: Codex
task_id: 20260831-document-drift-remediation
status: compressed
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

# 20260831-document-drift-remediation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

以当前代码、配置、CLI 和仓库状态为唯一依据，修复所有已确认的当前文档漂移，纠正冻结规格中与已交付 checkpoint 合同冲突的单句验收条件，并让根 README 与三个应用边界 README 的元数据、根 README 的风险变更和文档链接继续受到可执行门禁保护。

## Acceptance criteria

- AC-1: 根 `AGENTS.md` 明确区分 Harness、根 npm 与 API uv/Alembic 命令的工作目录，区分索引文档与 L0 直接映射的项目文档，并继续满足唯一 L0 与 60–80 行约束。
- AC-2: 根 README、Web README、API README、架构边界与 `.env.example` 对当前内容主路径、REST/SSE 访问边界、两套 E2E 端口、默认关闭但已进入当前代码的助手拓扑、精确管理路由、数据边界和面向操作者的配置边界陈述一致；任何测试内部配置均明确排除，不再宣称示例覆盖全部 Settings 字段。
- AC-3: 发布准备文档给出已有 profile/provider、目标 runner、签名/验证及本地备份恢复 CLI 的实际参数合同，明确 runner 只登记已复核观测，并描述 case observation、summary 与签名 key 的输入约束，但不猜测真实路径、秘密值或尚未选择的生产事实。
- AC-4: 产品基线中的助手长期边界引用解析为明确的 durable decision 链接；早期 durable decision 保留当时状态并明确链接后续已交付决策；冻结生产资格 AC-7 经可审计 resume/freeze 只禁止历史问答、证据正文、provider payload 与 query vector 进入 State/checkpoint，同时保留 current question 作为必要恢复状态，不再把历史状态或错误合同冒充当前事实。
- AC-5: 根 README 进入 change enforcement 与至少一个风险路由；根 README、Web README、API README 和 Contracts README 的 front matter 由 metadata check 验证，并有回归测试证明缺失元数据或根 README 漂移会失败。
- AC-6: 全量复核未发现其他未修复的当前态文档矛盾；历史快照保持原样，生成索引、Harness checks、OpenAPI/lock 合同和适用 release gate 全部通过；本任务拥有的路径最终无未提交漂移，同期出现的无关用户改动保持原样并单独报告。

## Result

Verified and closed by the harness close command.

## Evidence

[20260831-document-drift-remediation.json](../../verification/evidence/20260831-document-drift-remediation.json)

Closed at 2026-08-31T13:30:05.674997+00:00.
