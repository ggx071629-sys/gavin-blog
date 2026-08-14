---
id: archive-20260814-evidence-gate-efficiency
level: L2
summary: 固化历史关闭证据关系，并用运行时阶段证明安全消除 release 重复 gate
load_when:
  - task:20260814-evidence-gate-efficiency
author: Codex
task_id: 20260814-evidence-gate-efficiency
status: compressed
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/docs/decisions/20260814-evidence-integrity-and-gate-subsumption.md
documentation_reason: 历史关闭资产的保留规则和 release gate 包含关系会长期改变验证、审查与执行成本边界
state_history:
---

# 20260814-evidence-gate-efficiency

Deterministic compressed record. The original active spec remains in Git history.

## Goal

用全局只读 check 保护确定性关闭资产和原 spec 历史，用保守 taxonomy 区分过渡 evidence 与真正 invalid evidence；同时建立由单一 stage contract、运行时 proof、配置指纹和 evidence 校验共同约束的 gate subsumption，使 release 能在不减少实际测试覆盖的前提下满足已包含的风险/profile 最低 gate。

## Acceptance criteria

- AC-1: 新的全局 history-integrity check 确定性验证每个 compressed archive 都有同 task 的主 evidence 与 lifecycle `spec.completed` event，三者标识和 archive evidence 链接一致，active task 与已关闭 task 不重叠。
- AC-2: history-integrity 通过一次 Git 历史查询确认每个 archive 对应的原 active spec 路径仍可见；失败详情有界且只读，允许没有 completion event 的既有独立 evidence，不修改历史资产。
- AC-3: evidence inventory 将 passed、含 passed product checks、但没有隔离 execution 的早期 schema v2 记录保守分类为明确的 transitional product-reported 等级；存在畸形 execution、失败 check 或缺少 product check 的 schema v2 仍为 invalid。
- AC-4: release subsumption 使用项目内单一 JSON stage contract，逐项声明已注册子 gate、stage、cwd 与 command；解析拒绝越界路径、未知/自身/重复 gate 或 stage，以及与注册 gate 命令和 cwd 不一致的合同。
- AC-5: profile 与风险路由最低 gate 只有在该 gate 被 plan 直接选择，或 plan 选择了拥有有效直接 subsumption contract 的 gate 时才算满足；未证明、传递式或部分包含仍失败并报告触发路径。
- AC-6: release runner 从同一 stage contract 执行每个声明子 gate恰好一次；只有全部声明阶段和原有非合同 release 阶段通过后才输出含 contract SHA-256 与完成 gate/stage 的单一终态 proof。
- AC-7: product gate 即使进程退出 0，也会在 proof 缺失、重复、畸形、hash 漂移或阶段不全时失败；通过时 evidence 保存最小 verified subsumption，fingerprint 覆盖合同内容，close validation 拒绝 proof 或合同漂移。
- AC-8: 回归测试覆盖关闭三件套缺失/错配/active 冲突/历史缺失、过渡与 invalid taxonomy、合同配置篡改、直接满足/可信包含/未证明包含，以及成功和伪造 runtime proof；文档和决策记录能力与边界。
- AC-9: 全局 Harness checks、release profile、隔离清理与当前 schema v2 evidence 完整通过；该 task 的 plan 只映射一次 release gate，不重复执行其已证明包含的子 gate。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-evidence-gate-efficiency.json](../../verification/evidence/20260814-evidence-gate-efficiency.json)

Closed at 2026-08-14T06:40:18.343738+00:00.
