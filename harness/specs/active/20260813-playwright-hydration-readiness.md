---
id: spec-20260813-playwright-hydration-readiness
level: L1
summary: 统一 Playwright hydration 就绪等待，覆盖 Linux 冷启动而不放宽普通断言
load_when:
  - task:20260813-playwright-hydration-readiness
author: Codex
task_id: 20260813-playwright-hydration-readiness
status: active
verification_profile: release
documentation_impact: none
documentation_targets:
documentation_reason: 仅统一既有 data-hydrated 测试信号的有界等待实现，不改变产品行为、CI 拓扑或长期运维合同
state_history:
---

# Context

PR #2 的真实 GitHub Actions Ubuntu run 已完成依赖安装、API、Harness、OpenAPI、Web unit、build、quality、failure-state 与 Lighthouse 检查；核心 E2E 仅首个 `article-loop` 用例失败。失败点是默认 5 秒内 `app-root[data-hydrated]` 仍为 `false`，而后续 25 个核心用例通过。仓库内同一 readiness 信号存在多份实现，部分显式等待 30 秒，部分依赖 Playwright 默认 5 秒，导致冷启动结果受测试顺序与 runner 性能影响。

# Goal

为所有 Playwright 套件提供唯一、显式且有界的 hydration readiness helper，使 Linux 冷启动拥有合理启动窗口，同时保持 hydration 信号、普通断言严格度与零重试策略不变。

# Non-goals

- 不增加 Playwright 全局 expect/test timeout，不启用 retries，不跳过或软化 hydration 断言。
- 不修改 Nuxt hydration 生命周期、应用运行时或用户可见行为。
- 不改变部署、GitHub 分支保护、工作流触发器或 runner 拓扑。
- 不把偶发失败归因于网络并加入盲目重试。

# Acceptance criteria

- AC-1: `apps/web/tests` 提供唯一共享 `expectHydrated(page)` helper，继续断言 `app-root` 的 `data-hydrated=true`，仅该 readiness 等待显式使用 30 秒上限。
- AC-2: E2E、quality 与 failure-state 测试全部复用 helper，不再散布默认 5 秒或各自的 hydration 等待实现。
- AC-3: Playwright 配置维持零重试，普通断言超时不被放宽；hydration 在 30 秒内未完成仍确定性失败。
- AC-4: Harness 机器回归测试约束 helper 的信号、超时与唯一性，阻止重新引入散布的 hydration 断言。
- AC-5: 本地 release profile 完整通过，并产生与实现 HEAD 对应的 schema v2 evidence；随后现有 PR 分支的真实 GitHub Actions 被重新验证。

# Risks

- 30 秒窗口可能延后真正的 hydration 死锁暴露，但仍是有界硬失败，并且只作用于 readiness 信号。
- 机械迁移大量测试文件可能产生错误 import 或遗漏；必须由 TypeScript/Playwright discovery、Harness 静态约束和 release gate 联合验证。
- 本地 Windows 通过不能证明 Ubuntu 冷启动已修复，最终仍需观察真实 GitHub Actions。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5
