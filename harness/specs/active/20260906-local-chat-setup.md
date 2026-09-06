---
id: spec-20260906-local-chat-setup
level: L1
summary: 本机 LangChain OpenAI 兼容 Chat 配置与显式探测
load_when:
  - task:20260906-local-chat-setup
task_id: 20260906-local-chat-setup
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - build-qa.md
documentation_reason: 记录私密配置位置、零调用检查、显式单次探测及未完成的真实联调。
state_history:
---

# Context

用户跳过受限虚拟机测试，要求使用 LangChain 写好 OpenAI 兼容 Chat 并给出 API Key 文件路径。供应商、模型及预算尚未提供；用户自行在文件填写，不再阻塞工具实现。已有 build_chat_model 使用 ChatOpenAI，生产 probe 绑定完整生产 profile，不适合本机阶段 E。

# Goal

复用现有模型工厂与 ModelAnswer，新增显式本机 CLI：check 零网络验证，probe 每次最多一次真实 Chat Completions 严格结构化调用。提供可提交空白模板及忽略的 .env.chat 私密文件，不覆盖既有文件。配置包含 endpoint/model/key、输入输出上限、上下文和价格/测试/日预算。调用前持久预留保守费用，未知结果不退款；跨进程互斥，报告只含固定状态与数值，不打印秘密、端点或供应商原始正文。关闭 tracing，禁止自动重试。

# Non-goals

本轮不代填供应商、不付费调用、不启用公开 Chat/gate、不改生产资格、不修改现有 LangGraph 或 E5。阶段 F 的真实问答联调与增量内存测量后续执行。

# Acceptance criteria

- AC-1: check 不构造模型或调用网络；缺项和无效 endpoint/limits/prices 返回字段名，不泄露值；私密配置已忽略且创建不覆盖用户值。
- AC-2: probe 复用 ChatOpenAI 工厂，经严格 json_schema 和 max_completion_tokens 发出恰好一次请求；校验解析、usage、finish_reason、模型身份与预算上限；失败返回固定状态，无原文/Key，tracing 禁用。
- AC-3: 调用前持久保守预留，测试总预算和北京时间日预算均约束；异常/未知费用不退款，重复命令累计预算，损坏账本与并发锁失败不发送请求。

# Verification plan

## Verification cases

- AC-1 => M09-CHAT-SETUP-CONFIG-01
- AC-2 => M09-CHAT-SETUP-WIRE-01
- AC-3 => M09-CHAT-SETUP-BUDGET-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
