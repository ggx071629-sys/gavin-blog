---
id: spec-20260812-harness-verification-lifecycle
level: L1
summary: 补齐派生 verified 状态、证据指纹、验证分层与原子批量关闭
load_when:
  - task:20260812-harness-verification-lifecycle
author: Codex
task_id: 20260812-harness-verification-lifecycle
status: active
verification_profile: focused
state_history:
---

# Context

第一阶段已让 task verify 执行白名单产品 gate，并让 close 强制消费当前 HEAD 的 schema v2 evidence。剩余流程仍有四个缺口：文档把 verified 写成持久状态但文件没有该转换；evidence 只绑定 commit，未显式绑定 spec、验证合同和 gate 配置；不同风险任务没有最低验证层级；批量闭环仍需人工循环且第一个 close 产生的工作树变化会使后续 evidence 失效。

# Goal

把 verified 定义为可由当前有效 evidence 推导的非持久状态，为 evidence 增加可重算指纹，引入 focused／stack／release 验证 profile，并提供统一预检、默认跳过 frozen、失败整体回滚的 `close-all`。

# Non-goals

- 不修改博客应用、公开信息、文章内容、API 或数据库。
- 不修改、恢复、验证或关闭两个 frozen spec。
- 不建立临时 Git worktree、CI 签名或外部证明服务。
- 不宣称本地 JSON 指纹能够抵抗拥有仓库写权限的恶意伪造；本阶段防止意外漂移和流程误用。

# Acceptance criteria

- AC-1: 生命周期只持久化 draft／active／frozen／compressed；verified 是 active spec 在 evidence 对当前 HEAD、spec、合同、profile 与 gate 配置全部有效时推导出的状态，不改写 spec front matter。
- AC-2: schema v2 evidence 记录并校验 source tree、active spec SHA-256、规范化验证合同 SHA-256 和适用 gate/profile 配置 SHA-256；任一漂移使 close 失败。
- AC-3: active spec 必须声明 focused、stack 或 release profile；profile 在 config 中规定最低 gate，task verify 拒绝未知 profile 或缺少 profile 必需 gate，并把 profile 写入 evidence。
- AC-4: `close-all` 按排序统一预检所有非 frozen spec，明确报告并跳过 frozen；任一 active evidence 或 Harness 前置检查失败时不得关闭任何任务。
- AC-5: 批量关闭只在统一预检后变更文件，成功时为每个任务生成 archive 与完成事件并只重建一次索引；任一写入或后验检查失败时恢复全部 active spec、删除本批次生成物并恢复索引。
- AC-6: 单任务 close 复用同一事务关闭实现；全局 verify、task verify、freeze/resume 和既有 compressed evidence 保持兼容。
- AC-7: 模板、verify 工作流、生命周期与 verification policy 说明 profile、派生 verified、证据指纹和推荐命令顺序。

# Risks

- 批量回滚必须只删除本次创建的 archive/event，不能覆盖既有文件或 evidence。
- source tree 是提交级指纹，不替代验证范围清洁检查；两者必须同时成立。
- profile 最低 gate 约束过强会拖慢轻量 Harness 任务，过弱则失去风险分层价值。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- harness-integrity => AC-1, AC-2, AC-3, AC-6, AC-7
