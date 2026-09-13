# 问答助手主计划（已结项）

结项日期：2026-09-06。方案：本地 E5 + 第三方 OpenAI 兼容 Chat；已交付本机真实问答、资源估算与受限资源模拟验证。

**本计划已完成：A–F 及 D 补充实验均已完成，当前无进行中的任务。**
本页保留主进度、结项范围与归档入口；具体实施和测试事实按需查阅历史归档。

## 主进度

| 阶段 | 状态 | 任务或归档路径 |
| --- | --- | --- |
| A 环境与规格 | 已完成 | [A–C 归档](archive/stages-a-c.md) |
| B 本地 E5 服务 | 已完成 | [A–C 归档](archive/stages-a-c.md) |
| C 双语检索与索引 | 已完成 | [A–C 归档](archive/stages-a-c.md) |
| D 检索评估与本机资源推算 | 已完成 | [D 归档](archive/stage-d.md) |
| E 连接配置、普通调用 | 已完成 | [连接测试归档](archive/chat-connectivity-20260906.md) |
| E 结构化输出兼容性 | 已完成 | [E 归档](archive/stage-e.md) |
| F 完整真实问答与资源实测 | 已完成 | [F 归档](archive/stage-f.md) |
| D 补充：2 核 / 4 GB 本机模拟实验 | 已完成（用户确认） | [D 补充记录](archive/stage-d.md#supplement) |

<a id="current-task"></a>
## 结项状态与交付范围

真实 E5 + DeepSeek 的本机入口已实现。修复了多段引用误拒、空结果误重试、租约并发唯一约束和异步 saver 写锁等待。D 补充已按本机受限资源模拟测试完成；生产资格、HTTPS 与云端部署验收不属于本轮。

<a id="acceptance"></a>
### E/F 完成记录

- [x] E 阶段参数、严格应用 schema、usage、finish_reason 和预算合同通过；原资格探测及账本复用。
- [x] E/F 阶段用户批准测试总额 1 元、Chat 每日 2 元；该阶段最终保守费用 0.094950 元，无未结预留，不含后续 D 补充复测。
- [x] 显式 `npm run dev:assistant:real`，回环地址、签名 probe、本机 readiness、持久预算；不伪造生产 profile。
- [x] 中文、英文跨语言证据、连续追问、引用恢复、证据不足及两路真实请求完成；DeepSeek/Codex 配置题仍拒答，保留覆盖限制。
- [x] F 阶段补测资源：API 工作集峰值约 531 MiB；当时结合 D 基线规划 7–8 GiB 内存、3 个同档逻辑核、约 12 GiB 应用磁盘，属于历史保守估算，非最低配置或目标机保证。后续受限资源复测见主进度中的 D 补充记录。
- [x] 故障/预算/删除与保留账本迁移已补针对性回归；提交 5 个精确验收 case。
- [x] Harness 隔离验证通过：15 项检查、30 个精确测试引用；已确定性关闭并归档证据。
- [x] 更新 [本机操作交接](../../harness/docs/operations/local-real-qa.md)、配置模板和架构决策；原始日志仅留本地。

### 保留边界

- 不新增平行客户端、探测器或预算账本；保留结构化解析、schema 校验、引用约束与预算结算。若需换输出方式，先明确等价保证。
- 沿用后端 `.env`，不输出 Key 或原始供应商响应。现有资格探测绑定 production/profile，不通过伪造生产配置绕过限制。
- 本轮已完成本机联调与资源模拟；原 2 核 / 4 GB 虚拟机实验以本机 2 CPU / 4 GiB 容器复测完成，用户已确认该补充项完成。公网部署、防护与生产验收属于后续独立工作，不作为本计划未完成项；已知测试限制保留在对应归档中。

### 按需读取的必要章节

按当前问题选择入口，只读对应章节或函数，不批量预读全部文件。

| 当前问题 | 读取入口 |
| --- | --- |
| 请求参数 | [providers.py](../../apps/api/app/assistant/providers.py) 的 `build_chat_model` |
| 结构化回答与校验 | [graph.py](../../apps/api/app/assistant/graph.py) 的 `bind_answer_model` 及相关校验 |
| 探测与生产边界 | [provider_probe.py](../../apps/api/app/assistant_qualification/provider_probe.py) 的 `_validate_settings`、`_chat_probe`、`run_provider_probe` |
| 配置、上下文、价格和预算 | [Chat 配置要求](reference/chat-configuration.md#configuration) |
| 行为变更流程 | [SDD 规则](../../harness/specs/_sdd/README.md)，随后按 Harness 路由加载必要工作流 |
| 数据发送或部署边界 | [数据边界](reference/boundaries.md#data) / [本轮范围](reference/boundaries.md#scope) |

## 阅读与维护

- 本计划已结项，默认先读本页主进度与结项范围；仅需追溯具体事实时，按需查阅历史归档中的必要章节。
- 后续独立工作另立计划，不将本页的历史完成记录改写为进行中任务。
- 若明确恢复本计划，当前任务与进度仍直接维护在主 plan 中，不拆成独立文件；完成后再归档具体记录。
