---
id: spec-20260910-studio-suite-management
level: L1
summary: 后台联跑的保存发布、名片夹具与主题等待修复
load_when:
  - task:20260910-studio-suite-management
task_id: 20260910-studio-suite-management
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 明确联跑数据前置、去重媒体选择、真实发布落点和有界主题等待。
state_history:
---
# Context
本项承接 U6-03 整套浏览器联跑发现的后台测试修复；公开阅读和导航修复仍留在 studio-suite-compat 独立验收。分组保留原有冷启动和门禁预算。
# Goal
在共享夹具联跑与独立执行中准确验证后台真实数据，不将旧保存提示、后台同尾路径或新 Alt 当作新事实。
# Non-goals
不修改产品、SQL、媒体去重、认证、发布逻辑和质量阈值。
# Acceptance criteria
- AC-1: 关于工作副本保存和明确发布、修订增量、名片编辑与上传去重、运营主题与无障碍检查真实通过。
# Risks
禁止固定整库初始计数；公开模板不呈现的引言由公开 API 核对。名片用独立认证请求设置明确前置，页面访客登录仍单独验收。
# Verification plan
## Verification cases
- AC-1 => M07-STUDIO-SUITE-MANAGEMENT-01
## Gates
- e2e => AC-1
- harness-integrity => AC-1
