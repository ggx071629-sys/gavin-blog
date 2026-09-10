---
id: spec-20260910-studio-assistant-states
level: L1
summary: 补齐助手中断恢复与长内容状态验收
load_when:
  - task:20260910-studio-assistant-states
task_id: 20260910-studio-assistant-states
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录停止接收、恢复成功清理错误及长同步列表验收。
state_history:
---

# Context
U2-01 至 U2-03 已验收。覆盖审查发现缺少中断后 pending/恢复失败和长同步记录检查；现有 restore 成功分支不会清除上一次恢复错误，可能展示过时失败。

# Goal
补齐阶段状态验收，恢复成功清除过时错误；真实 pending、停止接收及继续计费提示保留。长同步列表和最终概览仍能跨尺寸操作。

# Non-goals
不改变 SSE/API/计费语义、不调用真实模型，不重跑无影响的全部站点流程。

# Acceptance criteria
- AC-1: 停止接收保留后台可能计费与刷新结果提示，pending 阻止重复提交；恢复失败明确可见，成功恢复后清除旧错误，清空失败不假装成功。
- AC-2: 双主题窄屏和长同步记录可滚动、分页过滤保持真实请求参数；最终概览无横溢和 axe 违规，未知/过期状态不画为确定成功。

# Risks
停止网络读取不等于后台取消；界面不能据此允许无条件重复计费。长未断词标题不能挤出弹窗。

# Verification plan
受控传输 fixture 验证 pending/abort/恢复/清空失败，不替代前三项已有真实管理验收；最终概览精确用例与长期状态合同回归。

## Verification cases
- AC-1 => M10-STUDIO-STATES-01
- AC-2 => M10-STUDIO-STATES-01, M10-STUDIO-OVERVIEW-01

## Gates
- e2e => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
