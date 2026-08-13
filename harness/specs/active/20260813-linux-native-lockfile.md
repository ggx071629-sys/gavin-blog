---
id: spec-20260813-linux-native-lockfile
level: L1
summary: 补齐 npm 锁文件中的 Linux 原生可选依赖，使 GitHub Ubuntu runner 可重建 Nuxt
load_when:
  - task:20260813-linux-native-lockfile
author: Codex
task_id: 20260813-linux-native-lockfile
status: active
verification_profile: release
documentation_impact: none
documentation_targets:
documentation_reason: 仅补齐既有 Rollup/LightningCSS 版本的 Linux 安装闭包和机器回归测试，不改变用户行为、发布流程或长期运维合同
state_history:
---

# Context

PR #1 的首个真实 GitHub Actions run 在 Ubuntu 的 `npm ci` 阶段失败。日志确认 `package-lock.json` 只含根级 Windows 原生 Rollup/LightningCSS 安装条目；Rollup 虽声明 Linux optional dependency，但 lockfile 没有对应 `node_modules/@rollup/rollup-linux-x64-gnu` 解析记录，导致 `nuxt prepare` 无法加载原生模块。此前 Windows 本地 release 全部通过，因此该缺口只能在干净 Linux runner 暴露。

# Goal

在不降低 `npm ci`、不重试非确定性安装和不跳过 Nuxt postinstall 的前提下，为 Windows 与 GitHub Ubuntu x64 同时固定 Rollup 和 LightningCSS 原生可选依赖，并用机器测试约束版本与 lockfile 完整性。

# Non-goals

- 不改用 `npm install`，不删除 lockfile，不在 CI 失败后动态修改依赖树。
- 不升级 Nuxt、Rollup、LightningCSS、Node 或 npm 主版本。
- 不增加 musl、ARM 或其他当前没有 runner 的平台矩阵。
- 不改变应用运行时、API 契约、部署拓扑或生产配置。

# Acceptance criteria

- AC-1: 根 `optionalDependencies` 同时显式固定 Windows 与 Linux x64 GNU 的 Rollup 4.62.3、LightningCSS 1.33.0 原生包。
- AC-2: `package-lock.json` 包含四个根声明及对应四个 `node_modules` package record，版本、CPU、OS 与 optional 标记一致。
- AC-3: Harness 回归测试解析 JSON 而非文本猜测，阻止平台包缺失、版本漂移或 Linux 包未锁定。
- AC-4: Windows 本地 `npm ci`/权威 release gate 仍能忽略不兼容 Linux optional 包并完整通过。
- AC-5: 变更产生新的 release-profile schema v2 evidence，供 PR 后续 GitHub change coverage 消费。

# Risks

- npm 对跨平台 optional dependencies 的 lockfile 处理存在历史缺陷；必须检查实际 package record，而不能只看 Rollup 自身的 optionalDependencies 声明。
- 锁定 Linux GNU 只覆盖 GitHub `ubuntu-latest` 当前 x64 glibc runner，不代表 musl/ARM 支持。
- 当前 registry 最新 Rollup 已是 4.62.4；本任务必须保持应用现有 4.62.3，不夹带升级。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5
