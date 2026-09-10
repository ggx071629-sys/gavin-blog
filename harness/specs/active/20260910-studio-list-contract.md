---
id: spec-20260910-studio-list-contract
level: L1
summary: 补齐后台内容列表搜索筛选计数的真实分页契约
load_when:
  - task:20260910-studio-list-contract
task_id: 20260910-studio-list-contract
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - packages/contracts/README.md
documentation_reason: 定义新增管理查询的字段、计数和分页语义。
state_history:
---
# Context
阶段二完成。三个管理列表现有数组接口仅支持 limit/offset，设计要求完整搜索和发布状态计数。
# Goal
新增已认证 query 端点与共享 Web 消费类型，查询先于分页且计数来自数据库。
# Non-goals
不修改公开列表、既有数组接口、发布语义、存储模型或真实助手配置。
# Acceptance criteria
- AC-1: 三类管理查询按标题或书名作者字面包含查询并在分页前筛选状态；计数排除删除内容且按关键词统计，非法参数拒绝，匿名不可访问。
- AC-2: 旧数组接口与公开发布快照分页保持，OpenAPI 与 Web 消费模型同步。
# Risks
SQL 通配符需转义；空查询不得被当成全表客户端过滤；计数不读取整个内容集合。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-QUERY-01
- AC-2 => M02-STUDIO-QUERY-01, M02-PAGINATION-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
