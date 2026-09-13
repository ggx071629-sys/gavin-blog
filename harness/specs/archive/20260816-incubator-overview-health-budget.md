---
id: archive-20260816-incubator-overview-health-budget
level: L2
summary: 孵化概览把检索探活改成有预算的观察，sidecar 宕机时首屏不再被同步活探堵住
load_when:
  - task:20260816-incubator-overview-health-budget
author: Gavin
task_id: 20260816-incubator-overview-health-budget
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 概览/健康检查的请求路径预算、进程内缓存和壳层共用 snapshot 是 API 与 Web 边界的一部分，不能只留在实现注释里。
state_history:
---

# 20260816-incubator-overview-health-budget

Deterministic compressed record. The original active spec remains in Git history.

## Goal

检索健康是有预算、可缓存的能力观察，不是概览首屏屏障。sidecar 拒绝连接或挂起时，overview 与 retrieval/health 仍返回既有 `unavailable` 契约，但必须在 1 秒内返回。壳层与概览页只取一次 snapshot。进程内重复探活不得再哈希模型文件或新建 InferenceSession。检索、预览、索引的长超时保持不变。

## Acceptance criteria

- AC-1: `retrieval_service_url` 指向拒绝连接或接受后不响应的 loopback 端口时，`GET /api/v1/admin/incubator/overview` 与 `GET /api/v1/admin/incubator/retrieval/health` 在 1 秒内返回 200；`retrieval_model` 仍为 `blocked` + `retrieval_unavailable`；health `state` 仍为 `unavailable`。
- AC-2: 同一 `RetrievalClient` 上并发或 TTL（2–5 秒）内的重复 `health()` 只向 sidecar 发出一次 HTTP 探活；成功与 `RETRIEVAL_UNAVAILABLE` 都缓存。`retrieve` / `preview` 不使用该短超时。
- AC-3: `IncubatorShell` 与 `/admin/incubator` 共用 `useAsyncData` key `incubator-overview`。壳层仍不调用 `useApiFailure`，概览页仍调用。
- AC-4: 模型文件指纹未变时，`model_health` 不得再次 `validate()`（全量 SHA256）或调用 `_session_executable`（新建 ORT session）。指纹变化后必须重新校验。
- AC-5: `apps/api/README.md` 写明 overview/health 的检索探活有请求路径预算与进程内短缓存；`apps/web/README.md` 写明壳层与概览共用一次 overview，检索宕机不得拖住首屏。

## Result

Verified and closed by the harness close command.

## Evidence

[20260816-incubator-overview-health-budget.json](../../verification/evidence/20260816-incubator-overview-health-budget.json)

Closed at 2026-08-16T12:53:49.144834+00:00.
