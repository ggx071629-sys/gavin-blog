# Chat 验证与运行恢复：计划入口

阶段 1、2 均已完成实施与隔离验收；目标是正常运行与正常重启不因验证记录单纯变旧而要求人工付费复验，真正的配置或兼容性变化再执行相应验证。部署不在范围内。

| 顺序 | 阶段主计划 | 当前任务 | 状态 |
| --- | --- | --- | --- |
| 1 | [运行与重启校验](CHAT-READINESS-PHASE-1.md) | 无（4/4 完成） | 完成 |
| 2 | [复验与账本恢复](CHAT-READINESS-PHASE-2.md) | 无（4/4 完成） | 完成 |

设计依据：[已讨论方案](CHAT-READINESS-DESIGN.md)。当前全局下一步：无，8/8 实施任务全部完成。

默认只读目标阶段主计划；实现、验收时再读设计依据对应章节，追溯事实时才读对应归档。
状态统一为：未开始、进行中、阻塞、未验证、完成；实施结束但验收未通过记为未验证。
当前任务就地更新；完成后先归档过程、关键决定和验证结论，再更新完成数与下一任务。
未完成任务不归档；仍有效的范围、限制和阻塞留在主计划。各阶段历史目录独立：

- 阶段 1：`plan-build/chat-readiness/completed/local-startup/`
- 阶段 2：`plan-build/chat-readiness/completed/revalidation-recovery/`

这些计划不替代 Harness spec、证据或其确定性关闭流程；阶段 1 spec `20260908-chat-readiness-age` 与阶段 2 spec `20260908-chat-revalidation-recovery` 均已确定性关闭并保留原始 Git 历史。
