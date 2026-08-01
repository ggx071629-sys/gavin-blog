---
id: spec-20260802-engineering-closeout
level: L1
summary: 将本地 MVP 收敛为可复现、可审计的发布候选基线并启动首次 Evolution 实际闭环
load_when:
  - task:20260802-engineering-closeout
author: Gavin
task_id: 20260802-engineering-closeout
status: active
---

# Engineering closeout

## Context

本地 MVP 的产品能力和质量门禁已经实现，但仓库尚无 Git 基线，多份已验证 spec 仍留在 active，开发日志与本地媒体尚未进入忽略边界，发布准备没有统一入口，Evolution 也只有机制而没有事件、提案、人工确认和应用记录。

## Goal

建立不泄露本地数据的 Git 基线、统一的本地发布候选门禁和诚实的首发准备边界，关闭已验证任务，并以真实事件启动首次人工确认的 Evolution 运行闭环。

## Non-goals

- 不选择或配置具体部署平台、域名、云数据库或对象存储。
- 不声称项目已经 production-ready 或已经上线。
- 不删除现有本地数据库、媒体、日志或用户文件。
- 不新增产品功能或改变 API、数据库和认证行为。

## Acceptance criteria

- Git 忽略规则覆盖环境密钥、日志、SQLite 数据、本地媒体、依赖和重型测试产物，且保留可提交的 `.env.example`。
- 根级 `npm run quality:release` 可重复执行 API lint/测试、契约同步、Web 质量门禁、核心 E2E 与 Harness 验证，并以任一失败阻断。
- README 准确表述“本地 MVP 完成、工程收口与首发准备进行中”，不再暗示已发布。
- 发布准备文档明确本地 RC 门禁、生产 No-Go 阻断项、数据备份与平台无关回滚原则。
- 已验证 active specs 在原文进入 Git 历史后通过 deterministic close 归档；未验证项先补证据再关闭。
- 至少产生一个真实 Evolution event 和 proposal；任何控制面改动只在用户明确确认该 proposal 后应用并重新验证。

## Risks

- 首次 Git 基线可能误纳本地数据，因此必须先修复忽略边界并审查待提交文件。
- 全量质量门禁耗时且依赖 Playwright 浏览器与 API 虚拟环境，缺少依赖时必须明确失败而非跳过。
- 批量关闭 spec 会产生多份事件与提案，必须逐项保留可追踪性且不得自动修改 `AGENTS.md`。
- 部署尚未决策，因此本任务只能准备本地 release candidate，不能替代生产发布验收。

## Verification plan

- 用 `git status --ignored` 审查本地数据、日志和环境文件均未进入待提交集合。
- 执行 `npm run quality:release`，确认所有应用层和 Harness 门禁通过。
- 初始化并提交包含原始 active specs 的基线，再逐项运行 `python -m tools.harness close <task_id>`。
- 检查归档、evidence、event 与 proposal 产物，并在用户确认选定 proposal 后应用、重新生成索引和复验。
