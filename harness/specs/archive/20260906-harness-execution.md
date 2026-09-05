---
id: archive-20260906-harness-execution
level: L2
summary: 干净快照前检、无认证局部诊断与精确隔离执行
load_when:
  - task:20260906-harness-execution
author: Codex
task_id: 20260906-harness-execution
status: compressed
documentation_impact: required
documentation_targets:
  - harness/workflows/verify.md
  - harness/docs/decisions/20260906-harness-execution.md
documentation_reason: 明确快照检查、初始化、诊断资格、身份核验与批次隔离的运行合同
evidence_sha256: 90d0b43a487f1986fbc2e98c8fd261ea8f4aaa69078589fdfbfc5f3ee4843fa3
state_history:
---

# 20260906-harness-execution

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不缩小完整任务影响范围的前提下，把快照缺陷和初始化失败前置，提供不授予认证的精确局部诊断，并以完整测试身份和显式数据策略控制批次执行。只有同条件成本证据达标才默认开放合并策略。

## Acceptance criteria

- AC-1: 固定 HEAD 快照检查先于依赖链接、初始化与产品执行，失败时消费者不执行；同快照结果承担 integrity gate。
- AC-2: 所选配置显式声明初始化合同，每隔离上下文只执行一次；失败保存阶段与精确消费者，Harness-only 不启动 Node。
- AC-3: diagnose 按当前 case 或可信失败子集隔离执行，不覆盖正式证据、账本 aggregate 或关闭资格；不确定引用阻断。
- AC-4: 精确身份包含 config/project/path/title_path，收集与执行拒绝重复、遗漏、扩张、跳过、重试和同数不同身份；数据未声明或独占时每身份独立 runtime。
- AC-5: 批次产物独立保留，阶段失败有来源且后续消费者 not-run；输入漂移及清理失败继续阻断认证。批量执行默认关闭，须通过对称配对成本测量后才能启用。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-harness-execution.json](../../verification/evidence/20260906-harness-execution.json)

SHA-256: `90d0b43a487f1986fbc2e98c8fd261ea8f4aaa69078589fdfbfc5f3ee4843fa3`

Closed at 2026-09-05T19:45:05.302099+00:00.
