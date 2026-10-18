---
id: archive-20260911-code-cleanup
level: L2
summary: 清理已复核的未使用实现与 React GSAP 适配依赖，保留现行动效和业务边界
load_when:
  - task:20260911-code-cleanup
author: Gavin
task_id: 20260911-code-cleanup
status: compressed
documentation_impact: none
documentation_reason: 删除无消费者的内部实现和未使用适配依赖不改变公开行为、接口、数据、运行配置或现有边界说明；阶段处置和证据在 code-cleanup 计划维护。
evidence_sha256: 38a2127ebcc9ad9422ef78886873d57058a061a3731afee99892fd152149d921
state_history:
---

# 20260911-code-cleanup

Deterministic compressed record. The original active spec remains in Git history.

## Goal

按候选处置表删除无使用路径的内部实现，迁移 SSE 测试辅助，并只移除未使用的 @gsap/react 及确实失去消费者的锁记录。保留公开阅读、回收站、问答运行库与现有悬浮球功能，通过独立影响计划选择的精确验证。

## Acceptance criteria

- AC-1: 删除 store/readiness/hydrate/money/pragmas/routes/runner/runtime_schema 的无消费者候选后，问答到期正文、会话删除、SSE、租约与运行库预算保护保持现行结果。
- AC-2: 删除 Worker 私有旧清理函数和无调用 trash_item 后，索引版本/围栏及回收站恢复、删除、导入边界保持现行结果；保留 API-owner finalize 防误用入口和搜索维护函数。
- AC-3: 删除未消费 Web 导出和手写类型、迁移 splitSseForTest 后，slug 校验、同源/SSE/引用/字数处理、BFCache 与清除后的旧结果隔离保持现行结果；专用测试的合同同步必须先通过人工语义审计。
- AC-4: 移除未使用 @gsap/react 后，两处 gsap 声明及 ScrollTrigger 消费链不变，悬浮球持续动效、暂停偏好、减少动态效果、离页清理与发现入口通过既有回归；锁文件无无关升级。
- AC-5: 候选、保留项及未决产物均可追溯，影响归属和精确引用有效；正式验证只覆盖最终提交并经确定性 close 归档。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-code-cleanup.json](../../verification/evidence/20260911-code-cleanup.json)

SHA-256: `38a2127ebcc9ad9422ef78886873d57058a061a3731afee99892fd152149d921`

Closed at 2026-09-11T11:55:04.156506+00:00.
