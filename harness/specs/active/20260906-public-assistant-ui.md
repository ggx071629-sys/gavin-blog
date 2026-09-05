---
id: spec-20260906-public-assistant-ui
level: L1
summary: 完成视觉提案第六阶段的公开问答面板与状态交互
load_when:
  - task:20260906-public-assistant-ui
author: Gavin
task_id: 20260906-public-assistant-ui
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-6.md
documentation_reason: 记录访客问答面板、状态恢复、引用焦点、设备验证和生产资格边界。
state_history:
---

# Context

用户要求完成 ui-fix/PROPOSAL.md 第六阶段。阶段一至五已归档；隔离设计副本尚未迁入产品。基线为 2b5f910；保留无关 UI_AUDIT_REPORT.md 修改。设计依据为 ASSISTANT.md 和 ASSISTANT-DESIGN.md。

# Goal

在真实公开页面迁入阅读批注式问答面板，补齐完整会话状态和交互，使用真实隔离问答及受控故障响应验证。

# Non-goals

不改变 API、存储、默认关闭、供应商调用、生产启用资格；不增加联网、上传、停止生成、长期历史；不发布全站。

# Acceptance criteria

- AC-1: 480px 桌面浮窗、平板抽屉、手机全屏符合现有双主题；全部八个设计宽度、短视口和长内容无横滚，输入与清除可达，可视视口缩小时保持操作可用。
- AC-2: 等待保留问题，欢迎和真实数据说明适时折叠，引用定位与返回对应本轮及本次触发点，未读定位最新回答且上翻不被抢滚动；输入支持 IME、桌面回车与手机换行。
- AC-3: 恢复、拒答、限流、断线、失效、结果检查及清除准确区分，检查不重新提问；迟到响应不恢复旧正文，恢复和清除期间禁止重复提交。
- AC-4: 真实隔离提问和来源导航通过，默认关闭零请求、引用校验、进行中刷新、多轮上下文、清除代际与菜单焦点互斥保持。
- AC-5: 文档、设计差异、验证结果和回退方式可复查；未执行真机或生产资格检查不得写为通过。

# Risks

UI 状态不能冒充服务器准入。清除和状态读取必须使用同一代际隔离。浏览器设备模拟只能证明布局、IME 事件与可视视口响应，不证明实体手机键盘。设计副本只作为起点，不能取代验证。

# Verification plan

## Verification cases

- AC-1 => M09-UI-LAYOUT-01
- AC-2 => M09-UI-INTERACTION-01
- AC-3 => M09-UI-STATES-01
- AC-4 => M09-P0-01, M09-P1-01, M09-UI-BOUNDARY-01
- AC-5 => M08-DOCS-01

## Gates

- e2e => AC-1, AC-2, AC-3, AC-4
- web-quality => AC-4
- harness-integrity => AC-5
