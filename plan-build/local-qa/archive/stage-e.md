# 阶段 E：结构化 Chat 兼容性归档

2026-09-06 完成。返回 [主计划](../build-qa.md)。

DeepSeek 官方接口使用 JSON object 与 max_tokens，未提供供应商 strict JSON schema。复用原 LangChain ChatOpenAI、graph、provider_probe 与预算账本，通过 development-only 请求适配与应用严格 schema 验证；禁止半截 JSON 修复、额外字段和未知引用，保留 usage、finish_reason、模型来源与保守结算。

用户批准 E/F 总额 1 元、Chat 每日 2 元；两次真实结构化 probe 共 0.001548 元（高峰未缓存价保守估计）。响应只证明模型 alias；版本声明由官方文档固定。不存在生产资格结论。

- [兼容性归档](../../../harness/specs/archive/20260906-deepseek-chat-compatibility.md)：13 项检查、7 个精确测试引用通过。
- [本机探测归档](../../../harness/specs/archive/20260906-local-chat-probe.md)：13 项检查、9 个精确测试引用通过。
- [架构边界](../../../harness/docs/decisions/20260906-local-deepseek-chat.md)。

F 阶段结果和累计费用由主计划与 [真实问答交接](../../../harness/docs/operations/local-real-qa.md) 维护；不再以普通 Chat 成功代替完整链路验收。
