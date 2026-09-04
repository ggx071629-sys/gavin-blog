---
id: spec-20260905-assistant-dev-integration
level: L1
summary: 将公开问答纳入可重复、仅本机且默认安全的项目开发启动流程
load_when:
  - task:20260905-assistant-dev-integration
author: Codex
task_id: 20260905-assistant-dev-integration
status: active
verification_profile: release
verification_escalation: 根启动入口属于 release-control，且本任务同时改变 API 开发装配、Web 代理身份与用户可见问答闭环，关闭前需要完整 release 包门禁并保留对应叶子 gate 证据。
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 本任务新增开发者实际使用的根命令、数据来源、离线 provider 边界和安全默认值，必须在项目与两个应用边界文档中长期说明。
state_history:
---

# Context

公开问答的索引、LangGraph 内核、悬浮气泡和运营页已在仓库中，但普通本地启动保持三个开关默认关闭，仓库没有一条受支持的命令把这些部件装配成可人工审计的开发环境。此前 `.run` 下的手工审计适配器能显示回答，却不受版本控制、使用隔离 seed 数据并要求额外边缘代理，因此不能证明开发者从真实项目内容库启动后可使用该功能。

生产资格任务仍冻结且部署 No-Go；本任务只解决本机功能开发入口，不选择供应商、服务器或公网拓扑。

# Goal

提供根级 `npm run dev:assistant`：使用现有 `apps/api/.env` 所指向的 development 内容 SQLite，自动装配离线确定性 Chat／Embedding、临时 assistant runtime 与向量索引，并在回环地址启动 FastAPI 和 Nuxt。相关公开内容可通过现有悬浮气泡得到带本站来源引用的确定性回答；命令退出时回收它创建的子进程和临时状态。

# Non-goals

- 不部署、不推送、不合并 PR，不恢复生产资格 spec，也不把任何公开问答开关改成普通启动的默认值。
- 不调用真实 Chat、Embedding、LangSmith 或其它公网服务，不复用 `.env` 中的历史 LLM 密钥，不宣称离线摘录器代表真实模型回答质量。
- 不更改公开问答 HTTP／SSE、费用、限流、会话、删除、引用闭包或运营 gate 合同。
- 不引入 Docker、Qdrant server、第二 API owner、后台常驻服务或生产基础设施文件。
- 不把 runtime、向量、日志、问答正文或开发数据库提交 Git。

# Acceptance criteria

- AC-1: 从仓库根执行 `npm run dev:assistant` 时，命令复用 `apps/api/.env` 的 development 内容库，在仅回环监听的 FastAPI／Nuxt 中开启悬浮入口；启动期基于当前已发布文章、项目、书摘与公开 Profile 重建临时索引，相关问题产生非空中文答案、至少一个合法本站引用和可导航来源，且不要求浏览器注入测试 header。
- AC-2: 开发入口仅接受 `GAVIN_ENVIRONMENT=development`，强制使用明确标识的离线 test provider、每次运行独立的临时 runtime／内存 Qdrant 和运行期随机控制 secret，不读取真实助手/provider 凭据、不访问非回环网络；production/test、非回环 origin、缺失 API 虚拟环境或端口冲突均在启动前失败关闭。普通 `npm run dev:web`、API 默认启动和生产三开关仍保持关闭。
- AC-3: 根 runner 监督自己创建的迁移、API 与 Web 进程，任一子进程异常会使整体失败；SIGINT／SIGTERM 和正常退出都会有界终止子进程并删除本次临时目录，不删除或重建现有内容数据库和媒体。开发 bootstrap 只写既有助手索引账本／generation 指针，并在 API 接受请求前完成 rebuild、receipt 与 runtime enable。
- AC-4: 项目、API 与 Web 长期文档给出唯一开发命令、监听地址、前置条件、真实数据与离线回答器的事实边界、退出语义，并继续标明 production No-Go 与普通启动默认关闭。

# Risks

- 开发 convenience seam 若缺少环境与回环双重约束，可能绕过生产可信代理或让 test provider 被误作生产能力。
- 在真实开发内容库上重建 generation 会写助手派生账本；必须保持内容正文、发布修订和媒体只读，并说明向量/runtime 为可删除临时状态。
- 多进程监督在 Windows 与 POSIX 的终止语义不同；runner 必须复用已有受控进程树模式并以自动化覆盖配置与失败边界。
- 确定性哈希向量不代表语义检索质量；开发回答器只能摘录已检索证据并显式标为离线模式。

# Verification plan

## Verification cases

- AC-1 => M09-P1-02, M09-P1-01
- AC-2 => M09-P0-03, M09-P0-01, M09-P0-02
- AC-3 => M09-P1-02
- AC-4 => M09-P1-02

## Gates

- api-tests => AC-1, AC-2, AC-3
- web-quality => AC-1, AC-2
- e2e => AC-1, AC-2
- harness-tests => AC-1, AC-2, AC-3, AC-4
- harness-integrity => AC-4
- release => AC-1, AC-2, AC-3, AC-4
