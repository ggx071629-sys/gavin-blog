---
id: spec-20260913-assistant-evidence-role
level: L1
summary: Q5-04从当前已发布字段区分文章元数据和正文证据
load_when:
  - task:20260913-assistant-evidence-role
author: Codex
task_id: 20260913-assistant-evidence-role
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录正文归属的确定性计算与仍未验证的回答范围。
state_history:
---

# Context

Q5-04指令修复后的角色/端口及追问通过定向实际复测；E01仍混淆文章摘要和正文。现有索引把标题/摘要/分类加在正文前，但传给模型的片段缺少字段归属。

# Goal

从当前已发布ArticleRevision内容与投影元数据判定片段是metadata、body或unknown，并仅作为内部提示描述符发送；歧义不猜测。

# Non-goals

不修改文章、公开来源正文/版本/哈希、索引切块或公开API，不放宽事实/引用/注入校验，不将内部标记变成用户事实，不给出全文顺序或完整性保证。

# Acceptance criteria

- AC-1: 仅当前有效公开文章字段可提供片段角色，元数据和正文重叠或混合时保持unknown，不根据标题关键词或片段排名猜测。
- AC-2: 初次hydrate和descriptor重建均计算角色；提示保留原始正文，公开引用/来源不增加字段，撤销/版本规则继续拒绝旧证据。
- AC-3: 在原200次/2元授权内对E01和对照题复测，失败和适用范围保持记录，未验证任务不提前归档。

# Risks

空白规范化只用作字段归属判断，不用于放宽引文匹配；正文与元数据文本重叠不能标成确定的正文。标记不保证模型正确回答。

# Verification plan

## Verification cases

- AC-1 => M09-EVIDENCE-ROLE-01
- AC-2 => M09-EVIDENCE-ROLE-01, M09-CONTEXT-CROSS-01, M09-CURRENT-PROMPT-01
- AC-3 => M09-CURRENT-BUDGET-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-3
