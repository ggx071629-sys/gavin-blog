---
id: archive-20260908-public-card-focus
level: L2
summary: 全站公开卡片统一聚焦反馈并排除全部写作台页面
load_when:
  - task:20260908-public-card-focus
task_id: 20260908-public-card-focus
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/product/interaction-references.md
documentation_reason: 记录已授权的公开卡片覆盖范围、输入方式和写作台排除边界。
evidence_sha256: 292ee97abbb6f3c4bec17ded998d5df2d74fff1b06dd3150408d4f5e80cc9d1d
state_history:
---

# 20260908-public-card-focus

Deterministic compressed record. The original active spec remains in Git history.

## Goal

公开卡片采用主题色轮廓与浅色强调层，鼠标进入/离开以 180ms opacity transition 平滑切换；键盘焦点即时反馈，触屏按压即时反馈。不移动阅读位置。图谱保留整条路径选择和联动。

## Acceptance criteria

- AC-1: 首页、文章/项目/书籍列表及详情、关于、搜索、归档、公开错误页和助手卡片具有统一反馈；两种主题下位置不变，嵌套卡片仅强调当前最内层，图谱仍联动。
- AC-2: 鼠标离开复位、键盘聚焦即时反馈、触屏不残留悬停；减少动态效果时反馈即时，原链接与控件可操作。
- AC-3: /admin 及所有子路由（含登录、运营、编辑、预览与版本页）不启用新卡片效果；公开与写作台间客户端跳转正确更新隔离标记。

## Result

Verified and closed by the harness close command.

## Evidence

[20260908-public-card-focus.json](../../verification/evidence/20260908-public-card-focus.json)

SHA-256: `292ee97abbb6f3c4bec17ded998d5df2d74fff1b06dd3150408d4f5e80cc9d1d`

Closed at 2026-09-08T15:10:21.036465+00:00.
