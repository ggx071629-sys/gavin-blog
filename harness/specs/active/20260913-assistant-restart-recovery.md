---
id: spec-20260913-assistant-restart-recovery
level: L1
summary: 保留本机问答启停选择并在恢复试问时验证新索引资格
load_when:
  - task:20260913-assistant-restart-recovery
task_id: 20260913-assistant-restart-recovery
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明本机启动状态保留与切换后恢复试问的资格验证边界。
state_history:
---
# Context
真实本机启动无条件开关访客入口，覆盖运营选择；切换索引后恢复试问只检查旧资格，必须重启才能重签。
# Goal
正常重启保留启停选择；本机管理员显式恢复试问时完成新索引资格验证，无需重启。
# Non-goals
不自动重建或切换索引，不调用付费 Chat，不修改预算；生产资格仍由既有签名流程签发，不放宽保护条件。
# Acceptance criteria
- AC-1: 本机正常启动和退出保留访客开放或关闭选择及管理员停止状态，失败不开放服务。
- AC-2: 本机恢复试问在新索引完整、签名探测有效和维护保护允许时更新资格并恢复，保持访客关闭；不完整索引、无效探测及维护保护拒绝恢复，非本机入口不自动签发资格。
# Risks
资格签发必须由 API owner 执行并在内容写入栅栏内校验，避免跨版本竞争；不得以恢复试问清除费用或维护锁。
# Verification plan
## Verification cases
- AC-1 => M09-RESTART-STATE-01, M08-DOCS-01
- AC-2 => M10-TRIAL-RECOVERY-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
