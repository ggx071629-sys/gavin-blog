---
id: archive-20260811-media-inline-lifecycle
level: L2
summary: 建立编辑器内媒体导入、去重、软删除恢复与可扩展管理闭环
load_when:
  - task:20260811-media-inline-lifecycle
author: Codex
task_id: 20260811-media-inline-lifecycle
status: compressed
state_history:
---

# 20260811-media-inline-lifecycle

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让 Markdown 编辑器成为主要图片导入入口，并建立不破坏历史公开链接的媒体软删除、恢复、精确去重和有界管理能力。

## Acceptance criteria

- 文章、项目和读书 Markdown 编辑区支持粘贴、拖放和文件选择；上传时在原位置显示占位，成功后替换，失败可局部重试或移除。
- 上传和插入不要求离开编辑器；已有资产按需打开选择，不默认加载完整媒体列表。
- 草稿允许缺失图片 Alt，发布前阻止缺失 Alt 的 Markdown 并定位错误。
- 本地上传按内容摘要精确去重，重复内容复用现有未移除资产 URL。
- 媒体列表支持文件名与 Alt 搜索、本地或外链来源筛选、活跃或已移除状态筛选、最新优先和有界分页。
- 单项与当前页批量软删除可部分成功并可恢复；移除资产不再出现在默认列表和选择器，但原公开 URL 继续可访问。
- 外链仅登记 URL，并明确其可能失效。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-media-inline-lifecycle.json](../../verification/evidence/20260811-media-inline-lifecycle.json)

Closed at 2026-08-12T02:23:20.342951+00:00.
