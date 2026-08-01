---
id: spec-20260731-harness-bootstrap
level: L1
summary: 建立 Gavin 博客项目的可运行、可验证 Harness 控制面
load_when:
  - task:20260731-harness-bootstrap
author: Gavin
task_id: 20260731-harness-bootstrap
status: verified
---

# Harness bootstrap

## Context

项目工作区为空，需要先建立 Agent 的上下文路由、短生命周期规格、模块化工作流、自动验证、只读观测和事件驱动演进机制。

## Goal

创建位于 `harness/` 的完整控制面，同时保留根 `AGENTS.md` 作为唯一 L0。

## Non-goals

- 不生成 Nuxt 或 FastAPI 业务代码。
- 不绑定 CI、部署平台或对象存储供应商。
- 不初始化或提交 Git 仓库。

## Acceptance criteria

- `AGENTS.md` 为 60–80 行。
- L1/L2 文档通过自动生成的索引路由。
- 五类 Harness checks 可执行。
- 验证可生成紧凑 evidence 清单。
- 未进入 Git 历史的 spec 无法被关闭删除。

## Risks

最大的风险是治理结构过重，因此 spec 按风险触发，且长期记录只保留压缩信息。

## Verification plan

生成全部索引，运行 `python -m tools.harness verify 20260731-harness-bootstrap`，并检查安全关闭护栏。

## Implementation record

- Harness 路由、SDD/VDD 工作流、确定性 checks、紧凑 evidence、只读 telemetry 与人工确认的 Evolution 机制均已实现。
- 2026-08-02 收口验证确认 8 个索引、唯一 L0、链接、metadata 与 required structure 全部通过；spec 等待原文进入首个 Git HEAD 后确定性归档。
