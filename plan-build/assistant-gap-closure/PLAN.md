# 知识问答缺口修复：计划入口

目标是修好问答助手并跑通页面提问→真实模型→校验→SSE→追问→刷新恢复。测试只用于确认修复和必要事实边界，复用已有有效结果，不扩展验收矩阵。按最新用户要求，实体手机和人工读屏已取消，不再作为待办或阻塞；不是验收通过。见[功能范围决定](../../harness/docs/decisions/20260913-assistant-functional-scope.md)。

当前执行：[阶段五执行状态](PHASE-5-QUALITY-EVALUATION.md)（阶段四5/5已验收归档；Q5所选回答修复和本地真实链路已跑通；独立人工复核与未覆盖来源质量未验证）。

阶段一5/5、阶段二7/7已完成所选范围并归档；独立当前内容质量尚未验证。

2026-09-12 用户再次确认 Q6 已取消：生产验证不在本计划范围，不是待办、前置或阻塞，不作生产资格结论。计划保留 Q1—Q5；Q5 未通过和未验证事项留在阶段五，不生成 Q6 完成归档。范围决定见[取消部署与线上验证](../../harness/docs/decisions/20260912-assistant-deployment-validation-scope.md)。

当前配置：输入32000、输出512；用户扩额为累计250次、4元，同一签名账本已用235次、3.438423元，剩15次、0.561577元，无未解决unknown。8个冻结新题首次结果与后续复验分开记录；真实页面链路及零调用刷新恢复已完成。见[最终结果](evaluation/Q5-RESULTS.md)。

| 顺序 | 独立阶段计划 | 关键前置 | 阶段历史 |
| --- | --- | --- | --- |
| 1 | [回归基线与关键词检索](PHASE-1-RETRIEVAL.md) | 无 | [phase-1-retrieval](completed/phase-1-retrieval/) |
| 2 | [事实支持、正常回答与注入防护](PHASE-2-ANSWER-RELIABILITY.md) | Q1-05 | [phase-2-answer-reliability](completed/phase-2-answer-reliability/) |
| 3 | [运行响应、预算与观测](PHASE-3-RUNTIME-OBSERVABILITY.md) | Q2-07 | [phase-3-runtime-observability](completed/phase-3-runtime-observability/) |
| 4 | [复杂问题、上下文与引用核查](PHASE-4-CONTEXT-CITATIONS.md) | Q3-06 | [phase-4-context-citations](completed/phase-4-context-citations/) |
| 5 | [当前内容与实际模型质量评测](PHASE-5-QUALITY-EVALUATION.md) | Q4-05 | [phase-5-quality-evaluation](completed/phase-5-quality-evaluation/) |

设计与条件定位：[设计依据及范围索引](DESIGN.md)。原始事实：[缺口审查报告](../assistant-safety/reviews/20260912-knowledge-qa-gap-analysis.md)。

默认读取目标阶段；实施或验收时读取对应设计章节，追溯具体事实时才读取对应历史。

状态及维护约定：[设计依据 M](DESIGN.md#m)。各阶段当前任务就地维护，本入口不保存任务过程。
