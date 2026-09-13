---
id: decision-local-deepseek-chat
level: L2
summary: 本机 DeepSeek JSON 输出与严格应用校验的边界
load_when:
  - local-chat-compatibility
author: Codex
---

# 本机 DeepSeek Chat 适配

2026-09-06，主计划阶段 E。普通调用成功不能证明结构化接口合同通过。官方 [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/) 仅列出 text/json_object，输出上限参数为 max_tokens，thinking 默认 enabled；[JSON 指南](https://api-docs.deepseek.com/guides/json_mode/) 要求提示中明确 JSON 格式。[LangChain 文档](https://docs.langchain.com/oss/python/langchain/models#structured-output) 说明 json_mode 需在提示中描述 schema。

development 的官方 HTTPS 根与 /v1 endpoint 使用既有 ChatOpenAI 子类，仅转换最终请求字段；不新增 SDK、网络客户端或账本。既有 graph 改用共享 bind_answer_model，保留 include_raw、原有费用结算和引用校验。其他端点与 production 继续原严格 schema 协议。没有错误后自动回退，也不会自动重试真实请求。

JSON 模式不提供供应商端 schema 强制约束。应用等价保证是：完整原始 JSON 必须经过严格 Pydantic 类型、必填字段和 extra=forbid 校验；不接受框架自动修复的半截 JSON、markdown fence 或尾部文本；验证成功后仍必须通过既有完成原因、引用别名、内容版本与输出安全检查。不能把此保证称为供应商 strict schema 通过，也不能据此推断回答事实忠实性。

schema 指令由发送链和 estimator 共用，追加的 system 消息在发送前计入 byte 上界，避免预算只覆盖用户提示。输出限额在最终传输层由 max_completion_tokens 转为 max_tokens。JSON 模式的 response_format 通过 SDK extra_body 合并到相同顶层请求字段，使 SDK 使用 create 而非提前对 length 抛异常的 parse；应用保留截断响应的 usage，再拒绝发布不完整回答。解析错误只返回固定错误代码，不记录供应商正文。

本次不修改生产资格探测或 readiness。真实 Chat 启动仍须解决本机独立 readiness 边界，禁止传入伪造生产 profile 或以 test provider 冒充真实服务。既有生产任务保持冻结；本机测试预算、供应商版本/价格复核和 E/F 实测结果继续由 build-qa 主计划维护。新适配测试使用合成 HTTP 响应，不是供应商兼容性实测。

阶段 F 补充：增加显式 `dev:assistant:real`、签名的本机 probe 和仅 development 可用的 readiness 路径，复用原账本、图与开关。完整空 blocks 在本地适配中表示证据不足；来源仍按路径去重，Web 保留段落编号并映射到共同来源。生产 strict-schema/profile 保持独立。步骤和证据见 [真实问答交接](../operations/local-real-qa.md)。

真实并发发现租约唯一约束与已有 IP=2/global=3 合同冲突，v4 迁移将 owner turn 纳入唯一键；迁移不丢弃既有租约、预算或 saver 行。另将 API 的 aiosqlite saver 连接设为 autocommit，避免异步语句后的隐式事务跨 await 阻塞同事件循环的同步控制写入。原有 thread identity、会话序列化和 DELETE 完成后零残留检查继续负责可交付边界；部分多语句写入只能进入原恢复清理流程。此决策仍限定单 API owner，不构成多进程 SQLite 支持。
