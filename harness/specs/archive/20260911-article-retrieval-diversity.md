---
id: archive-20260911-article-retrieval-diversity
level: L2
summary: 避免重复切片挤掉其他文章并隐藏来源路径文本
load_when:
  - task:20260911-article-retrieval-diversity
task_id: 20260911-article-retrieval-diversity
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录候选来源覆盖和面向用户的标题引用规则。
evidence_sha256: 8aebe3dec7ebb46b1e009d496a978e447f3136a7290209ffc4a182f65a5c73dd
state_history:
---

# 20260911-article-retrieval-diversity

Deterministic compressed record. The original active spec remains in Git history.

## Goal

扩大默认候选池至32条（可配置到128），证据组装上限扩大至24000字符；在候选上限前按当前有效来源轮转，优先不同资料的首个命中，再追加同来源切片；去掉用户可见的来源路径文本并保留标题跳转。

## Acceptance criteria

- AC-1: 默认候选32条、组装上限24000字符且可配置，模型输入及费用上限不变；同一资料多个高排名切片不会挤掉可用的其他来源首项，过期/删除资料仍不返回，真实两个技术文章均可进入提示。
- AC-2: 提示描述不提供来源路径，要求正文用标题和引用；来源卡片不显示裸路径，仍按原路径跳转。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-article-retrieval-diversity.json](../../verification/evidence/20260911-article-retrieval-diversity.json)

SHA-256: `8aebe3dec7ebb46b1e009d496a978e447f3136a7290209ffc4a182f65a5c73dd`

Closed at 2026-09-11T04:46:32.100245+00:00.
