---
id: spec-20260910-studio-trial
level: L1
summary: 对齐试问布局并保留真实会话和引用状态
load_when:
  - task:20260910-studio-trial
task_id: 20260910-studio-trial
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录试问布局、实际会话及计费呈现边界。
state_history:
---

# Context
U2-01 已验收。现有试问接入管理员会话与 SSE，原型只是布局和空态参考。

# Goal
桌面采用说明/对话两列，手机单列；空态、问题、回答依据和输入操作采用选定稿层级。保留真实状态及会话操作。

# Non-goals
不替换真实回答，不调用生产模型，不改公开面板、供应商、服务端预算或准入。

# Acceptance criteria
- AC-1: 试问桌面分区、手机堆叠，双主题 320/390/1440px 无溢出且 axe 通过；空态、真实回答、折叠依据、输入与发送可读可操作。
- AC-2: 隔离真实会话完成提问、结算、恢复及清空；引用仍只指向安全公开来源；未满足试问条件时按钮与快捷键均不能提交。

# Risks
迁移模板不能卸载隐藏的现有会话；暂停接收不等于取消费用，必须保留原提示。禁止用模拟回答代替真实 API 流程验收。

# Verification plan
复用隔离助手集成用例与引用合同，增加试问状态截图、会话恢复和关闭条件下快捷键验证。

## Verification cases
- AC-1 => M10-STUDIO-TRIAL-01
- AC-2 => M10-STUDIO-TRIAL-01

## Gates
- e2e => AC-1, AC-2
- web-quality => AC-1, AC-2
- harness-integrity => AC-1, AC-2
