---
id: spec-20260812-harness-product-verification-gate
level: L1
summary: 让 task verify 运行白名单产品门禁，并让 close 强制消费当前提交的完整验收证据
load_when:
  - task:20260812-harness-product-verification-gate
author: Codex
task_id: 20260812-harness-product-verification-gate
status: active
state_history:
---

# Context

当前 `verify <task_id>` 和 `close <task_id>` 只执行 Harness 文档结构检查。产品测试失败时，close 仍可能压缩 spec；close 还会覆盖已有 evidence，无法区分产品验证与控制面完整性。历史上另有人工维护的 `.application.json`，但没有统一生成命令、验收标准覆盖校验或当前提交约束。

# Goal

建立可执行、可审计的 task verification：active spec 显式把每项验收标准映射到配置白名单 gate，`verify <task_id>` 在已提交源码上运行这些 gate 并生成紧凑 evidence，`close <task_id>` 只在 evidence 完整、通过且对应当前 HEAD 时才允许压缩。

# Non-goals

- 不改变应用 API、数据库、公开页面、公开信息或文章内容。
- 不执行或修改两个 frozen spec。
- 不实现批量 close、临时 worktree 验证或测试结果数量解析。
- 不从 Markdown 执行任意 shell 命令。
- 不迁移或重写已经 compressed 的历史 evidence。

# Acceptance criteria

- AC-1: 新 active spec 的验收标准使用唯一 `AC-N` 标识，Verification plan 使用确定性 `gate => AC` 语法；未知 gate、重复或未覆盖验收项使 task verify 失败。
- AC-2: 产品 gate 仅来自 `config.toml` 白名单，使用参数数组和受控工作目录运行；evidence 记录命令、状态、耗时、覆盖项与当前 source commit，不保存重型原始日志。
- AC-3: task verify 在验证范围存在未提交源码、spec 未进入 Git HEAD、任务 frozen 或任一 gate 失败时返回失败，且不能生成可用于 close 的 passed evidence。
- AC-4: close 在任何写入前拒绝缺失、格式错误、失败、覆盖不全、source commit 过期或验证范围已变化的 evidence；成功 close 保留 task evidence，不用结构检查结果覆盖它。
- AC-5: 全局 `verify`、freeze/resume、历史 compressed evidence 与 frozen spec 行为保持兼容，关闭仍具备失败回滚和前后 Harness 完整性检查。
- AC-6: spec 模板、verify 工作流、生命周期与 verification policy 明确记录新的先提交 spec、提交实现、task verify、close 顺序。

# Risks

- Windows 与 POSIX 可执行文件解析不同；gate runner 必须解析 `{python}` 与 PATH 命令而不启用 shell。
- evidence 在 verify 后、close 前尚未提交；关闭校验不能把自身 evidence 输出误判为未提交源码。
- 全仓库可能存在无关用户改动；源码清洁检查必须限定配置范围，不能要求整个工作树绝对干净。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5
- harness-integrity => AC-1, AC-4, AC-5, AC-6
