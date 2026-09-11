---
id: spec-20260912-assistant-lexical-recall
level: L1
summary: 修复问答检索的中英文自然问句词法召回
author: Codex
load_when:
  - task:20260912-assistant-lexical-recall
task_id: 20260912-assistant-lexical-recall
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录 FTS 词法投影、匹配回退顺序，以及既有 generation 必须重建才能获得中文子串召回。
state_history:
---
# Context
2026-09-12 缺口审查 G08 证明：实时 `assistant_chunk_fts` 使用 unicode61，会把连续中文保存为单个词项，因此“向量检索”无法命中“系统支持全文检索和向量检索”；英文自然问句又被默认 AND 与功能词限制，`How does retry work?` 同样零命中。本轮复核确认该行为在当前 HEAD 仍然存在，且失败发生在词法分支，不能靠向量分支或整体 Recall 掩盖。
# Goal
让中文子串、中文自然问句与英文自然问句在词法分支可召回，同时保持精确术语、代码标识符和旧 generation 的既有行为；并明确既有索引的重建路径，使修复不只在新建索引上成立。
# Non-goals
不更换 tokenizer 或引入外部检索服务；不改变全站 `/api/v1/search` 的文档级索引与查询行为；不提高输入预算、不更换生成模型、不新增在线校验；不把回退形式当作已获得子串召回的证明。
# Acceptance criteria
- AC-1: 中文子串、中文自然问句、英文自然问句、代码标识符与精确术语都能通过真实 FTS5 表召回；端到端检索的候选来源包含词法分支。
- AC-2: 无关问题不被宽松回退召回，未重建的 generation 仍保持原来的召回范围，且不会被当作已经支持中文子串。
- AC-3: 逐字词法投影与既有原文投影都通过完整性审计，FTS 定向修复使用同一投影。
# Risks
放宽为 OR 会扩大候选面，因此只在精确形式无命中时使用；`repair-fts` 与重建是既有受控操作，本次不自动触发，也不改变审计失败时的阻断语义；中文相邻字符对可能把常见字对带进候选，实际入选仍受 RRF、来源轮转与证据预算约束。
# Verification plan
## Verification cases
- AC-1 => M10-UNIT-ASSISTANT-LEXICAL-RECALL-01
- AC-2 => M10-UNIT-ASSISTANT-LEXICAL-RECALL-01
- AC-3 => M10-UNIT-INDEX-INTEGRITY-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
