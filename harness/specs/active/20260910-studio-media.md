---
id: spec-20260910-studio-media
level: L1
summary: 媒体库类型筛选真实查询与资源操作
load_when:
  - task:20260910-studio-media
task_id: 20260910-studio-media
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U5-06 按计划在前置验收归档后实施。
# Goal
媒体库类型筛选真实查询与资源操作
# Non-goals
仅支持真实上传图片/外链图片；不增加视频文档、反向引用统计或伪造数量，不变更已有 API。
# Acceptance criteria
- AC-1: 媒体使用图片工作区、真实上传/外链类型和服务端搜索分页；未提交筛选不能污染加载更多结果。
- AC-2: 上传、外链、选择/复制、移除/恢复和批量失败反馈保留；共用编辑器与名片选择及双主题响应式可用。
# Risks
筛选与分页必须使用同一已提交条件；共用控件读失败不丢失编辑内容，批量失败不可伪报成功。
# Verification plan
## Verification cases
- AC-1 => M05-STUDIO-MEDIA-01
- AC-2 => M05-STUDIO-MEDIA-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
