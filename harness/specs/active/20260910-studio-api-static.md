---
id: spec-20260910-studio-api-static
level: L1
summary: 补齐列表查询的类型和格式静态检查
load_when:
  - task:20260910-studio-api-static
task_id: 20260910-studio-api-static
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 仅排序导入、格式化既有表达式和显式解包 SQLAlchemy Row，不改变持久产品契约；阶段归档记录验收事实。
state_history:
---
# Context
U6-03 全量 API 检查发现阶段三代码的四处导入排序、长行及 SQLAlchemy Row 转字典的类型推断问题。
# Goal
恢复 API 全量 Ruff 与 Mypy，通过实际查询回归证明等价修复。
# Non-goals
不改变查询、计数、排序、分页、鉴权、数据模型或 API 字段；不修改质量规则。
# Acceptance criteria
- AC-1: 三类后台查询保留鉴权、查询后计数、转义搜索、稳定分页和公开边界，静态修复不改变用户可见结果。
# Risks
不得用 Any 忽略、禁用规则或修改门槛掩盖类型问题；格式修复限定相关五个文件。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-QUERY-01
## Gates
- api-tests => AC-1
- harness-integrity => AC-1
