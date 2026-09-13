---
id: archive-20260906-public-reading
level: L2
summary: 完成视觉方案第三阶段的公开索引、详情与统一阅读体验
load_when:
  - task:20260906-public-reading
author: Gavin
task_id: 20260906-public-reading
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-3.md
documentation_reason: 同步公开页面布局、目录与阅读合同以及阶段验收记录。
evidence_sha256: f68ba29281ca57bedbc840eb2e1f2b05838e3cb0b3c4b7779e56a968a317d284
state_history:
---

# 20260906-public-reading

Deterministic compressed record. The original active spec remains in Git history.

## Goal

将文章、项目、读书、归档、关于、搜索与错误页迁入已确认的双主题工程视觉，保持真实 URL、发布快照、SEO 和现有业务边界。

## Acceptance criteria

- AC-1: 文章列表、项目列表、读书列表、归档、关于、搜索与错误页采用紧凑共同尺度；元信息、真实资料和真实筛选链接可用，空项目/读书仍完整，无伪造事实或封面。
- AC-2: 长短文章、项目与书籍详情采用最大 740px 正文轴、43/34px 标题、17px 正文；日期在元信息行；长文只有一套主要目录，手机目录先于正文；代码复制、表格局部横滚、已有内容图、来源及相关链接可用。
- AC-3: 隔离发布数据验证列表到详情、搜索到阅读、目录、引用、关联及公开快照；canonical、结构化信息及既有 SEO、404 与服务故障分类保持正确。
- AC-4: 双主题、320–1440px、480px 短视口、长标题/代码/表格/多条目、键盘与减少动态效果通过检查；加载、空数据、404 与服务故障分别验证，生产无障碍和性能门槛不降低。
- AC-5: 范围、差异、执行命令、真实证据和恢复边界写入阶段记录，Harness 影响计划与模块合同同步并确定性关闭。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-public-reading.json](../../verification/evidence/20260906-public-reading.json)

SHA-256: `f68ba29281ca57bedbc840eb2e1f2b05838e3cb0b3c4b7779e56a968a317d284`

Closed at 2026-09-05T18:58:43.668243+00:00.
