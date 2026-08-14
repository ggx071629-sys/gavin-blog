---
id: spec-20260814-upload-artifact-node24
level: L1
summary: 升级 CI telemetry artifact action 到官方 Node 24 运行时并消除弃用警告
load_when:
  - task:20260814-upload-artifact-node24
author: Codex
task_id: 20260814-upload-artifact-node24
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - harness/docs/decisions/20260814-python-lock-and-control-plane.md
documentation_reason: CI 供应链的固定 action 版本与运行时基线是长期控制面决策
state_history:
---

# Context

最终 Draft PR CI 在 head `7689b71` 上全部通过，但 GitHub 注解指出固定的 `actions/upload-artifact@v4.6.2` 仍声明 Node 20，runner 正强制使用 Node 24。官方仓库最新稳定 release 为 v7.0.1，tag 指向 commit `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`，其 `action.yml` 明确使用 Node 24。该信息只能由真实远端 CI 暴露，不能把兼容性警告忽略为完全收敛。

# Goal

将唯一 artifact 上传步骤固定到官方 v7.0.1 的完整 commit SHA，在不改变脱敏文件集合、失败语义和保留期的前提下消除 Node 20 弃用依赖。

# Non-goals

- 不升级其他 action、Node/Python/uv 版本或应用依赖。
- 不改变 artifact 内容、名称、路径、保留期、公开性或 telemetry schema。
- 不启用缓存、部署、发布仓库或修改 GitHub 仓库可见性。

# Acceptance criteria

- AC-1: workflow 将 `actions/upload-artifact` 固定到 v7.0.1 对应的完整 commit `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`，注释与官方 tag 一致。
- AC-2: 上传步骤仍为 `if: always()`，只包含 runner temp 下的 sanitized summary/health，`if-no-files-found: error` 与 `retention-days: 14` 不变。
- AC-3: CI 静态测试与全局 supply-chain check 拒绝旧 SHA、浮动 ref、权限或上传边界降级。
- AC-4: 供应链决策文档记录官方 v7.0.1、Node 24 原因和远端 warning 来源，不把版本更新扩张为其他改动。
- AC-5: 本地 release 与最终 Draft PR `quality-release` 在当前 head 通过，最终 run 不再产生 upload-artifact Node 20 弃用注解。

# Risks

- major action 升级可能改变上传实现；本任务只使用 v7 仍支持的 name/path/error/retention 输入，并通过真实私有 CI 验证。
- 仅修改版本注释而未固定正确 commit 会产生虚假供应链保证；测试必须断言精确 SHA。
- 再次推送会额外消耗一次私有 Actions 运行，但不修复会保留已知的运行时弃用风险。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5
