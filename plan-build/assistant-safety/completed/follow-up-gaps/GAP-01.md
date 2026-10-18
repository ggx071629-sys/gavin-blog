# GAP-01：复核缺口修复

- 状态：已验收并归档。
- 规格先行提交：`5f8f70d`；实现验收提交：`8357949`。
- 修复：中文紧邻数字和单位错配；含逗号完整句误拒；本人来源的作者自述转述；无据个人经历、共现推依赖代表例；完整教程引文误拒与已知改写攻击。
- 正反边界：保留否定、时间、主体和引用周围语境；教程引文豁免不覆盖凭据或外部执行请求；普通综合、部分回答、证据恢复与历史分区继续可用。
- 验收：`python -m tools.harness verify 20260911-assistant-gap-closure --close`，10 cases / 43 exact refs，api-tests 与 harness-integrity 均通过；隔离清理及确定性关闭成功。
- [规格归档](../../../../harness/specs/archive/20260911-assistant-gap-closure.md)
- [机器证据](../../../../harness/verification/evidence/20260911-assistant-gap-closure.json)
- [有限规则决策](../../../../harness/docs/decisions/20260911-assistant-gap-closure.md)

未调用配置模型、在线裁判或部署，未增加测试框架或大矩阵。仍不保证任意自然语言蕴含、任意数字单位或全部注入改写；新的表达可能误拒或漏检。本次关闭指已复现缺口及相邻正反例验收通过，不改写原离线评审的历史观察。
