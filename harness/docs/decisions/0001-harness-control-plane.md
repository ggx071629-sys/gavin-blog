---
id: decision-harness-control-plane
level: L1
summary: 将 Agent 治理内容集中到 harness 目录，并保留根 AGENTS.md 作为唯一 L0
load_when:
  - harness-change
  - architecture-decision
author: Gavin
---

# Decision 0001: Harness control plane

## Status

Accepted.

## Decision

根 `AGENTS.md` 是唯一 L0，只提供加载地图与硬边界。项目知识、规格、工作流、验证、观测和演进全部进入 `harness/`。产品代码保持在 `apps/` 与 `packages/`。

Harness 的 Markdown 负责约束，Python 标准库工具只负责索引、检查、证据、事件和压缩等确定性工作。

## Consequences

- Agent 不递归预读整个知识库。
- 控制面与产品代码边界清晰。
- 自动化工具不替代判断，也不允许 telemetry 改变行为。

