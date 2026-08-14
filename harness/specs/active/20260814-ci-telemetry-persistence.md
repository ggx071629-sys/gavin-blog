---
id: spec-20260814-ci-telemetry-persistence
level: L1
summary: 在 CI 成功或失败后持久化脱敏 Harness telemetry 摘要
load_when:
  - task:20260814-ci-telemetry-persistence
author: Codex
task_id: 20260814-ci-telemetry-persistence
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - harness/telemetry/README.md
  - harness/docs/operations/release-readiness.md
documentation_reason: CI telemetry 的持久化范围、保留周期、失败语义和人工解释边界属于长期观测与发布合同
state_history:
---

# Context

本地 release runner 已生成只含允许字段的追加式 telemetry，但 GitHub Actions runner 是临时环境，运行结束后本地 JSONL 随之消失，跨运行趋势没有可复查输入。直接上传原始 telemetry、日志或工作区内容会扩大敏感信息和存储边界，也可能让观测流程掩盖权威 gate 的失败。

# Goal

让每次 GitHub release workflow 无论权威 gate 成功或失败，都生成可审计的脱敏 summary 与 health 派生结果，写入 GitHub Job Summary 并以短保留期 artifact 保存，同时维持只读权限、不可变 action 依赖和原 release 失败语义。

# Non-goals

- 不上传原始 JSONL、stdout/stderr、环境变量、绝对路径、用户内容或 `.run/`、`my_image/`、`my_blog_fork/`。
- 不自动提交 telemetry summary，不改变验证门槛，也不直接触发 Evolution。
- 不新增外部可观测平台、部署流程或 GitHub 仓库公开性要求。

# Acceptance criteria

- AC-1: release workflow 在权威 gate 成功或失败后都运行 telemetry 派生步骤，并从 runner 本次生成的本地事件计算 JSON summary 与 health。
- AC-2: CI 只把脱敏 summary 与 health 写入 runner 临时目录；artifact 路径不包含原始 JSONL、日志、工作区目录或三个永久排除目录。
- AC-3: GitHub Job Summary 展示有限的人类可读 telemetry 结果，生成或上传失败会显式失败，且不会把已失败的权威 release gate 改为成功。
- AC-4: artifact 使用固定提交 SHA 的官方 upload action、短期保留和缺失文件失败策略；workflow 继续只拥有 `contents: read` 权限。
- AC-5: 静态回归测试锁定 always 语义、两类派生产物、Job Summary、artifact 范围、保留策略、不可变 action 和禁止原始 telemetry 上传。
- AC-6: telemetry policy 与 release readiness 文档说明 CI 持久化边界、保留期、观察不驱动行为原则和 GitHub 存储成本。
- AC-7: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

# Risks

- YAML 表达式或失败条件书写错误会导致 gate 失败时不产出摘要，或意外吞掉失败状态。
- artifact 路径过宽可能把本地原始事件、排除目录或其他工作区数据上传。
- telemetry CLI 若在无事件时失败，会让依赖安装前的失败缺少摘要；必须保留合法空结果语义。
- 私有仓库 artifact 会消耗 GitHub Actions 存储配额，因此保留期与内容必须严格受限。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
