---
id: spec-20260809-editor-save-safety
level: L1
summary: 为文章、项目、书摘与孵化草稿建立一致的离页保存安全边界
load_when:
  - task:20260809-editor-save-safety
author: Codex
task_id: 20260809-editor-save-safety
status: active
---

# 20260809-editor-save-safety

## Context

`AutosaveQueue.dispose()` 当前只清除 debounce timer。用户在输入后的 0–899ms 内预览、站内导航、浏览器后退或卸载编辑组件时，最新 dirty snapshot 可能从未进入保存请求；现有测试只覆盖等待自动保存后再离页，无法阻止 AUD-01 回归。

## Goal

为文章、项目、书摘和孵化草稿建立同一保存协调语义：任何可控的预览、发布或站内离页动作都必须先等待最新 snapshot 保存成功；保存失败或冲突时保留本地内容并阻止动作；浏览器无法等待异步保存的刷新或关闭路径显示 dirty 提醒。

## Non-goals

- 不改变数据库 schema、API payload 或乐观锁协议。
- 不为项目和书摘建立发布修订；该边界属于 `20260809-publishing-snapshots`。
- 不声称浏览器刷新或关闭时能够可靠完成异步保存。
- 不重新设计编辑器视觉样式或冲突合并 UI。

## Acceptance criteria

- `AutosaveQueue` 可观察 pending、saving、error、conflict 与 clean 状态；`dispose()` 不再静默丢弃 dirty snapshot。
- 文章、项目、书摘和孵化草稿的预览、发布及站内路由离开在动作前调用同一 single-flight `flush()` 屏障。
- 输入后 0ms、300ms、899ms 发起可控动作时，动作只在最新 snapshot 保存成功后继续。
- 保存返回 500、超时或 409 时动作被阻止，本地 snapshot 保留且可重试；冲突状态不被误报为已保存。
- 存在 dirty 或 saving snapshot 时注册 `beforeunload` 提醒，恢复 clean 后移除；组件卸载不再清除未保存 snapshot 后宣称成功。
- 参数化/共享契约测试覆盖四类编辑器使用的协调语义，并至少有核心 E2E 覆盖 debounce 窗口内的预览与站内离页。

## Risks

- 路由守卫递归触发或多编辑器同时注册可能造成导航死锁。
- flush 与自动保存并发时若不复用同一 Promise，可能重复写入或发布旧版本。
- 浏览器原生 `beforeunload` 文案不可控，测试只能断言阻止语义与监听生命周期。
- 孵化草稿的发布/重生成动作较多，遗漏任一离页入口会形成局部语义漂移。

## Verification plan

- Vitest：扩展 `AutosaveQueue` 单测，覆盖 debounce 内 flush、失败保留、并发 single-flight、dirty 生命周期与 dispose。
- Vitest：对文章、项目、书摘和孵化草稿的保存屏障接入做参数化静态/组件契约测试。
- Playwright：在隔离 API/数据库中覆盖输入后立即预览和站内导航，断言返回后最新内容仍存在；覆盖失败时不离页。
- 运行 Web typecheck、单测、构建及相关 E2E。
- 从 `harness/` 运行 `python -m tools.harness verify 20260809-editor-save-safety`，生成紧凑 evidence 后关闭 spec。
