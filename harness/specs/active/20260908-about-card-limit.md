---
id: spec-20260908-about-card-limit
level: L1
summary: 关于页各支持十项并提供十种不同的几何动效图标
load_when:
  - task:20260908-about-card-limit
task_id: 20260908-about-card-limit
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录两个关于页可编辑集合各自的数量上限。
state_history:
---
# Context
用户希望在写作台编辑截图中的能力卡片与最近在做条目，上限十个。现有编辑器已支持增删排序，但前后端各限制六项。
# Goal
能力领域与最近在做分别最多十项，保持现有自动保存、预览和显式发布流程。能力领域前十项使用互不相同的几何动效图标。
# Non-goals
不改变卡片样式、标签上限、必填规则、数据库结构或发布权限。
# Acceptance criteria
- AC-1: 两个区域各显示数量 / 10，允许新增至十项，满额禁止新增，删除后可再次新增。
- AC-2: API 接受各十项并保留顺序，独立拒绝任一区域的第十一项；保存不改变公开内容，发布后公开内容完整包含十项。
- AC-3: 十张能力卡片显示十种不同的 SVG 几何图标；鼠标悬停有短过渡反馈，离开平滑复位，减少动态效果与触屏不触发位移动画。
# Risks
仅修改前端会导致保存失败，必须同步服务端数组校验和 OpenAPI。现有未提交 UI 改动必须保留。
# Verification plan
## Verification cases
- AC-1 => M11-CARD-EDITOR-01
- AC-2 => M11-CARD-LIMIT-01
- AC-3 => M11-CARD-ICONS-01
## Gates
- e2e => AC-1, AC-3
- api-tests => AC-2
- harness-integrity => AC-1, AC-2, AC-3
