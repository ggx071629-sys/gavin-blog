---
id: spec-20260912-assistant-tutorial-relations
level: L1
summary: 保留教程风险解释关系并区分跨语言事实和支持引文
load_when:
  - task:20260912-assistant-tutorial-relations
author: Codex
task_id: 20260912-assistant-tutorial-relations
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明明确风险原因关系的有限核对与跨语言空答仍须实测的边界。
state_history:
---

# Context

授权100次/2元后的首轮24次中，6正常对照仅1通过、4 grounding、1空答。新增改写暴露文中/标题归属与显式危险原因句合并误拒。传输全部通过不是质量通过。

# Goal

比较完整的教程归属和显式危险原因关系，保留主题、原因、否定和限定；提示明确跨语言答案与原语言支持引文。运行器支持精确选择少量诊断样例，仍消费同一累计账本。

# Non-goals

不放行仅关键词相似、任意翻译、隐含因果或无据拒答说明；不伪造空答成功，不自动重试供应商失败，不改变生产开关。

# Acceptance criteria

- AC-1: 两轮正常教程转述以及新的中文危险原因正例通过；替换对象、原因、否定、条件与撤回反例拒绝。
- AC-2: 所有24个提示在原上限内，跨语言处理保留原文quote；空blocks仍失败。运行器精确选择样例，不自动重复或扩大选定范围，仍禁止未授权调用并保留失败。
- AC-3: 既有事实语境、数量、讨论与历史提示门禁通过，文档如实记录有限范围和真实质量待验证。

# Risks

句子连接不能创造因果，仅在来源明确解释危险且紧邻同一指代原因时匹配；自由翻译仍缺少通用语义保证，必须如实保留失败。

# Verification plan

## Verification cases

- AC-1 => M09-G07-REPLAY-01
- AC-2 => M09-G07-PREPARE-01, M09-G07-RUNNER-01
- AC-3 => M09-CLAIM-CONTEXT-01, M09-QUANTITY-BINDING-01, M09-DISCUSSION-CONTEXT-01, M09-DEFENSE-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-3
