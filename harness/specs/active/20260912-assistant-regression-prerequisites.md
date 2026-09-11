---
id: spec-20260912-assistant-regression-prerequisites
level: L1
summary: 修复三个失效问答回归测试的真实前置条件
author: Codex
load_when:
  - task:20260912-assistant-regression-prerequisites
task_id: 20260912-assistant-regression-prerequisites
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 只修正三个失效测试的前置条件与旧库构造方式，不改产品契约、API、数据模型、迁移或运行行为，因此没有 durable 文档影响。
state_history:
---
# Context
2026-09-12 的知识问答缺口审查用独立诊断证明：两个竞态用例因输入预算低于固定提示开销而从未调用模型替身，一个旧库恢复用例用“从最新 schema 删两张预算表并回写版本号”的合成旧库，保留当时不存在的 admin_credentials，导致迁移重复建表失败。三项都属于测试前置条件漂移，不能继续引用它们旧的通过结论，也不能把诊断中的通过当作原测试已修复。
# Goal
让这三个用例在真实前置条件下重新通过：竞态用例的模型调用确实发生，旧库用例的快照来自迁移生成的真实旧结构；并且前置条件本身被显式断言，未来再次漂移时用例直接失败而不是静默跳过目标路径。
# Non-goals
不修改产品运行路径、生成预算上限、提示词、检索或迁移代码；不放宽任何断言；不为追求通过而删除或跳过用例；不调用模型或部署。
# Acceptance criteria
- AC-1: 两个竞态用例在高于固定提示开销的输入预算下运行，模型替身被调用且租约与晚到结果路径真正执行；等待前置不成立时用例失败并说明原因，而不进入后续断言。
- AC-2: 旧库恢复用例用 Alembic 迁移到 20260907_0024 生成旧结构，在快照前断言版本号及缺失的共享预算表与 admin_credentials，并断言快照清单记录同一版本；恢复到 fresh 目标后迁移到 head、生成共享预算策略与空预留表并保留恢复日锁。
# Risks
提高测试输入预算只改变测试配置，不改变产品预算策略；合成旧库路径必须保持失败可见，不能被重新引入为“等价”前置；旧库断言依赖迁移 revision 名称，迁移重命名或压缩时需要同步复核。
# Verification plan
## Verification cases
- AC-1 => M09-UNIT-ASSISTANT-RUNTIME-INTEGRITY-01
- AC-2 => M10-UNIT-ASSISTANT-LEGACY-SCHEMA-RESTORE-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
