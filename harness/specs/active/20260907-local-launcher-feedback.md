---
id: spec-20260907-local-launcher-feedback
level: L1
summary: 修复 Windows 快捷入口反馈和过期验证诊断
load_when:
  - task:20260907-local-launcher-feedback
task_id: 20260907-local-launcher-feedback
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - README.md
documentation_reason: 说明停止反馈、免暂停方式和24小时验证维护边界
state_history:
---
# Context
Chat probe 超过24小时导致启动失败，停止成功后窗口立即关闭。
# Goal
保持真实问答准入与进程归属，修复反馈；恢复已授权预算内的验证记录。
# Non-goals
不修改有效期、不自动收费、不提高预算、不停止其他入口的进程。
# Acceptance criteria
- AC-1: 停止结果可见，自动化可免暂停并保留退出码。
- AC-2: 过期提示明确，manager早退立即反馈，未运行时显示上次失败原因。
# Risks
不输出密钥，不绕过签名校验，保留PID复用保护和Job清理。
# Verification plan
## Verification cases
- AC-1 => M08-P1-99
- AC-2 => M08-P1-99
## Gates
- api-tests => AC-1, AC-2
