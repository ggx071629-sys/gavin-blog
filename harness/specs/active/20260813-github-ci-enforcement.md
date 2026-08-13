---
id: spec-20260813-github-ci-enforcement
level: L1
summary: 将本地 release 与 Harness 变更覆盖门禁接入 smart_blog 的 GitHub Actions
load_when:
  - task:20260813-github-ci-enforcement
author: Codex
task_id: 20260813-github-ci-enforcement
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/operations/release-readiness.md
documentation_reason: 远端仓库、CI 运行入口、可信比较基线和合并约束改变了长期发布保证边界
state_history:
---

# Context

本地 Harness 已有 `quality:release`、schema v2 隔离 evidence 和基于 Git diff 的 change coverage，但此前没有 remote 或 CI provider，任何检查都可被本地绕过。现在已获授权接入私有仓库 `ggx071629-sys/smart_blog`；远端 main 只有一个初始 README commit，本地已用保留双方历史的 merge 接入，且 `my_blog_fork/`、`.run/`、`my_image/` 明确不得推送。

# Goal

建立最小、可复现的 GitHub Actions release workflow，在 pull request、main push 与人工触发时从干净检出安装锁定依赖，并以可信 base/head 强制执行 Harness change coverage 与完整 release gate。

# Non-goals

- 不推送或打包 `my_blog_fork/`、`.run/`、`my_image/`。
- 不部署应用、不创建生产环境、不配置域名、密钥、数据库或媒体持久化。
- 不伪造 GitHub required check 已启用；分支保护必须在 workflow 首次存在并可识别后单独核实。
- 不使用 force push，不丢弃远端初始历史，不自动合并 PR。

# Acceptance criteria

- AC-1: workflow 在 pull request、main push 与 workflow dispatch 上运行，权限最小化、并发可取消，checkout 保留完整 Git 历史。
- AC-2: Ubuntu runner 使用显式 Python/Node 版本，从锁文件安装 Node 依赖，在 `apps/api/.venv` 安装 API dev 依赖，并安装 release gate 所需 Chromium 系统依赖。
- AC-3: workflow 为 PR、push 和人工运行确定性解析非空 `HARNESS_BASE_REF` 与 `HARNESS_HEAD_REF`，拒绝全零/不可解析基线，不允许远端 CI 进入 local-only coverage skip。
- AC-4: CI 唯一权威执行入口是 `npm run quality:release`；`.github/workflows/` 被纳入 Harness risk paths，workflow 与解析规则有静态测试覆盖。
- AC-5: README 与 release-readiness 准确说明 smart_blog 远端、CI 覆盖范围、排除目录、merge-commit 可达性约束，以及 CI 不等于 production-ready。
- AC-6: 本任务自身通过 release profile 的隔离验证，并产生可供远端 change coverage 消费的 schema v2 evidence。

# Risks

- Playwright/Lighthouse 在共享 runner 上可能耗时或波动；仍复用本地权威 gate，避免形成两套质量语义。
- squash/rebase 会改写 evidence source commit，使 reachability 校验失败；合并策略必须保留已验证提交。
- workflow_dispatch 没有事件 base；只能使用当前 HEAD 的第一父提交，并在无法解析时明确失败。
- 私有仓库套餐或权限可能不支持 required branch protection；必须报告真实 API 结果，不能把 workflow 文件存在等同于不可绕过。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
