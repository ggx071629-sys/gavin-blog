---
id: archive-20260911-assistant-resume-storage
level: L2
summary: Q3-03 简历版本缓存和索引失效边界
load_when:
  - task:20260911-assistant-resume-storage
task_id: 20260911-assistant-resume-storage
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录内容库缓存、资格及清理语义。
evidence_sha256: 14cb012956e1989c26e32e3854667513423fad04157c1594fd0b3373c9bf6432
state_history:
---

# 20260911-assistant-resume-storage

Deterministic compressed record. The original active spec remains in Git history.

## Goal

保存有界PDF/文本版本，以绑定代次和任务lease阻止迟到提交，立即撤销旧资格，版本限定清理派生索引。

## Acceptance criteria

- AC-1: 迁移增加独立单例来源、版本和请求记录；PDF/正文在内容库，同hash/管线复用版本；换址/清空递增epoch并删除缓存，A到B到A不会复活引用。
- AC-2: 短事务检查epoch/request/owner/token/fence/lease；检查失败立即暂停，发现新hash先停旧证据再解析；过期或被替代工作不能写版本/outbox。
- AC-3: resume投影可重建并混合检索；hydrate拒绝失败/旧版；索引完成才可用，版本限定purge不能删除新版本，多代索引旧片段可清理。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-resume-storage.json](../../verification/evidence/20260911-assistant-resume-storage.json)

SHA-256: `14cb012956e1989c26e32e3854667513423fad04157c1594fd0b3373c9bf6432`

Closed at 2026-09-10T18:04:57.352432+00:00.
