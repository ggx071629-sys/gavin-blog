---
id: spec-20260910-studio-suite-compat
level: L1
summary: 整套浏览器联跑的真实数据与现行页面定位对齐
load_when:
  - task:20260910-studio-suite-compat
task_id: 20260910-studio-suite-compat
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录整套回归的共享数据边界与旧定位修复，保持实际产品和验收边界一致。
state_history:
---
# Context
U6-03 全套 E2E 联跑发现既有修订/卡片数量假设，以及已交付公开页面上的旧标签位置、标题和响应式定位。单独精确验收不能代替联跑的共享数据检查。
# Goal
让浏览器回归在独立执行和整套联跑中都验证真实业务状态及当前交付页面。
# Non-goals
不改变产品行为、数据库清理策略、发布确认、权限、质量阈值或用户既有修改。
# Acceptance criteria
- AC-1: 修订增量、公开数据呈现、筛选 URL、主题对比、响应式与共享页面边界在当前实现上通过真实浏览器回归；不靠移除断言或静默跳过错误通过。
# Risks
初始用户修改单独保留；测试计数应绑定真实前置或显式夹具，不把整库固定数量当作事实。只等待主题相关有限过渡，不等待滚动时间线永久完成。
# Verification plan
## Verification cases
- AC-1 => M07-STUDIO-SUITE-01
## Gates
- e2e => AC-1
- harness-integrity => AC-1
