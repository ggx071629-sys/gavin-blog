---
id: spec-20260910-studio-suite-state
level: L1
summary: 收敛全套联跑的媒体空态、旧定位和动画时序前置
load_when:
  - task:20260910-studio-suite-state
task_id: 20260910-studio-suite-state
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 说明共享媒体数据、显式空态与稳定几何的联跑边界。
state_history:
---
# Context
U6-03 后半段生产联跑暴露了固定媒体总数、多个 status 的无范围定位、旧箭头文本和过早读取动画中间帧。
# Goal
让现有九个场景在联跑与独立执行下具备明确前置和相同验收语义。
# Non-goals
不修改产品行为、媒体去重、动画设计、数据库或任何质量阈值。
# Acceptance criteria
- AC-1: 媒体分页/失败重试、迁移恢复、助手陈旧状态、显式空态、卡片无位移和搜索最终布局及现行首页/列表结构、761px 后台导航断点通过真实浏览器验证。
# Risks
不能清空全套测试共享数据以制造通过；空态用明确响应夹具，分页按命名样例过滤，几何仍精确比较而非放宽误差。
# Verification plan
## Verification cases
- AC-1 => M07-STUDIO-SUITE-STATE-01
## Gates
- e2e => AC-1
- harness-integrity => AC-1
