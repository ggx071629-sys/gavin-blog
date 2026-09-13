---
id: archive-20260912-assistant-regression-prerequisites
level: L2
summary: 修复三个失效问答回归测试的真实前置条件
load_when:
  - task:20260912-assistant-regression-prerequisites
author: Codex
task_id: 20260912-assistant-regression-prerequisites
status: compressed
documentation_impact: none
documentation_reason: 只修正三个失效测试的前置条件与旧库构造方式，不改产品契约、API、数据模型、迁移或运行行为，因此没有 durable 文档影响。
evidence_sha256: 1e7b863e2813f581a821ce437736d006f0b513a7611fa60a16e3c5d7cd64ed27
state_history:
---

# 20260912-assistant-regression-prerequisites

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让这三个用例在真实前置条件下重新通过：竞态用例的模型调用确实发生，旧库用例的快照来自迁移生成的真实旧结构；并且前置条件本身被显式断言，未来再次漂移时用例直接失败而不是静默跳过目标路径。

## Acceptance criteria

- AC-1: 两个竞态用例在高于固定提示开销的输入预算下运行，模型替身被调用且租约与晚到结果路径真正执行；等待前置不成立时用例失败并说明原因，而不进入后续断言。
- AC-2: 旧库恢复用例用 Alembic 迁移到 20260907_0024 生成旧结构，在快照前断言版本号及缺失的共享预算表与 admin_credentials，并断言快照清单记录同一版本；恢复到 fresh 目标后迁移到 head、生成共享预算策略与空预留表并保留恢复日锁。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-regression-prerequisites.json](../../verification/evidence/20260912-assistant-regression-prerequisites.json)

SHA-256: `1e7b863e2813f581a821ce437736d006f0b513a7611fa60a16e3c5d7cd64ed27`

Closed at 2026-09-11T18:58:40.217337+00:00.
