---
id: archive-20260905-harness-resume
level: L2
summary: 以显式影响计划选择模块测试，并验证可信收尾与成本
load_when:
  - task:20260905-harness-resume
author: Gavin
task_id: 20260905-harness-resume
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/decisions/20260905-verification-resume.md
  - harness/workflows/verify.md
documentation_reason: 执行、证据信任边界、失败恢复和关闭职责改变，必须同步耐久决策与操作流程。
evidence_sha256: 848967abe4e6170a05baa376ecd665658b1456a16297b52068d0d37bab6134a1
state_history:
---

# 20260905-harness-resume

Deterministic compressed record. The original active spec remains in Git history.

## Goal

测试范围由逐文件影响分析和逐项依赖判断确定。结构检查不调用 collector；规范 runner 执行所选 exact refs。未知归属阻断，普通任务不自动 release。

## Acceptance criteria

- AC-1: 显式源码归属、case 和依赖理由形成独立计划；未知文件与不完整依赖阻断，未影响模块不执行。
- AC-2: runner 使用受限 Pytest/Vitest/Playwright 选择器；结构检查、plan/status、close 不启动产品 collector。fresh 仅执行所选范围。
- AC-3: 默认不复用；仅具备有界输入合同时允许复用。失败后未执行保持 not-run，旧成功不能覆盖新失败，清理失败和中断不能关闭。
- AC-4: 真实 runner 的完整凭据可以被 close 消费；全复用补足隔离来源，同进程 verify --close 不重跑测试，篡改与关闭竞态拒绝并回滚。
- AC-5: 记录所选范围、实际测试计数、输出字节和耗时，以轻量 fixture 与 Harness/产品所选真实测试验收成本。

## Result

Verified and closed by the harness close command.

## Evidence

[20260905-harness-resume.json](../../verification/evidence/20260905-harness-resume.json)

SHA-256: `848967abe4e6170a05baa376ecd665658b1456a16297b52068d0d37bab6134a1`

Closed at 2026-09-05T15:40:51.489500+00:00.
