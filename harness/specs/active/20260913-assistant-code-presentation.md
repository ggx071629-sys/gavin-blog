---
id: spec-20260913-assistant-code-presentation
level: L1
summary: Q5-04命令原文在行内代码与围栏代码之间转换时保留相同事实
load_when:
  - task:20260913-assistant-code-presentation
author: Codex
task_id: 20260913-assistant-code-presentation
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 区分命令格式等价和未经证明的改写，记录实际质量限制。
state_history:
---

# Context

Q5真实续期追问被拒绝：当前证据的“执行：”与围栏命令，回答转为相同前缀和行内代码。逐句比较把代码包装当成事实字符，因此相同完整上下文被误拒。

# Goal

仅增加完整支持上下文与完整回答的代码展示等价比较：允许行内代码/完整围栏/普通文本之间的包装差异；保留全部命令、参数、前缀、否定、条件及后续撤回。原始quote仍必须连续精确匹配当前body。

# Non-goals

不支持任意语义改写或翻译，不删除Markdown链接/强调/删除线，不丢弃限定语、不增加在线模型或重试；不改变引用与公开结构。

# Acceptance criteria

- AC-1: 完整上下文的代码包装等价可通过，代码内容/参数、主体、否定、条件、撤回改变或裁剪仍拒绝。
- AC-2: 保持原始引文精确匹配、结构及既有事实/冲突门禁；离线复放和最终真实固定题集结果如实记录，未验证Q5事项不归档。

# Verification plan

## Verification cases

- AC-1 => M09-CODE-PRESENTATION-01
- AC-2 => M09-GROUNDING-01, M09-GROUNDING-02, M09-CONTEXT-CROSS-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-2
