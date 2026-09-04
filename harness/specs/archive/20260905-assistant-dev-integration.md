---
id: archive-20260905-assistant-dev-integration
level: L2
summary: 将公开问答纳入可重复、仅本机且默认安全的项目开发启动流程
load_when:
  - task:20260905-assistant-dev-integration
author: Codex
task_id: 20260905-assistant-dev-integration
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 本任务新增开发者实际使用的根命令、数据来源、离线 provider 边界和安全默认值，必须在项目与两个应用边界文档中长期说明。
evidence_sha256: 478a2810353dfd28ae9843684579e3d99b859dbad47315c302a4cc362a921b19
state_history:
---

# 20260905-assistant-dev-integration

Deterministic compressed record. The original active spec remains in Git history.

## Goal

提供根级 `npm run dev:assistant`：使用现有 `apps/api/.env` 所指向的 development 内容 SQLite，自动装配离线确定性 Chat／Embedding、临时 assistant runtime 与向量索引，并在回环地址启动 FastAPI 和 Nuxt。相关公开内容可通过现有悬浮气泡得到带本站来源引用的确定性回答；命令退出时回收它创建的子进程和临时状态。

## Acceptance criteria

- AC-1: 从仓库根执行 `npm run dev:assistant` 时，命令复用 `apps/api/.env` 的 development 内容库，在仅回环监听的 FastAPI／Nuxt 中开启悬浮入口；启动期基于当前已发布文章、项目、书摘与公开 Profile 重建临时索引，相关问题产生非空中文答案、至少一个合法本站引用和可导航来源，且不要求浏览器注入测试 header。
- AC-2: 开发入口仅接受 `GAVIN_ENVIRONMENT=development`，强制使用明确标识的离线 test provider、每次运行独立的临时 runtime／内存 Qdrant 和运行期随机控制 secret，不读取真实助手/provider 凭据、不访问非回环网络；production/test、非回环 origin、缺失 API 虚拟环境或端口冲突均在启动前失败关闭。普通 `npm run dev:web`、API 默认启动和生产三开关仍保持关闭。
- AC-3: 根 runner 监督自己创建的迁移、API 与 Web 进程，任一子进程异常会使整体失败；SIGINT／SIGTERM 和正常退出都会有界终止子进程并删除本次临时目录，不删除或重建现有内容数据库和媒体。开发 bootstrap 只写既有助手索引账本／generation 指针，并在 API 接受请求前完成 rebuild、receipt 与 runtime enable。
- AC-4: 项目、API 与 Web 长期文档给出唯一开发命令、监听地址、前置条件、真实数据与离线回答器的事实边界、退出语义，并继续标明 production No-Go 与普通启动默认关闭。

## Result

Verified and closed by the harness close command.

## Evidence

[20260905-assistant-dev-integration.json](../../verification/evidence/20260905-assistant-dev-integration.json)

SHA-256: `478a2810353dfd28ae9843684579e3d99b859dbad47315c302a4cc362a921b19`

Closed at 2026-09-04T21:48:25.425007+00:00.
