---
id: archive-20260909-assistant-discovery
level: L2
summary: 助手入口进入导航并提供可关闭首页提示
load_when:
  - task:20260909-assistant-discovery
task_id: 20260909-assistant-discovery
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 更新入口位置、提示偏好和焦点恢复合同。
evidence_sha256: 1fa790a86c1961623f5b5397b570e3f951be4e83d386a436a11eb16c2a2c6560
state_history:
---

# 20260909-assistant-discovery

Deterministic compressed record. The original active spec remains in Git history.

## Goal

导航持续显示问 Gavin；首页介绍下方显示开始提问提示，关闭后记住偏好。

## Acceptance criteria

- AC-1: 允许路径且开关启用时导航显示唯一问 Gavin 入口，无悬浮入口；不同视口无横溢。
- AC-2: 首页提示正常占位，点击打开同一面板，关闭后刷新不再出现；存储不可用时不影响页面及助手。
- AC-3: 入口不提前请求助手接口；关闭面板恢复触发点焦点，导航及助手保持单一 modal，禁用时入口和提示均隐藏。

## Result

Verified and closed by the harness close command.

## Evidence

[20260909-assistant-discovery.json](../../verification/evidence/20260909-assistant-discovery.json)

SHA-256: `1fa790a86c1961623f5b5397b570e3f951be4e83d386a436a11eb16c2a2c6560`

Closed at 2026-09-08T17:07:17.188364+00:00.
