---
id: spec-20260911-assistant-resume-admin-ui
level: L1
summary: Q3-05 简历同步状态与立即刷新管理界面
load_when:
  - task:20260911-assistant-resume-admin-ui
task_id: 20260911-assistant-resume-admin-ui
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录首次/换址自动同步、手动刷新与状态展示。
state_history:
---
# Context
后端绑定与显式刷新API已验收；个人名片已有简历URL输入。
# Goal
在现有名片设置旁提供清楚可操作的同步状态，区分保存、排队、检查与索引结果。
# Non-goals
不重设计页面，不修改公开名片或新增定时下载；状态轮询仅管理员页面可见期间运行。
# Acceptance criteria
- AC-1: 展示未配置/处理中/成功/失败、可用性、最后检查与索引时间和可操作错误；仅显式按钮POST刷新。未保存换址时禁用刷新并说明先保存；刷新不重置其他草稿，409提示绑定冲突，429说明冷却。
- AC-2: 保存后重新读取状态，活动任务只轮询GET、离开页面停止；键盘可用、手机无溢出、双主题可读，读状态失败不伪称同步成功。
# Risks
其他管理员换址后不能对着旧表单刷新新绑定；检测epoch变化后禁用直到重新载入资料。轮询不等于重新下载。
# Verification plan
## Verification cases
- AC-1 => M06-RESUME-ADMIN-UI-01
- AC-2 => M06-RESUME-ADMIN-UI-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
