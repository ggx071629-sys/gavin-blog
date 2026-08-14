---
id: spec-20260814-evidence-gate-efficiency
level: L1
summary: 固化历史关闭证据关系，并用运行时阶段证明安全消除 release 重复 gate
load_when:
  - task:20260814-evidence-gate-efficiency
author: Codex
task_id: 20260814-evidence-gate-efficiency
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/docs/decisions/20260814-evidence-integrity-and-gate-subsumption.md
documentation_reason: 历史关闭资产的保留规则和 release gate 包含关系会长期改变验证、审查与执行成本边界
state_history:
---

# Context

现有 71 个确定性关闭任务都保留 archive、`spec.completed` event、主 evidence 三件套，原 active spec 也仍在 Git 历史，但这些关系没有全局可执行门禁，文件被单独删除或错配时只能靠人工发现。73 份主 evidence 中另有两份早期 schema v2 产品记录产生于隔离字段落地之前，inventory 将其标为 `invalid`，混淆了“历史保证较弱”和“内容损坏”。

验证成本也存在可消除重复：风险路由要求 `api-lint`、`api-tests` 时，如果 verification plan 同时选择完整 `release`，当前实现仍先单独运行子 gate，再由 release 重跑。仅声明 `release` 包含这些 gate 不足以防降级；必须让同一机器合同定义子 gate 命令，并由成功运行返回实际完成阶段证明。

# Goal

用全局只读 check 保护确定性关闭资产和原 spec 历史，用保守 taxonomy 区分过渡 evidence 与真正 invalid evidence；同时建立由单一 stage contract、运行时 proof、配置指纹和 evidence 校验共同约束的 gate subsumption，使 release 能在不减少实际测试覆盖的前提下满足已包含的风险/profile 最低 gate。

# Non-goals

- 不删除、迁移、重写或补造任何历史 archive、event、evidence 或 Git commit。
- 不把 schema v1 或过渡 v2 记录升级宣称为当前 schema v2 隔离验证。
- 不减少 `quality:release` 当前执行的 API、Harness、Web、E2E、OpenAPI 与完整性阶段。
- 不允许仅靠 TOML 名称、注释、静态字符串或退出码声称 gate 已被包含。
- 不增加重试、缓存、部署、远端写入，也不要求 GitHub Pro。

# Acceptance criteria

- AC-1: 新的全局 history-integrity check 确定性验证每个 compressed archive 都有同 task 的主 evidence 与 lifecycle `spec.completed` event，三者标识和 archive evidence 链接一致，active task 与已关闭 task 不重叠。
- AC-2: history-integrity 通过一次 Git 历史查询确认每个 archive 对应的原 active spec 路径仍可见；失败详情有界且只读，允许没有 completion event 的既有独立 evidence，不修改历史资产。
- AC-3: evidence inventory 将 passed、含 passed product checks、但没有隔离 execution 的早期 schema v2 记录保守分类为明确的 transitional product-reported 等级；存在畸形 execution、失败 check 或缺少 product check 的 schema v2 仍为 invalid。
- AC-4: release subsumption 使用项目内单一 JSON stage contract，逐项声明已注册子 gate、stage、cwd 与 command；解析拒绝越界路径、未知/自身/重复 gate 或 stage，以及与注册 gate 命令和 cwd 不一致的合同。
- AC-5: profile 与风险路由最低 gate 只有在该 gate 被 plan 直接选择，或 plan 选择了拥有有效直接 subsumption contract 的 gate 时才算满足；未证明、传递式或部分包含仍失败并报告触发路径。
- AC-6: release runner 从同一 stage contract 执行每个声明子 gate恰好一次；只有全部声明阶段和原有非合同 release 阶段通过后才输出含 contract SHA-256 与完成 gate/stage 的单一终态 proof。
- AC-7: product gate 即使进程退出 0，也会在 proof 缺失、重复、畸形、hash 漂移或阶段不全时失败；通过时 evidence 保存最小 verified subsumption，fingerprint 覆盖合同内容，close validation 拒绝 proof 或合同漂移。
- AC-8: 回归测试覆盖关闭三件套缺失/错配/active 冲突/历史缺失、过渡与 invalid taxonomy、合同配置篡改、直接满足/可信包含/未证明包含，以及成功和伪造 runtime proof；文档和决策记录能力与边界。
- AC-9: 全局 Harness checks、release profile、隔离清理与当前 schema v2 evidence 完整通过；该 task 的 plan 只映射一次 release gate，不重复执行其已证明包含的子 gate。

# Risks

- subsumption 若只校验阶段名称会形成虚假覆盖；合同必须同时绑定注册 gate 的 cwd、command 和内容 hash，runner 与 verifier 必须读取同一文件。
- release runner 在中途失败时可能产生部分阶段记录；只有全部阶段完成后的唯一终态 proof 可用于满足最低 gate。
- 历史 schema 曾在未升版本时扩展 execution 字段；taxonomy 必须保守命名，不能回写旧记录或把过渡保证等同当前保证。
- Git 历史检查依赖完整历史；当前 CI 已使用 `fetch-depth: 0`，缺少相关历史时应失败关闭而不是静默跳过。
- 新全局 check 会增加少量固定成本；实现应使用一次 Git 查询和线性文件扫描，避免逐任务启动 Git 进程。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9
