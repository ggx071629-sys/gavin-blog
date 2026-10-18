---
id: archive-20260910-assistant-management
level: L2
summary: 将已确认的第二版问答管理设计落实为真实、可验证的运营功能
load_when:
  - task:20260910-assistant-management
task_id: 20260910-assistant-management
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/product/assistant-management-design.md
  - apps/api/README.md
  - packages/contracts/README.md
documentation_reason: 记录管理试问、统一预算与公开入口控制的新契约及运维边界
evidence_sha256: 3aa73bb8381111c315752f6be75325175d67354b53b01dad7d3f3eac6fd74b1a
state_history:
---

# 20260910-assistant-management

Deterministic compressed record. The original active spec remains in Git history.

## Goal

交付概览、管理员试问与高级维护三个视图，统一对外启停和每日预算，提供可操作的同步状态，并完成验证和提交。

## Acceptance criteria

- AC-1: 已确认的第二版落实到 /admin/assistant，概览呈现真实状态、异常处理、费用和同步，移动端及双主题可用，无演示数据。
- AC-2: 公开启停同时控制新问题准入和访客入口；活动页面最多 30 秒刷新一次可用性，读取失败隐藏入口；部署开关仍为上限。
- AC-3: 经管理员认证和 CSRF 校验的短会话试问在普通公开关闭时仍能使用真实检索和模型，引用默认折叠；全局停机、恢复锁、资格失效仍阻断并撤销输出。
- AC-4: 版本化的每日总预算以整数 micro-CNY 原子预留，三类调用共享权威；不得突破部署费用授权，未知调用保守占用且结算幂等。
- AC-5: 同步为下一次有界问答保留额度，预算不足延后新批次；撤回删除不受付费预算限制；同步列表分页且状态不能把历史成功误报为当前同步。
- AC-6: 高级维护保留重建、切换、诊断和全局停止；错误、冲突、清空与请求取消具有真实反馈，验证与文档完成后提交。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-assistant-management.json](../../verification/evidence/20260910-assistant-management.json)

SHA-256: `3aa73bb8381111c315752f6be75325175d67354b53b01dad7d3f3eac6fd74b1a`

Closed at 2026-09-10T00:34:05.363382+00:00.
