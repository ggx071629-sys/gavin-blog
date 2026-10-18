# 阶段二：事实支持、正常回答与注入防护

## 总体进度

- 完成：7/7；当前任务：无；总体状态：本阶段所选范围完成。
- 有限合成样例及跨链路回归通过；任意语义、当前真实内容质量与生产资格仍未证明。

## 任务清单

| 编号 | 任务名称 | 状态 | 关键前置 |
| --- | --- | --- | --- |
| Q2-01 | 建立正反例并确定事实校验改进方案 | 完成 | Q1-05 |
| Q2-02 | 处理无依据事实、否定、时间、主体和冲突（G01/G03） | 完成 | Q2-01 |
| Q2-03 | 处理数字归属、中文数值与单位换算（G02） | 完成 | Q2-02 |
| Q2-04 | 减少合法改写、归纳与换算误拒（G04） | 完成 | Q2-03 |
| Q2-05 | 允许安全的技术符号和数组表达（G05） | 完成 | Q2-04 |
| Q2-06 | 区分技术讨论、资料示例与执行指令（G06/G07） | 完成 | Q2-05 |
| Q2-07 | 验证正反例、公开/管理/恢复链路并收尾 | 完成 | Q2-06 |

## 阶段交接

- [x] 最终输入上的事实、引用、公开问答、管理试问及恢复链路回归通过。
- [x] Web公开/管理引用与恢复消费者24条单元测试通过。
- [x] 记录最终适用范围及残余语义、真实内容质量和生产资格未验证项。

- 输入：[设计 D2](DESIGN.md#d2)；最终校验器与提示，以及阶段已完成证据。
- 结果：API33条精确引用初次32通过，唯一失效前提修复后正式验收通过；产品代码未因此变化，原成功证据有效。
- G07：6正常真实输出同提示重放通过，18攻击实测未见注入服从/秘密泄露；累计账本78次/335376 micro-CNY，剩22次/1664624 micro-CNY。见[实际状态](evaluation/G07-status.json)。
- 下一步：[Q3-01同步IO隔离](PHASE-3-RUNTIME-OBSERVABILITY.md)，不将本阶段结果当作生产资格。

## 简短验收

- 按[设计依据 D2](DESIGN.md#d2)引用的适用条件验收，不复制矩阵或新增门槛。
- 实施完成未验证时标记“未验证”；通过适用验证后才能标记“完成”。

## 已完成事项

- [Q2-01 正反例与方案比较](completed/phase-2-answer-reliability/Q2-01.md)：40例离线比较完成，选定有限确定性修复路径，残余语义明确。
- [Q2-02 有限事实与语境支持](completed/phase-2-answer-reliability/Q2-02.md)：10 cases / 23 exact refs 通过，残余语义明确。
- [Q2-03 数值原位规范化](completed/phase-2-answer-reliability/Q2-03.md)：5 cases / 4 exact refs 通过。
- [Q2-04 有限改写与摘要](completed/phase-2-answer-reliability/Q2-04.md)：5 cases / 4 exact refs通过，诊断40例错放0/误拒4，未覆盖项已记录。
- [Q2-05 安全技术文本](completed/phase-2-answer-reliability/Q2-05.md)：6 cases / 16 exact refs，通过后归档。
- [Q2-06 讨论与执行及实际挑战](completed/phase-2-answer-reliability/Q2-06.md)：有限样例通过；旧失败和残余语义误拒保留。
- [Q2-07 阶段跨链路验证](completed/phase-2-answer-reliability/Q2-07.md)：API与Web消费者所选范围通过，无新增真实调用。
- 阶段历史目录：[completed/phase-2-answer-reliability/](completed/phase-2-answer-reliability/)。
