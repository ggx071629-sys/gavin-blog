# 阶段三：提示词与输入防护

## 总体进度

- 完成：4/4；当前任务：无；总体状态：完成，转阶段四 S4-01。
- 范围：整理六类提示约束，修复正常技术问题误拒，核对问题、资料元数据及历史入口。
- 限制：不把删关键词当成防护方案；不让证据授予权限，不扩大为通用工具 Agent。
- 测试规模：各相关类别只取代表样例并复用现有覆盖，不做语言、编码、轮次的组合枚举。

## 任务清单

| 编号 | 任务名称 | 状态 | 关键前置 |
| --- | --- | --- | --- |
| S3-01 | 分段整理提示词与实际输出契约 | 完成 | S2-04、当期 SDD 就绪 |
| S3-02 | 区分正常安全讨论与直接注入请求 | 完成 | S3-01、基线对照样例 |
| S3-03 | 补齐资料字段与历史的注入边界 | 完成 | S3-02 |
| S3-04 | 完成攻击和正常问答配对回归 | 完成 | S3-03 |

## 当前任务

- 本阶段完成。43 个精确测试身份与适用 Harness 检查通过，spec 已确定性归档。
- 必要输入：[设计 §4](DESIGN.md#4-提示词补充)、[prompt.py](../../apps/api/app/assistant/prompt.py)、[providers.py](../../apps/api/app/assistant/providers.py)。
- 补充定位：[hydrate.py](../../apps/api/app/assistant/hydrate.py)、[preflight.py](../../apps/api/app/assistant/preflight.py)、[output.py](../../apps/api/app/assistant/output.py)。
- 阻塞：无；有限规则的剩余误拒/漏检留阶段四离线核对。
- 下一步：[阶段四 S4-01](PHASE-4-EVALUATION.md)。
- 完成条件：已满足，见 S3-04 归档。

## 简短验收

- 适用：[设计 §4 P-1](DESIGN.md#4-提示词补充)和 [§5 D-1—D-2](DESIGN.md#5-输入与资料防护)。
- S3-04 用少量代表样例检查 §5 所列类别，并有正常内容对照；已有覆盖直接复用，不建设攻击样例平台。
- 分开记录过滤、模型替身与最终输出；阶段四由 Codex 离线评审，不能宣称验证了部署模型抗注入能力。

## 已完成事项

- 完成：[S3-01](completed/phase-3-defense/S3-01.md)、[S3-02](completed/phase-3-defense/S3-02.md)、[S3-03](completed/phase-3-defense/S3-03.md)、[S3-04](completed/phase-3-defense/S3-04.md)。
