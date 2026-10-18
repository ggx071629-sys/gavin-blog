---
id: archive-20260809-editor-save-safety
level: L2
summary: 为文章、项目、书摘与孵化草稿建立一致的离页保存安全边界
load_when:
  - task:20260809-editor-save-safety
author: Codex
task_id: 20260809-editor-save-safety
status: compressed
---

# 20260809-editor-save-safety

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为文章、项目、书摘和孵化草稿建立同一保存协调语义：任何可控的预览、发布或站内离页动作都必须先等待最新 snapshot 保存成功；保存失败或冲突时保留本地内容并阻止动作；浏览器无法等待异步保存的刷新或关闭路径显示 dirty 提醒。

## Acceptance criteria

- `AutosaveQueue` 可观察 pending、saving、error、conflict 与 clean 状态；`dispose()` 不再静默丢弃 dirty snapshot。
- 文章、项目、书摘和孵化草稿的预览、发布及站内路由离开在动作前调用同一 single-flight `flush()` 屏障。
- 输入后 0ms、300ms、899ms 发起可控动作时，动作只在最新 snapshot 保存成功后继续。
- 保存返回 500、超时或 409 时动作被阻止，本地 snapshot 保留且可重试；冲突状态不被误报为已保存。
- 存在 dirty 或 saving snapshot 时注册 `beforeunload` 提醒，恢复 clean 后移除；组件卸载不再清除未保存 snapshot 后宣称成功。
- 参数化/共享契约测试覆盖四类编辑器使用的协调语义，并至少有核心 E2E 覆盖 debounce 窗口内的预览与站内离页。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-editor-save-safety.json](../../verification/evidence/20260809-editor-save-safety.json)

Closed at 2026-08-09T14:50:12.141600+00:00.
