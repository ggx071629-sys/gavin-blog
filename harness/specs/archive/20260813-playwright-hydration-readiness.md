---
id: archive-20260813-playwright-hydration-readiness
level: L2
summary: 统一 Playwright hydration 就绪等待，覆盖 Linux 冷启动而不放宽普通断言
load_when:
  - task:20260813-playwright-hydration-readiness
author: Codex
task_id: 20260813-playwright-hydration-readiness
status: compressed
documentation_impact: none
documentation_reason: 仅统一既有 data-hydrated 测试信号的有界等待实现，不改变产品行为、CI 拓扑或长期运维合同
state_history:
---

# 20260813-playwright-hydration-readiness

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为所有 Playwright 套件提供唯一、显式且有界的 hydration readiness helper，使 Linux 冷启动拥有合理启动窗口，同时保持 hydration 信号、普通断言严格度与零重试策略不变。

## Acceptance criteria

- AC-1: `apps/web/tests` 提供唯一共享 `expectHydrated(page)` helper，继续断言 `app-root` 的 `data-hydrated=true`，仅该 readiness 等待显式使用 30 秒上限。
- AC-2: E2E、quality 与 failure-state 测试全部复用 helper，不再散布默认 5 秒或各自的 hydration 等待实现。
- AC-3: Playwright 配置维持零重试，普通断言超时不被放宽；hydration 在 30 秒内未完成仍确定性失败。
- AC-4: Harness 机器回归测试约束 helper 的信号、超时与唯一性，阻止重新引入散布的 hydration 断言。
- AC-5: 本地 release profile 完整通过，并产生与实现 HEAD 对应的 schema v2 evidence；随后现有 PR 分支的真实 GitHub Actions 被重新验证。

## Result

Verified and closed by the harness close command.

## Evidence

[20260813-playwright-hydration-readiness.json](../../verification/evidence/20260813-playwright-hydration-readiness.json)

Closed at 2026-08-13T15:20:15.987429+00:00.
