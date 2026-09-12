---
id: spec-20260912-assistant-feedback
level: L1
summary: Q3-05 提供短会话内无正文赞踩和被动后台观测
load_when:
  - task:20260912-assistant-feedback
task_id: 20260912-assistant-feedback
status: active
verification_profile: stack
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
documentation_reason: 反馈接口、告知、短留存和删除语义跨端生效。
state_history:
---

# Context
用户为 Q3-05 选择增加无正文赞踩，未选择正文纠错或外部告警。

# Goal
为当前短会话的有效回答保存一个可修改/撤销的赞踩选择；后台展示有界、无正文反馈与异常统计。

# Non-goals
不采集评价正文，不发送外部告警、不增加模型调用，不把赞踩当正确率或自动训练标签。

# Acceptance criteria
- AC-1: 反馈受原 Origin、Cookie、CSRF、会话和速率保护，只能评价自己的有效回答；同 turn 幂等覆盖或撤销，不携带正文、不调用模型。
- AC-2: 反馈不延长原回答TTL，正文到期/清除时删除；无正文诊断保留7天并由既有清理器删除，清理失败不宣称成功。
- AC-3: 公开回答可赞踩并撤销，提交/失败状态准确，恢复严格解析选择；界面告知用途和删除语义，过期/清除不接纳迟到结果。
- AC-4: 管理端只读展示当前有效赞踩及阶段统计/已有错误异常提示；契约生成同步，用户反馈不冒充正确率，未选正文采样与外部告警有明确范围说明。

# Risks
匿名反馈有选择偏差和滥用可能；短TTL不支持永久质量追溯。保留调用与并发保护。

# Verification plan
## Verification cases
- AC-1 => M09-FEEDBACK-API-01
- AC-2 => M09-FEEDBACK-TTL-01
- AC-3 => M09-FEEDBACK-WEB-01
- AC-4 => M09-FEEDBACK-ADMIN-01, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2, AC-4
- web-quality => AC-3, AC-4
- e2e => AC-3, AC-4
- harness-integrity => AC-4
