---
id: archive-20260813-github-ci-enforcement
level: L2
summary: 将本地 release 与 Harness 变更覆盖门禁接入 smart_blog 的 GitHub Actions
load_when:
  - task:20260813-github-ci-enforcement
author: Codex
task_id: 20260813-github-ci-enforcement
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/operations/release-readiness.md
documentation_reason: 远端仓库、CI 运行入口、可信比较基线和合并约束改变了长期发布保证边界
state_history:
---

# 20260813-github-ci-enforcement

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立最小、可复现的 GitHub Actions release workflow，在 pull request、main push 与人工触发时从干净检出安装锁定依赖，并以可信 base/head 强制执行 Harness change coverage 与完整 release gate。

## Acceptance criteria

- AC-1: workflow 在 pull request、main push 与 workflow dispatch 上运行，权限最小化、并发可取消，checkout 保留完整 Git 历史。
- AC-2: Ubuntu runner 使用显式 Python/Node 版本，从锁文件安装 Node 依赖，在 `apps/api/.venv` 安装 API dev 依赖，并安装 release gate 所需 Chromium 系统依赖。
- AC-3: workflow 为 PR、push 和人工运行确定性解析非空 `HARNESS_BASE_REF` 与 `HARNESS_HEAD_REF`，拒绝全零/不可解析基线，不允许远端 CI 进入 local-only coverage skip。
- AC-4: CI 唯一权威执行入口是 `npm run quality:release`；`.github/workflows/` 被纳入 Harness risk paths，workflow 与解析规则有静态测试覆盖。
- AC-5: README 与 release-readiness 准确说明 smart_blog 远端、CI 覆盖范围、排除目录、merge-commit 可达性约束，以及 CI 不等于 production-ready。
- AC-6: 本任务自身通过 release profile 的隔离验证，并产生可供远端 change coverage 消费的 schema v2 evidence。

## Result

Verified and closed by the harness close command.

## Evidence

[20260813-github-ci-enforcement.json](../../verification/evidence/20260813-github-ci-enforcement.json)

Closed at 2026-08-13T14:14:31.150164+00:00.
