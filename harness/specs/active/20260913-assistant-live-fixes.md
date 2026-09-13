---
id: spec-20260913-assistant-live-fixes
level: L1
summary: 修复隔离现场验证发现的助手控制、清除与测试入口问题
author: Gavin
load_when:
  - task:20260913-assistant-live-fixes
task_id: 20260913-assistant-live-fixes
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 明确内容备份围栏与运行控制边界、清除失败及测试模式说明。
state_history:
---
# Context
现场测试发现后台试问、清除和紧急停止被全局内容写围栏拒绝，删除失败先清空视图；隔离构建和持续Worker存在配置缺口，readiness变化后的概览可能陈旧。
# Goal
修复已确认的问题，增加精确回归，按合同核定待验证现象并保留原失败记录。
# Non-goals
不使用真实付费供应商，不修改既有评测结果，不取消内容备份保护，不以替身测试证明生产模型质量。
# Acceptance criteria
- AC-1: 内容围栏持有期间仅运行库会话创建、删除与紧急停止可执行，认证及内容写入保护保持；在途执行失去资格后不得发布回答。
- AC-2: 清除失败保留可见记录并明确未确认服务端清除；成功及202撤销态继续阻止迟到响应恢复正文。
- AC-3: E2E干净构建可启动，持续Worker使用同一测试索引，离线测试说明匹配配置。
- AC-4: 管理开放状态核验当前readiness绑定，费用身份维度与剩余七行缺口按现行合同完成核定。
# Risks
不得把写内容库的问答预算准入接口排除于备份围栏；不得把断网删除未知当作删除失败可安全重发问题。
# Verification plan
## Verification cases
- AC-1 => M09-LIVE-FIXES-01
- AC-2 => M09-LIVE-FIXES-02
- AC-3 => M09-LIVE-FIXES-03
- AC-4 => M09-LIVE-FIXES-04
## Gates
- api-tests => AC-1, AC-3, AC-4
- web-quality => AC-2, AC-3, AC-4
- harness-integrity => AC-1, AC-2, AC-3, AC-4
