---
id: archive-20260911-assistant-about-source
level: L2
summary: 将管理员主动发布的关于页纳入现有问答检索和引用
load_when:
  - task:20260911-assistant-about-source
task_id: 20260911-assistant-about-source
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
documentation_reason: 记录新来源的发布资格、索引同步和关于页引用消费边界。
evidence_sha256: 6ae408f292d36c4a1e0e4d6968062805d29793d7ca444ea46354218210ad9c22
state_history:
---

# 20260911-assistant-about-source

Deterministic compressed record. The original active spec remains in Git history.

## Goal

新增 about 来源、明确发布资格、事务 outbox 与失效复检，使相关个人自述可被现有混合检索、预算和引用流程使用。

## Acceptance criteria

- AC-1: 关于页只有主动发布/回滚的当前修订可投影；草稿、自动 seed 和无发布版本不进入来源；升级旧库保留现有数据及四类来源约束。
- AC-2: 发布/回滚在内容事务内登记新版本索引；事务失败不泄漏任务，旧版立即失效，索引等待时其他来源可用，旧任务和重建不能恢复旧版本。
- AC-3: about 正文按既有 tokenizer 切片并参与关键词/向量检索与初次重建，相关证据满足片段预算及最终版本复检，不把整个页面无条件放入提示词。
- AC-4: 回答引用显示“关于 Gavin”并可点击 /about，公开与管理试问共享正确消费合同；提示词允许明确自述、拒绝从文章主题推断能力，冲突事实引用双方。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-about-source.json](../../verification/evidence/20260911-assistant-about-source.json)

SHA-256: `6ae408f292d36c4a1e0e4d6968062805d29793d7ca444ea46354218210ad9c22`

Closed at 2026-09-10T17:30:27.267896+00:00.
