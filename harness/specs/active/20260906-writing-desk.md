---
id: spec-20260906-writing-desk
level: L1
summary: 完成视觉提案第四阶段的后台写作闭环
load_when:
  - task:20260906-writing-desk
author: Gavin
task_id: 20260906-writing-desk
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-4.md
documentation_reason: 记录正文设置分区、字段定位、保存发布边界和十二个页面状态的实施验收。
state_history:
---

# Context

提案阶段 1–3 已归档。第四阶段覆盖登录、三类列表/新建/编辑、文章工作副本预览与版本历史，共十二个页面状态。现有保存队列与发布快照已实现；原型操作为模拟，不能替代真实业务验收。基线 f00a826；保留用户 UI_AUDIT_REPORT.md 修改。

# Goal

将写作台设计落实到真实页面，正文先行、设置分区、稳定操作，完成隔离数据上的编辑到公开阅读路径。

# Non-goals

不改 API、数据模型、部署或助手开关；资源运营五页留在阶段五。不新增接口不支持的全库搜索、项目版本历史或伪造快照。

# Acceptance criteria

- AC-1: 登录及三类列表、新建和编辑采用原字体双主题的紧凑写作台，主要操作稳定，正文与设置分区，手机正文/设置及 Markdown/预览切换可用，320–1440px 和短视口无横滚，键盘和错误字段可达。
- AC-2: 隔离数据实际验证三类创建、自动保存、重试、预览和发布更新；失败和冲突阻止旧内容发布和站内离页，dirty 时刷新有提醒，字段校验能打开隐藏设置并聚焦，工作副本不泄漏公开页面。
- AC-3: 文章工作副本预览沿用阅读尺度且提示发布边界；真实版本快照、比较和确认回滚可操作，加载或操作失败可见，不伪造历史。
- AC-4: 十二页面范围、设计业务差异、验证证据和恢复方式记录完整，影响计划与合同同步并通过确定性关闭。

# Risks

手机隐藏字段可能失去焦点；双栏迁移可能导致媒体重复挂载；异步保存失败可能阻塞且不解释；发布和回滚须保留版本一致性。用单实例面板、明确反馈及隔离真实请求验收。

# Verification plan

## Verification cases

- AC-1 => M02-DESK-LAYOUT-01, M02-UNIT-ARTICLE-LOOP-01
- AC-2 => M02-DESK-SAFETY-01, M02-UNIT-AUTOSAVE-01, M02-UNIT-ARTICLE-LOOP-01
- AC-3 => M02-DESK-REVISIONS-01, M02-P1-01
- AC-4 => M08-DOCS-01

## Gates

- e2e => AC-1, AC-2, AC-3
- web-quality => AC-2
- api-tests => AC-3
- harness-integrity => AC-4
