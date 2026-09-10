---
id: spec-20260910-studio-overview
level: L1
summary: 助手概览对齐选定设计并保留真实状态
load_when:
  - task:20260910-studio-overview
task_id: 20260910-studio-overview
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录概览视觉与真实未知和过期数据边界。
state_history:
---

# Context
U2-01 接续已完成阶段一。现有助手页面已接入真实管理 API；原型仅用于视觉，不能复制示例费用或开放状态。主要差异为页头、开放行、警告区与预算/同步行字号及留白。

# Goal
对齐选定概览设计的开放布局、图标、文字层级与双主题响应式；费用与同步仍来自既有 API，未知预算不绘制确定值。

# Non-goals
不调用真实模型、不改变准入/预算/同步/Worker 业务，不改公开助手和原有用户改动。试问布局和弹窗留后续任务。

# Acceptance criteria
- AC-1: 概览对齐选定页头、页签、开放状态、警告和信息行；320–1487px 双主题可读、无横溢及 axe 违规，桌面保持开放分隔布局。
- AC-2: 金额及同步数量绑定管理 API；未知费用不显示确定进度，失败刷新明确标注过期且不显示开放成功；刷新不发起写入或模型调用。

# Risks
长状态说明不能套用原型固定短文而截断；未知费用与过期快照不得伪装为正常。选定绿点只辅助文字表达成功，不作为唯一状态。

# Verification plan
对真实隔离 API 的费用和同步值进行页面比对；注入未知计量与刷新失败检查 UI 语义。既有状态单元测试保持约束。

## Verification cases
- AC-1 => M10-STUDIO-OVERVIEW-01
- AC-2 => M10-STUDIO-OVERVIEW-01

## Gates
- e2e => AC-1, AC-2
- web-quality => AC-1, AC-2
- harness-integrity => AC-1, AC-2
