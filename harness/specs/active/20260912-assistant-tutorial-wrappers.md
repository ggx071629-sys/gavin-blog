---
id: spec-20260912-assistant-tutorial-wrappers
level: L1
summary: 校验真实教程回答中的重复主题引介和英文完整通知关系
load_when:
  - task:20260912-assistant-tutorial-wrappers
author: Codex
task_id: 20260912-assistant-tutorial-wrappers
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明重复主题引介仅在与后句一致时归一化，保留有限英文关系范围。
state_history:
---

# Context

最终语言提示的2次实测均非空且英文正确，但中文重复主题引介与英文完整通知关系仍误拒。只改校验器，保留这些原始模型输出进行离线重放，避免重复付费生成。

# Goal

允许同一主题重复引介及完整邮件通知关系的已确认英文表达；完整事实内容、标题、原因和限定保持核对。

# Non-goals

不修改提示、生成参数、调用次数或生产资格；不允许任意引介语消除未知事实；真实攻击验收仍需最终提示复验。

# Acceptance criteria

- AC-1: 两个真实输出的合法重复引介/英文完整关系通过；错误主题、协议、否定、限定和新增事实仍拒绝。
- AC-2: 数值、事实语境、讨论以及运行器授权边界回归通过，文档明确有限范围，不以离线关闭替代G07实际模型验收。

# Risks

去除引介语可能掩盖错误主题；仅当引介主题与后句同前缀且保留完整后句时消除重复，不删除任意冒号前内容。

# Verification plan

## Verification cases

- AC-1 => M09-G07-REPLAY-01
- AC-2 => M09-CLAIM-CONTEXT-01, M09-QUANTITY-BINDING-01, M09-DISCUSSION-CONTEXT-01, M09-G07-PREPARE-01, M09-G07-RUNNER-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-2
