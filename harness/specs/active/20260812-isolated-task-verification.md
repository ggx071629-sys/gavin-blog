---
id: spec-20260812-isolated-task-verification
level: L1
summary: 在固定 HEAD 的临时 Git worktree 中运行任务产品门禁并确定性清理
load_when:
  - task:20260812-isolated-task-verification
author: Codex
task_id: 20260812-isolated-task-verification
status: active
verification_profile: focused
state_history:
---

# Context

task evidence 已绑定 HEAD、source tree、spec、验证合同和 gate 配置，但 gate 仍在共享工作目录运行。本地忽略文件、构建缓存、测试产物或并行编辑可能影响结果，也可能让 gate 在验证过程中污染主工作树。项目已有可复用的根 `node_modules` 和 API `.venv`，Windows 环境需要安全处理目录链接和 Git worktree 清理。

# Goal

让 task verify 默认在当前 HEAD 的 detached 临时 Git worktree 中运行全部产品 gate，受控复用已安装依赖，并在成功、失败、超时或异常后确定性清理；evidence 明确记录隔离执行上下文和清理结果。

# Non-goals

- 不修改博客应用、公开信息、文章内容、API 或数据库。
- 不修改、恢复、验证或关闭两个 frozen spec。
- 不下载、安装或升级依赖，不复制整个 `node_modules` 或 `.venv`。
- 不在本阶段接入远端 CI 服务或签名 evidence。
- 不允许隔离失败时静默退回共享工作目录。

# Acceptance criteria

- AC-1: task verify 在执行产品 gate 前以当前 HEAD 创建 detached 临时 Git worktree；gate cwd、项目源码解析和 Git 上下文均来自该 worktree。
- AC-2: 隔离配置只允许项目内相对路径，已存在的依赖源通过受控目录链接挂载；缺失源、越界路径、目标冲突或链接失败使验证失败。
- AC-3: 成功、gate 失败、超时、初始化失败和执行异常均触发清理：先移除本次依赖链接，再注销 Git worktree，最后删除验证专用临时根；不得删除依赖源或其他 worktree。
- AC-4: evidence 记录 execution mode、verified commit、临时环境是否清理；只有 gate 通过且清理成功时 task evidence 才能是 passed 并派生 verified。
- AC-5: 隔离环境建立或清理失败时 task verify 返回失败并保存有限诊断，close 拒绝该 evidence；不提交临时路径中的日志、缓存、截图或测试产物。
- AC-6: 无 task ID 的全局 verify、close/close-all、freeze/resume、profile 和既有 compressed evidence 保持兼容。
- AC-7: verification policy 与 verify workflow 记录隔离默认值、依赖复用边界、失败语义和推荐命令顺序。

# Risks

- Windows 目录 junction 清理若顺序错误可能触及依赖源；必须先删除链接节点再删除临时 worktree。
- Git worktree 注册和磁盘目录清理可能分别失败；诊断必须保留两个阶段结果且不能掩盖 gate 失败。
- 浏览器门禁会在隔离目录生成大量忽略文件，清理必须有明确的临时根边界。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- harness-integrity => AC-1, AC-4, AC-6, AC-7
