---
id: archive-20260910-studio-project-list
level: L2
summary: 项目列表对齐开放行并呈现真实技术信息与查询操作
load_when:
  - task:20260910-studio-project-list
task_id: 20260910-studio-project-list
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
evidence_sha256: 0e75f510d4d4019adea5bff759fcb2ca02b611f0e93fe56a3eb8e75dbaa6c3aa
state_history:
---

# 20260910-studio-project-list

Deterministic compressed record. The original active spec remains in Git history.

## Goal

项目列表对齐开放行并呈现真实技术信息与查询操作

## Acceptance criteria

- AC-1: 项目标题搜索与状态筛选使用完整服务端集合，真实摘要、仓库和站点链接可达，编辑及删除沿用确认。
- AC-2: 双主题窄屏无横溢且 axe 通过，读取失败可重试，不新增项目历史或虚构统计。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-project-list.json](../../verification/evidence/20260910-studio-project-list.json)

SHA-256: `0e75f510d4d4019adea5bff759fcb2ca02b611f0e93fe56a3eb8e75dbaa6c3aa`

Closed at 2026-09-10T08:35:29.691518+00:00.
