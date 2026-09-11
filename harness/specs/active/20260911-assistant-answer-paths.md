---
id: spec-20260911-assistant-answer-paths
level: L1
summary: 问答正文使用来源标题并阻止来源路径回显
author: Codex
load_when:
  - task:20260911-assistant-answer-paths
task_id: 20260911-assistant-answer-paths
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确正文来源地址替换与导航元数据保留的边界。
state_history:
---
# Context
提示已禁止来源 URL 路径，但后端允许正文中的裸路径与完整 URL，历史回答也可能再次带入路径。前端来源卡片已仅显示标题。
# Goal
本站来源的地址在新回答正文中改用可信来源标题，引用跳转保持可用。
# Non-goals
不扩展为全面注入防护，不改数据库或 API schema，不删除已有会话，不隐藏教程中的无关技术路径，不调用真实模型。
# Acceptance criteria
- AC-1: 回答中与当前证据绑定的来源裸路径、完整 HTTP(S) URL 及其查询/片段形式使用来源标题；路径边界不误匹配其他文件或更长路径；引用元数据保留原跳转路径，非法引用及原有危险格式仍被拒绝。
- AC-2: 提示明确历史中的来源路径不得复述，事实仍以本轮证据为准；有效教程路径不受全局斜杠过滤影响。
- AC-3: 实际问答链路的 SSE、会话恢复和新存储历史使用同一处理后的回答，来源导航路径保持不变。
# Risks
页面地址是公开导航信息，修复属于回答呈现约束，不宣称保护服务器文件或阻止所有注入。仅替换可绑定当前证据的来源地址，不猜测未知地址对应的标题。
# Verification plan
## Verification cases
- AC-1 => M09-ANSWER-PATHS-01
- AC-2 => M09-ANSWER-PATHS-02, M09-EVIDENCE-BUDGET-01, M09-EVIDENCE-BUDGET-02, M09-RESUME-PAGES-01
- AC-3 => M09-ANSWER-PATHS-03, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
