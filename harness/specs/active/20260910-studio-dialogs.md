---
id: spec-20260910-studio-dialogs
level: L1
summary: 统一助手预算费用同步维护弹窗及真实确认状态
load_when:
  - task:20260910-studio-dialogs
task_id: 20260910-studio-dialogs
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录助手弹窗、维护直达链接与确认错误反馈。
state_history:
---

# Context
概览和试问已验收；费用与同步原为内联区，维护为独立视图。选定稿使用弹窗，真实预算/版本/同步逻辑必须保留。

# Goal
共用一个焦点与滚动边界呈现预算、费用、同步和高级维护，避免叠加弹窗；仍可直达维护链接，确认取消返回原上下文，失败可见且可重试。

# Non-goals
不改变服务端准入、预算上限/精度、同步资格、版本锁或 Worker。无真实模型或生产开放操作。不复制演示数据。

# Acceptance criteria
- AC-1: 费用、同步、预算、维护使用统一有名称弹窗；320–1440px 双主题无溢出、axe 通过，Escape/关闭/焦点恢复与直接维护链接可用。
- AC-2: 保留金额精度和版本确认，隔离真实预算保存及单项同步操作；未知结果不显示成功，确认失败留在可见上下文，取消不得发送写入。

# Risks
Teleport 脱离页面根样式；维护包含长诊断和危险操作，不能叠加焦点陷阱或丢失错误。未知计量不能在费用明细中伪装为零。

# Verification plan
精确弹窗浏览器用例覆盖可访问性、直达、冲突与故障；既有隔离管理用例验证真实预算和会话，金额单元合同保留。

## Verification cases
- AC-1 => M10-STUDIO-DIALOGS-01
- AC-2 => M10-STUDIO-DIALOGS-01

## Gates
- e2e => AC-1, AC-2
- web-quality => AC-1, AC-2
- harness-integrity => AC-1, AC-2
