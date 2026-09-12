---
id: spec-20260912-assistant-technical-text
level: L1
summary: 允许有依据的比较符号和数组表达并保留输出安全
author: Codex
load_when:
  - task:20260912-assistant-technical-text
task_id: 20260912-assistant-technical-text
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明纯文本技术表达与禁止HTML/模型自造引用的边界。
state_history:
---
# Context
G05 中原文一致的 x < 10 与 a[1] 被当作非法结构；输出仍由受控引用编号与纯文本正文组成。
# Goal
允许有支持的比较符号、数组下标与简单类型参数；保留HTML、危险链接、图片及游离引用标记的拒绝，并保留来源地址转标题行为。
# Non-goals
不启用任意HTML、Markdown执行或自定义模型引用编号；不放宽事实/数量支持。
# Acceptance criteria
- AC-1: 有依据的中英文比较、数组和简单泛型可通过，技术表达中的数字变化仍被拒绝。
- AC-2: script/HTML、危险链接、Markdown图片、javascript和手写引用标记仍拒绝；受绑定来源地址继续只显示正确标题，引用闭合与不支持陈述保护不回退。
# Risks
语法识别是有限的；复杂代码若无法区分则仍拒绝。允许纯文本技术语法不意味着允许可执行输出。
# Verification plan
## Verification cases
- AC-1 => M09-TECHNICAL-TEXT-01, M09-QUANTITY-BINDING-01
- AC-2 => M09-ANSWER-PATHS-01, M09-GROUNDING-02, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
