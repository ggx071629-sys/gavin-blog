---
id: spec-20260814-risk-derived-gates
level: L1
summary: 根据 spec 后的已提交变更自动推导不可降低的最低验证 gate
load_when:
  - task:20260814-risk-derived-gates
author: Codex
task_id: 20260814-risk-derived-gates
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/workflows/verify.md
documentation_reason: 风险路径如何推导最低产品 gate 是长期验证合同和日常执行流程的一部分
state_history:
---

# Context

当前 verification profile 只提供静态最低 gate，`focused` 没有必选 gate；spec 作者可以为 API、Web、跨栈、依赖或 Harness 控制面修改选择过轻的验证计划。现有 change coverage 能证明最后风险修改经过某份 evidence，却不能证明该 evidence 根据实际变更类型运行了足够的产品 gate。

# Goal

从 active spec 首次提交到当前 HEAD 的已提交路径中确定性推导最低 gate，并要求 spec 的显式 verification plan 至少包含这些 gate；spec 可以增加验证但不能降低系统推导的风险下限。

# Non-goals

- 不根据自然语言或模型判断风险，不执行 spec 中的任意命令。
- 不改变现有 profile 的静态语义，不自动重写 active spec。
- 不为文档、生成索引或确定性 close 产物强制产品 gate。
- 不合并 PR、不部署、不改变 GitHub 套餐或仓库可见性。

# Acceptance criteria

- AC-1: `config.toml` 声明有序、可验证的 risk routes，每条 route 使用项目相对 prefix/file 匹配并引用已注册 gate。
- AC-2: task verify 以 spec introduction commit 的下一提交至 HEAD 为范围，确定性返回匹配路径、route 和去重后的最低 gate。
- AC-3: verification plan 缺少任一推导 gate 时在产品执行前失败，并报告缺失 gate 与触发路径；spec 不能用较低 profile 绕过。
- AC-4: spec 声明全部推导 gate 或额外 gate 时继续通过现有白名单、AC 覆盖、隔离和 evidence 校验。
- AC-5: risk route 配置、推导结果和变更路径进入规范化 evidence 指纹，配置或 HEAD 漂移使旧 evidence 失效。
- AC-6: 回归测试覆盖 API、Web、contracts/跨栈、依赖/CI/Harness、非风险文档、未知 gate、未提交修改与无实现变化。
- AC-7: 权威验证政策和 verify workflow 明确说明自动风险下限与 spec 只能增加不能降低的规则。
- AC-8: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

# Risks

- 路由重叠会产生多个最低 gate；实现必须稳定去重且保留可解释触发来源。
- spec introduction commit 本身包含 spec 和索引，推导范围必须从该提交之后开始，避免控制文档自触发 release。
- 控制面任务会命中 release route；本任务必须完整验证新机制自身。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8
