---
id: decision-evidence-integrity-and-gate-subsumption
level: L1
summary: 以关闭资产关系门禁保护历史证据，并用运行时阶段证明约束 release gate 包含关系
load_when:
  - harness-change
  - verification
  - architecture-decision
author: Codex
---

# Decision: evidence integrity and gate subsumption

## Status

Accepted.

## Context

确定性 close 会生成 compressed archive、主 evidence 和 lifecycle `spec.completed` event，并承诺原 active spec 留在 Git 历史；此前只有 close 当下验证，没有持续检查这些资产之后是否被单独删除或错配。旧 schema v2 又曾在未升版本时增加隔离 execution 字段，两份过渡记录被当前 inventory 误称 invalid。

风险路由与 release profile 可能同时要求子 gate 和完整 release。逐个执行 plan 后，release 会再次运行相同 API、Harness、Web 或 E2E 命令；直接把 release 名称当作包含证明虽能降本，却允许 runner 与注册 gate 静默漂移。

## Decision

- 全局 `history-integrity` check 以 compressed archive 为已关闭权威集合，检查 archive、passed 主 evidence、lifecycle completion event 的 task 标识与链接，拒绝 active/closed 重叠，并用一次 Git 查询确认原 active spec 路径仍在当前 HEAD 历史。
- 未带 completion event 的既有独立 evidence 不冒充确定性关闭资产；check 不改写历史。inventory 将无 execution、全部 checks passed 且含 product gate 的早期 schema v2 单列为 `v2-transitional-product-reported`，不提升其保证等级。
- `scripts/release-stage-contract.json` 是 release 可 subsume 子 gate 的单一执行合同，绑定每个注册 gate 的 stage、cwd 与 argv。`config.toml` 只引用合同路径；全局 check 和 task verifier 都要求合同与注册 gate 完全一致。
- release runner 从该合同执行所有声明项，非合同的 change coverage、OpenAPI consistency 等阶段仍保留。只有全部阶段成功后才输出唯一 proof，内容为合同 SHA-256 与有序完成 gate/stage。
- profile 或风险最低 gate 可由 plan 中直接选择的 gate满足，也可由具有有效直接合同的已选择 owner gate满足。禁止未证明包含与传递式推导。
- product gate 对退出 0 仍验证 proof；proof 缺失、重复、畸形、hash 或阶段漂移均失败。verified subsumption 进入 evidence，合同与满足关系进入指纹，close 再次校验。

## Consequences

- 完整 release 的实际测试覆盖不变；当 plan 已选择 release 时，不必再为了满足已包含的最低 gate 重跑相同子命令。
- 合同格式、命令、cwd 或 runner proof 的任何漂移都会在全局完整性、task gate 或 close 中至少一处失败，代价是增加一个小型 JSON 控制面和解析测试。
- 历史关系从“约定存在”变为每次 verify 可执行检查；Git 历史不完整的环境会失败关闭。CI 已使用完整 checkout，本地浅克隆需先取得相关历史。
- 过渡 evidence 被准确降级描述但保持原字节不变；assurance 标签仍不代表重新执行或当前 HEAD 有效。
- 所有约束仍位于同一仓库，能防止误改并提高审查可见性，但在私有 GitHub Free、没有 required review/ruleset 的条件下不是外部不可变信任根。
