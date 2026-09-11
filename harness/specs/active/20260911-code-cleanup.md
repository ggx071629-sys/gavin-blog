---
id: spec-20260911-code-cleanup
level: L1
summary: 清理已复核的未使用实现与 React GSAP 适配依赖，保留现行动效和业务边界
load_when:
  - task:20260911-code-cleanup
author: Gavin
task_id: 20260911-code-cleanup
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 删除无消费者的内部实现和未使用适配依赖不改变公开行为、接口、数据、运行配置或现有边界说明；阶段处置和证据在 code-cleanup 计划维护。
state_history:
---

# Context

用户授权按 plan-build/code-cleanup 阶段顺序清理并验证。C1-01 已复核 16 个后端函数及 _Gen、Web 导出、依赖与本地产物。根 @gsap/react 没有业务消费者，但 gsap/ScrollTrigger 由 AssistantDiscovery 动态加载，必须保留。现有模块合同还引用将随无用导出移除的专用测试，修改这些 case 前需人工核对断言映射。

# Goal

按候选处置表删除无使用路径的内部实现，迁移 SSE 测试辅助，并只移除未使用的 @gsap/react 及确实失去消费者的锁记录。保留公开阅读、回收站、问答运行库与现有悬浮球功能，通过独立影响计划选择的精确验证。

# Non-goals

不移除两处 gsap 声明或改写动画；不改变接口、数据库迁移、预算、认证、存储、清理策略或质量门槛。保留 switch_generation、rebuild_search_index、parseAssistantTasks 和公开 SVG；无法确认安全的本地产物保留。不调用真实模型、不迁移真实库、不部署、不修改无关用户工作。不将基线或静态审查当作修复后通过。

# Acceptance criteria

- AC-1: 删除 store/readiness/hydrate/money/pragmas/routes/runner/runtime_schema 的无消费者候选后，问答到期正文、会话删除、SSE、租约与运行库预算保护保持现行结果。
- AC-2: 删除 Worker 私有旧清理函数和无调用 trash_item 后，索引版本/围栏及回收站恢复、删除、导入边界保持现行结果；保留 API-owner finalize 防误用入口和搜索维护函数。
- AC-3: 删除未消费 Web 导出和手写类型、迁移 splitSseForTest 后，slug 校验、同源/SSE/引用/字数处理、BFCache 与清除后的旧结果隔离保持现行结果；专用测试的合同同步必须先通过人工语义审计。
- AC-4: 移除未使用 @gsap/react 后，两处 gsap 声明及 ScrollTrigger 消费链不变，悬浮球持续动效、暂停偏好、减少动态效果、离页清理与发现入口通过既有回归；锁文件无无关升级。
- AC-5: 候选、保留项及未决产物均可追溯，影响归属和精确引用有效；正式验证只覆盖最终提交并经确定性 close 归档。

# Risks

Nuxt 自动导入不代表调用；仓库零引用不能排除维护使用。旧任务 parser 不能接入字段更多的 /sync。测试辅助移出生产模块不能损失 SSE 分片或 BFCache 真实覆盖。移除 npm 适配包时必须核对 peer React 的其他消费者及锁变化，禁止附带升级。未通过人工审计前保留当前测试与验证合同；未确认占用和递归路径安全前保留生成目录。

# Verification plan

## Verification cases

- AC-1 => M09-UNIT-ASSISTANT-EXPIRY-SERIALIZATION-01, M09-UNIT-ASSISTANT-RUNTIME-INTEGRITY-01, M09-UNIT-ASSISTANT-ONLINE-01
- AC-2 => M10-UNIT-ASSISTANT-INDEX-01, M05-UNIT-CONTENT-PORTABILITY-01
- AC-3 => M01-UNIT-ARTICLE-01, M09-UI-BOUNDARY-01, M09-UI-STATES-01
- AC-4 => M09-UI-ORB-MOTION-01, M09-UI-DISCOVERY-01
- AC-5 => M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- web-quality => AC-3
- e2e => AC-3, AC-4
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5
