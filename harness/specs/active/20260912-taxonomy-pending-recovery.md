---
id: spec-20260912-taxonomy-pending-recovery
level: L1
summary: 栏目标签请求悬挂时退出无限保存并保留输入和结果核对入口
load_when:
  - task:20260912-taxonomy-pending-recovery
author: Codex
task_id: 20260912-taxonomy-pending-recovery
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录栏目标签操作的局部等待上限、超时不等于服务端未写入、手动核对与禁止自动重放的边界。
state_history:
---
# Context
O001 曾出现标签 POST 长期 pending，刷新后重复 slug 返回 409。原始传输追踪缺失，无法确认当时哪一层停住；Uvicorn 访问日志在 http.response.start 才输出，不能由缺日志推断请求未到 API。TaxonomyManager 当前无限 await apiFetch，保存和删除没有等待上限；请求不完成时 finally 不执行，界面长期处于提交状态。用户要求解决该观察暴露的无法恢复问题。
# Goal
为共享栏目/标签组件的操作提供 15 秒局部等待上限，退出无限 pending、保留输入并如实提示写入结果未知；允许有界只读核对最新列表，禁止自动重放 mutation。
# Non-goals
不宣称还原原请求 #4950 的传输根因；不增加全站超时/重试、永久遥测、API 或数据库改动；不以取消客户端等待冒充服务器回滚。
# Acceptance criteria
- AC-1: 栏目与标签保存请求持续悬挂时，15 秒后退出保存中，保留名称/slug/说明，提示结果未确认并提供核对最新列表入口；不自动再次 POST/PATCH。
- AC-2: 请求已在服务器成功但响应丢失时不得假报失败或清空输入；核对仅发 GET、更新真实列表并保留输入。核对或删除本身悬挂也必须有界结束；离页中止本组件等待，不接受迟到结果覆盖状态。
- AC-3: 正常新增、编辑、删除、持久化刷新及重复 slug 409 继续有效；文档明确局部恢复与未知写入边界。
# Risks
15 秒是本组件的交互等待预算，不是对服务器提交耗时的保证。客户端中止后服务器可能仍提交，因此未知结果必须先核对，不能自动重试写操作。共享组件同时影响栏目和标签，回归需覆盖两者及删除/核对路径。
# Verification plan
## Verification cases
- AC-1 => M03-TAXONOMY-PENDING-01
- AC-2 => M03-TAXONOMY-PENDING-02
- AC-3 => M03-OPS-TAXONOMY-01, M03-TAXONOMY-CONFLICT-01, M08-DOCS-01
## Gates
- e2e => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
