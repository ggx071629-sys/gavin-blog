---
id: spec-20260910-assistant-management
level: L1
summary: 将已确认的第二版问答管理设计落实为真实、可验证的运营功能
load_when:
  - task:20260910-assistant-management
task_id: 20260910-assistant-management
status: active
verification_profile: stack
documentation_impact: required
documentation_targets:
  - harness/docs/product/assistant-management-design.md
  - apps/api/README.md
  - packages/contracts/README.md
documentation_reason: 记录管理试问、统一预算与公开入口控制的新契约及运维边界
state_history:
---

# Context

用户已确认第二版原型，但真实写作台仍为旧版。三个分离账本不能提供跨调用的统一预算；公开关闭会阻断现有匿名管线。必须补齐真实能力，不能用演示数据交付。

# Goal

交付概览、管理员试问与高级维护三个视图，统一对外启停和每日预算，提供可操作的同步状态，并完成验证和提交。

# Non-goals

不启用生产服务，不修改真实供应商费用授权，不编辑模型、密钥或提示词，不索引草稿，不提交其他任务的改动。

# Acceptance criteria

- AC-1: 已确认的第二版落实到 /admin/assistant，概览呈现真实状态、异常处理、费用和同步，移动端及双主题可用，无演示数据。
- AC-2: 公开启停同时控制新问题准入和访客入口；活动页面最多 30 秒刷新一次可用性，读取失败隐藏入口；部署开关仍为上限。
- AC-3: 经管理员认证和 CSRF 校验的短会话试问在普通公开关闭时仍能使用真实检索和模型，引用默认折叠；全局停机、恢复锁、资格失效仍阻断并撤销输出。
- AC-4: 版本化的每日总预算以整数 micro-CNY 原子预留，三类调用共享权威；不得突破部署费用授权，未知调用保守占用且结算幂等。
- AC-5: 同步为下一次有界问答保留额度，预算不足延后新批次；撤回删除不受付费预算限制；同步列表分页且状态不能把历史成功误报为当前同步。
- AC-6: 高级维护保留重建、切换、诊断和全局停止；错误、冲突、清空与请求取消具有真实反馈，验证与文档完成后提交。

# Risks

跨库账本的崩溃窗口、管理员执行隔离、已发送费用不可撤销、恢复旧库重置预算、陈旧公开状态以及并发配置冲突。保持既有租约、fence、资格验证与发布引用复核；不通过临时开启公开开关实现试问。

# Verification plan

另执行 API Ruff、Mypy 与 Web 类型检查；当前 Harness 普通任务只接受已登记 exact test refs 的 gate 集合，静态工具检查单独记录。

## Verification cases

- AC-1 => M10-MANAGEMENT-UI-01
- AC-2 => M10-PUBLIC-AVAILABILITY-01
- AC-3 => M10-ADMIN-TRIAL-01
- AC-4 => M10-TOTAL-BUDGET-01
- AC-5 => M10-SYNC-PRIORITY-01
- AC-6 => M10-MANAGEMENT-UI-01, M10-ADMIN-TRIAL-01, M08-DOCS-01

## Gates

- web-quality => AC-1, AC-2, AC-6
- e2e => AC-1, AC-2, AC-3, AC-6
- api-tests => AC-2, AC-3, AC-4, AC-5, AC-6
- harness-integrity => AC-6
