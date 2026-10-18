# Chat 配置与兼容性要求

读取条件：当前任务需要核对配置字段、费用或兼容性验收条件时。连接配置和普通调用已完成；下文保留阶段 E 的完整要求，完成情况以 [主计划中的当前任务](../build-qa.md#current-task) 为准。

<a id="configuration"></a>
## 配置与调用要求

1. 向管理员提供本地 Embedding 验收结果，以及所需非秘密信息清单：供应商、Chat Completions Base URL、模型 ID、可核验版本声明、上下文窗口、价格/币种及实际日预算。
2. 管理员在供应商平台开通相应模型并创建 Key，在后端秘密配置或秘密管理服务中填写；不要把 Key 发到对话、写入本方案、提交 Git 或放入前端公开环境变量。
3. 指导填写下列现有配置；完整必填项以 `.env.example` 和配置校验器为准。供应商价格若不是人民币，需明确换算依据和更新时间。

| 配置组 | 要填写的内容 |
| --- | --- |
| `GAVIN_ASSISTANT_CHAT_PROVIDER` | `openai-compatible` |
| `GAVIN_ASSISTANT_CHAT_ENDPOINT` | 供应商支持 Chat Completions 的 HTTPS Base URL，核对是否需要 `/v1` |
| `GAVIN_ASSISTANT_CHAT_API_KEY` | 后端秘密注入 |
| `GAVIN_ASSISTANT_CHAT_MODEL` / `MODEL_VERSION` | 使用完整 `GAVIN_ASSISTANT_CHAT_` 前缀的模型 ID 与版本配置 |
| `GAVIN_ASSISTANT_CHAT_MAX_INPUT_TOKENS` / `MAX_OUTPUT_TOKENS` / `CONTEXT_WINDOW_TOKENS` | 使用完整 Chat 前缀；输入加输出预算不超过已确认窗口 |
| Chat 价格、并发和日预算 | 配置真实价格及管理员确认的额度；仓库 2 元日 cap 不等于供应商总账单保证 |
| Embedding 配置 | `openai-compatible`、本地服务 endpoint、内部 Key、E5 revision、384 维、并发/批次限制 |
| 本地 Embedding 单价 | 可按无按量 API 费用配置为 0，但真实 token 用量仍记录；服务器成本另计 |
| 其他运行配置 | Qdrant、独立 HMAC 秘密、runtime 路径、超时、release/policy 和目标环境资格配置 |

4. 管理员确认实际供应商及测试预算后，执行少量真实调用。验证 `json_schema` + `strict=True`、usage、finish_reason、模型身份、输出上限、超时和限额错误；不能只凭“兼容 OpenAI”宣传判断可用。
5. 若供应商不支持现有合同，明确不兼容项，选择符合要求的模型/端点，或在独立 spec 中调整适配；不偷偷关闭结构化输出、预算结算或引用校验。

当前执行重点：复用 `apps/api/app/assistant/providers.py` 的 `build_chat_model`、`graph.py` 的结构化回答及现有 `assistant_qualification/provider_probe.py`。不再新增平行客户端、探测器或预算账本。现有资格探测绑定 production/profile，本机联调与它的边界需要明确处理，不能伪造生产配置来绕过限制。先核对本次 HTTP 400 涉及的 `response_format` 与供应商实际支持范围；若需改变结构化输出方式，在独立 spec 中明确解析、schema 校验、引用约束和错误处理的等价保证，再修改既有适配并执行回归。

完成条件：管理员完成私密配置，实际 Chat 请求通过兼容性探测，测试消耗和模型身份可核查。

## 当前文件位置

真实配置使用 `apps/api/.env`；Key 在第一行 `DEEPSEEK_API_KEY` 中填写，项目字段通过变量引用读取。字段模板见 [`.env.example`](../../../apps/api/.env.example)，加载方式见 [API 操作说明](../../../apps/api/README.md)。不输出 Key，不将私密配置复制进计划或归档。
