---
id: spec-20260816-incubator-overview-health-budget
level: L1
summary: 孵化概览把检索探活改成有预算的观察，sidecar 宕机时首屏不再被同步活探堵住
load_when:
  - task:20260816-incubator-overview-health-budget
author: Gavin
task_id: 20260816-incubator-overview-health-budget
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 概览/健康检查的请求路径预算、进程内缓存和壳层共用 snapshot 是 API 与 Web 边界的一部分，不能只留在实现注释里。
state_history:
---

# Context

开发配置把 API 配成 HTTP 客户端打 `127.0.0.1:8101`。打开任意孵化页都要等 `GET /admin/incubator/overview`，而 overview 同步调用 `retrieval_client.health()`。sidecar 未监听时，本机一次探活约 5.7 秒，超时上限 60 秒。`IncubatorShell` 与概览页用不同 `useAsyncData` key，同一份 snapshot 打两次。sidecar 起来后，`engine.health()` 仍会对模型文件全量 SHA256 并新建 ONNX session。08-16 已把宕机改成 200 + `unavailable`，但首屏仍被这次失败的活探挡住。

# Goal

检索健康是有预算、可缓存的能力观察，不是概览首屏屏障。sidecar 拒绝连接或挂起时，overview 与 retrieval/health 仍返回既有 `unavailable` 契约，但必须在 1 秒内返回。壳层与概览页只取一次 snapshot。进程内重复探活不得再哈希模型文件或新建 InferenceSession。检索、预览、索引的长超时保持不变。

# Non-goals

- 不拆 overview / health 为两个首屏接口，不新增 `unknown` 状态。
- 不改检索算法、索引、Zvec 或 LLM 健康。
- 不在 API 进程回退加载生产 ONNX。
- 不把「启动 sidecar」当成这个缺陷的修复。
- 不改预览/检索/索引的 60 秒工作超时。

# Acceptance criteria

- AC-1: `retrieval_service_url` 指向拒绝连接或接受后不响应的 loopback 端口时，`GET /api/v1/admin/incubator/overview` 与 `GET /api/v1/admin/incubator/retrieval/health` 在 1 秒内返回 200；`retrieval_model` 仍为 `blocked` + `retrieval_unavailable`；health `state` 仍为 `unavailable`。
- AC-2: 同一 `RetrievalClient` 上并发或 TTL（2–5 秒）内的重复 `health()` 只向 sidecar 发出一次 HTTP 探活；成功与 `RETRIEVAL_UNAVAILABLE` 都缓存。`retrieve` / `preview` 不使用该短超时。
- AC-3: `IncubatorShell` 与 `/admin/incubator` 共用 `useAsyncData` key `incubator-overview`。壳层仍不调用 `useApiFailure`，概览页仍调用。
- AC-4: 模型文件指纹未变时，`model_health` 不得再次 `validate()`（全量 SHA256）或调用 `_session_executable`（新建 ORT session）。指纹变化后必须重新校验。
- AC-5: `apps/api/README.md` 写明 overview/health 的检索探活有请求路径预算与进程内短缓存；`apps/web/README.md` 写明壳层与概览共用一次 overview，检索宕机不得拖住首屏。

# Risks

短超时会把「正在加载模型的 sidecar」短暂标成 unavailable；10 秒轮询会纠正，且当时确实不能检索。进程内缓存最多让健康态滞后 5 秒，与现有 10 秒轮询同量级。共用 key 后壳层与概览共享错误；概览页的 `useApiFailure` 仍处理真实 5xx。

# Verification plan

- api-lint => AC-1, AC-2, AC-4
- api-tests => AC-1, AC-2, AC-4
- web-quality => AC-3, AC-5
