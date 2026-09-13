---
id: archive-20260813-linux-native-lockfile
level: L2
summary: 补齐 npm 锁文件中的 Linux 原生可选依赖，使 GitHub Ubuntu runner 可重建 Nuxt
load_when:
  - task:20260813-linux-native-lockfile
author: Codex
task_id: 20260813-linux-native-lockfile
status: compressed
documentation_impact: none
documentation_reason: 仅补齐既有 Rollup/LightningCSS 版本的 Linux 安装闭包和机器回归测试，不改变用户行为、发布流程或长期运维合同
state_history:
---

# 20260813-linux-native-lockfile

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不降低 `npm ci`、不重试非确定性安装和不跳过 Nuxt postinstall 的前提下，为 Windows 与 GitHub Ubuntu x64 同时固定 Rollup 和 LightningCSS 原生可选依赖，并用机器测试约束版本与 lockfile 完整性。

## Acceptance criteria

- AC-1: 根 `optionalDependencies` 同时显式固定 Windows 与 Linux x64 GNU 的 Rollup 4.62.3、LightningCSS 1.33.0 原生包。
- AC-2: `package-lock.json` 包含四个根声明及对应四个 `node_modules` package record，版本、CPU、OS 与 optional 标记一致。
- AC-3: Harness 回归测试解析 JSON 而非文本猜测，阻止平台包缺失、版本漂移或 Linux 包未锁定。
- AC-4: Windows 本地 `npm ci`/权威 release gate 仍能忽略不兼容 Linux optional 包并完整通过。
- AC-5: 变更产生新的 release-profile schema v2 evidence，供 PR 后续 GitHub change coverage 消费。

## Result

Verified and closed by the harness close command.

## Evidence

[20260813-linux-native-lockfile.json](../../verification/evidence/20260813-linux-native-lockfile.json)

Closed at 2026-08-13T14:37:24.217838+00:00.
