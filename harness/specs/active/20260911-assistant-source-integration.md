---
id: spec-20260911-assistant-source-integration
level: L1
summary: 核验关于页和简历在同一问答运行链中的成功、更新及失败闭环
load_when:
  - task:20260911-assistant-source-integration
task_id: 20260911-assistant-source-integration
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录两来源联调的真实执行边界以及实际PDF仍待输入的差异。
state_history:
---
# Context
阶段四Q4-01/Q4-02。分项测试覆盖来源和UI，仍需在同一隔离内容库、真实解析/worker/检索/问答图中证明两来源共存与故障降级。用户已决定首次/换址自动导入，同址手动刷新，无周期检查。
# Goal
补充两来源与既有文章的可执行联调证据，避免用分项通过替代完整业务链。
# Non-goals
不修改产品取舍，不引入付费调用、外部网络依赖、部署或真实个人数据；Q4-03实际文件验收独立等待输入。
# Acceptance criteria
- AC-1: 管理员发布关于页并首次配置简历后，真实PDF解析和worker索引使两来源可在同一公开问答中被检索、引用并下载对应文件；既有文章仍可回答，证据预算和模型调用上限保持。
- AC-2: 同址新版手动刷新撤销旧PDF资格，当前版本引用不混用；下载失败时只回答关于页等有效来源并说明简历不可用；清空撤销缓存，关于页发布等待排除旧修订。
- AC-3: 既有公开/管理引用与刷新界面继续通过真实构建流程，明确浏览器夹具与真实代理范围、保留真实输入待验事项。
# Risks
确定性provider只验证调度、引用和响应合同，不证明真实模型事实识别质量。网络下载使用非个人PDF夹具，不证明目标文件服务允许下载或缓存刷新。实际输入仍需用户提供。
# Verification plan
## Verification cases
- AC-1 => M09-SOURCE-INTEGRATION-01
- AC-2 => M09-SOURCE-INTEGRATION-02
- AC-3 => M09-ABOUT-CITATION-01, M09-RESUME-CITATION-UI-01, M06-RESUME-ADMIN-UI-01
## Gates
- api-tests => AC-1, AC-2
- e2e => AC-3
- harness-integrity => AC-1, AC-2, AC-3
