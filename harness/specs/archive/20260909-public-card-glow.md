---
id: archive-20260909-public-card-glow
level: L2
summary: 补齐公开卡片随鼠标移动的局部光晕
load_when:
  - task:20260909-public-card-glow
task_id: 20260909-public-card-glow
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/product/interaction-references.md
documentation_reason: 记录用户确认的鼠标跟随光晕参数及首页图谱保留边界。
evidence_sha256: 9761355f2b08c040401b3a84481e6561c4719dad166b1669c905b918098e3b98
state_history:
---

# 20260909-public-card-glow

Deterministic compressed record. The original active spec remains in Git history.

## Goal

公开卡片采用首页同款 160px、12% 主题色径向光晕，随鼠标直接移动，进入离开沿用 180ms 淡入淡出。原卡片位置、图谱联动保持稳定。

## Acceptance criteria

- AC-1: 普通公开卡片和嵌套卡片的最内层光晕随两个不同鼠标位置移动，沿用页面主题色，裁切在圆角内部；首页分支保留原光晕且不重复叠加。
- AC-2: 离开、键盘输入、减少动态效果、触屏和进入写作台后无残留跟随光晕；清理待执行帧与事件监听，原反馈和导航可用。

## Result

Verified and closed by the harness close command.

## Evidence

[20260909-public-card-glow.json](../../verification/evidence/20260909-public-card-glow.json)

SHA-256: `9761355f2b08c040401b3a84481e6561c4719dad166b1669c905b918098e3b98`

Closed at 2026-09-08T16:24:22.597781+00:00.
