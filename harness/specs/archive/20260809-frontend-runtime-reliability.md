---
id: archive-20260809-frontend-runtime-reliability
level: L2
summary: 消除 SSR 共享状态漂移并统一轮询、媒体逐项反馈与 Profile 初态
load_when:
  - task:20260809-frontend-runtime-reliability
author: Codex
task_id: 20260809-frontend-runtime-reliability
status: compressed
restoration_source: "0f0a2ba1546767693b9a1ba97629d047f3fe70ce:harness/specs/active/20260809-frontend-runtime-reliability.md"
restored_at: 2026-08-11
---

# 20260809-frontend-runtime-reliability

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让生产 SSR 与共享数据处理无警告，使孵化轮询具备单飞、可见性、终态、退避和卸载取消边界；让媒体上传准确展示每个文件的成功或失败并及时刷新成功资产；允许合法的零技能 Profile 修改其他字段。

## Acceptance criteria

1. 公开 Profile 读取集中到唯一 composable；共享 AsyncData key 的 handler 与关键 options 完全一致，首页、默认布局及其他消费者不再自行定义同 key handler。
2. 依赖 system color mode 的公开与后台主题图标使用 SSR 稳定 DOM/CSS 或显式 unknown 占位；生产首页及主题切换不产生 hydration mismatch、Vue error 或 `NUXT_E3004`。
3. E2E 监听 console/pageerror，并把 hydration mismatch、Vue error、`NUXT_E3004` 与未处理错误作为失败，而非只把日志留在 WebServer 输出。
4. 所有需要持续刷新的孵化详情页使用 `useIncubatorPolling`，不保留页面私有 async `setInterval`。
5. 统一轮询在一次请求完成后才用 `setTimeout` 安排下一次，间隔下限 2000ms；同一实例最多一个 in-flight 请求，hidden 暂停、visible 恢复，终态停止，卸载后中止/忽略在途结果；失败指数退避并暴露重试状态与最后成功时间供页面展示。
6. 多文件媒体上传逐文件继续执行，展示每个文件的 pending/success/error 结果；任一成功后刷新资产列表，后续失败不抹掉成功事实，失败项可明确重试且不会自动重传成功项。
7. API 与 Web 允许 Profile `skills=[]`，仍拒绝空白技能、超过 6 项或单项超长；fresh database 首次只修改简介、头像或其他非技能字段可成功保存。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-frontend-runtime-reliability.json](../../verification/evidence/20260809-frontend-runtime-reliability.json)

Closed at 2026-08-10T13:57:58.196207+00:00.
