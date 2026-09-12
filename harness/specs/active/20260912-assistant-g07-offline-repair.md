---
id: spec-20260912-assistant-g07-offline-repair
level: L1
summary: 修复真实正常教程改写误拒并准备空答复验
load_when:
  - task:20260912-assistant-g07-offline-repair
author: Codex
task_id: 20260912-assistant-g07-offline-repair
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明有限教程转述边界及空答提示改进尚需真实模型复验。
state_history:
---

# Context

Q2-06 的24次真实调用已耗尽授权。两条有据教程转述误拒，两条相关问题空答；危险原因对照缺少原因证据。先离线修复，真实复验前另申请次数。

# Goal

重放真实有据转述并保留否定、主体、限定和注入防护；明确提示如何回答相关教程，修正合成材料歧义，完成离线验收。Q2-06真实模型结果另行验收。

# Non-goals

不新增模型调用、在线重试、通用语义判定或生产资格；不把空答改为成功，不覆盖旧实验记录。

# Acceptance criteria

- AC-1: 两条真实有据正常回答离线重放可用，教程转述的否定、主体、限定、错误事实与错误标题反例仍拒绝。
- AC-2: 提示明确技术讨论可答及部分有据优先；空blocks仍失败；24个修订挑战满足原预算，正常对照有明确证据，准备和断网运行器不新增真实调用。
- AC-3: 既有事实语境、数量、讨论防护及提示历史预算回归通过；文档区分离线结果与未验证的真实空答质量。

# Risks

宽泛删除转述前缀可能掩盖主体错配；仅对文章自身的有界语法做等价处理，不删除任意逗号限定。提示改进无法离线证明模型不再空答。

# Verification plan

## Verification cases

- AC-1 => M09-G07-REPLAY-01
- AC-2 => M09-G07-PREPARE-01, M09-G07-RUNNER-01
- AC-3 => M09-CLAIM-CONTEXT-01, M09-QUANTITY-BINDING-01, M09-DISCUSSION-CONTEXT-01, M09-DEFENSE-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-3
