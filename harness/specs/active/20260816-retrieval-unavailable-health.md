---
id: spec-20260816-retrieval-unavailable-health
level: L1
summary: 检索服务不可用时概览与健康检查返回能力态，不再把整台孵化打成 500
load_when:
  - task:20260816-retrieval-unavailable-health
author: Gavin
task_id: 20260816-retrieval-unavailable-health
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: API 文档把 health 写成稳定态清单，Web 边界写明检索失败不得整页打死详情，两者都需要与新能力态对齐。
state_history:
---

# Context

2026-08-16 审计 AUD26-016/018/019/020/028：`.env.example` 把 API 配成 HTTP 客户端。Retrieval Service 未监听时，`health()` 抛出未捕获的 `RetrievalError`，`overview` 与 `retrieval/health` 变成 500。`IncubatorShell` 的 `useApiFailure` 再把所有孵化页打成错误页，尽管 `GET /sources` 仍 200。预览把该错误映射成 `LOCAL_MODEL_NOT_READY`。Worker 只捕获 `IncubatorError`，检索失败被记成 `INTERNAL_ERROR`。测试夹具走 in-process，看不见这条路径。

# Goal

检索服务不可用是与 Worker 离线同类的能力健康，不是未捕获 500。概览、健康检查、待处理池在第三进程未启动时仍可打开；预览与 Worker 使用稳定码 `RETRIEVAL_UNAVAILABLE`。

# Non-goals

- 不改检索算法、索引或 Zvec 决策。
- 不在 API 进程内回退加载生产 ONNX。
- 不修 AUD26-017 及之后批次。
- 不改两条 GitHub frozen spec。
- 不把 overview 的真实 5xx（例如数据库失败）伪装成空成功。

# Acceptance criteria

- AC-1: `retrieval_service_url` 指向拒绝连接的 loopback 端口时，`GET /api/v1/admin/incubator/overview` 与 `GET /api/v1/admin/incubator/retrieval/health` 返回 200；概览 `health` 中 `retrieval_model` 为 `blocked` 且 code 为 `retrieval_unavailable`；health 的 `state` 为 `unavailable`。
- AC-2: 同一配置下 `POST /api/v1/admin/incubator/retrieval/preview`（`full` 与 `fts_only`）返回 503 且 `error.code` 为 `RETRIEVAL_UNAVAILABLE`，不得写成 `LOCAL_MODEL_NOT_READY`。
- AC-3: Worker 处理审计计划取回时，`RetrievalError` 记入计划项/任务的 `RETRIEVAL_UNAVAILABLE`，不得记成 `INTERNAL_ERROR`。
- AC-4: `IncubatorShell` 在 overview 失败时仍渲染子页导航，不调用 `useApiFailure`，也不把失败吞成 `.catch(() => null)` 的 0 角标；`/admin/incubator` 概览页本身仍用 `useApiFailure`。资料详情把 health `unavailable` 显示成检索服务不可用，而不是模型未就绪。
- AC-5: `apps/api/README.md` 将 `unavailable` 列入 retrieval/health 稳定态；`apps/web/README.md` 写明检索服务不可用是能力态，工作台壳不得因此整页打死三池。

# Risks

壳层不再对 overview 抛整页错误后，操作者可能只看到计数缺失。必须有可见提示，且概览页本身的 5xx 仍走失败分类。

# Verification plan

- api-lint => AC-1, AC-2, AC-3
- api-tests => AC-1, AC-2, AC-3
- web-quality => AC-4, AC-5
