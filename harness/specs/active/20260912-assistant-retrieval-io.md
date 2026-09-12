---
id: spec-20260912-assistant-retrieval-io
level: L1
summary: 将在线同步查询 Embedding 与检索隔离到有界执行器
load_when:
  - task:20260912-assistant-retrieval-io
author: Codex
task_id: 20260912-assistant-retrieval-io
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录检索线程容量、取消后的结算和关闭等待边界，区分合成延迟与生产性能。
state_history:
---

# Context

Q2-07 已归档。Q3-01/G14 的 async retrieve_node 直接执行同步 Embedding、Qdrant 和 SQL，慢请求会阻塞事件循环。现有每次控制事务独立连接、内容 session 局部创建，可将整个检索工作单元隔离；支付、身份和 checkpoint 规则须保留。

# Goal

慢检索期间事件循环及其他会话可继续运行；执行器容量有界，取消不提前释放正在工作的线程槽，停止运行时先等待迟到结算再关闭控制数据库和 owner lock。

# Non-goals

不改变供应商重试、价格、额度、生产开关或持久化 schema；不声称线程可强制中止远端请求，不把合成延迟结果当作生产 P95；其他图节点的同步数据库调用不在本次隔离范围。

# Acceptance criteria

- AC-1: 受控慢 Embedding 和检索期间，实际应用事件循环、会话读取及心跳可运行；正常回答保持可用，工作线程不超过现有 Embedding 并发配置。
- AC-2: 排队取消不发请求；执行中取消不提前释放线程槽；关闭等待已发送工作完成并拒绝新工作。删除会话后迟到 Embedding 不写正文、向量、历史或 checkpoint，不重复结算或调用聊天。
- AC-3: 原始身份围栏、供应商迟到结果和状态 descriptor 边界通过适用回归；文档明确容量及关闭等待限制。

# Risks

Python 线程不能强制中止同步 IO，必须沿用 provider 超时并保留工作到实际结束；不能把 SQLAlchemy session 从事件循环传入线程。共享客户端仍使用原生同步接口，检索仅读；本地持久 Qdrant 的跨线程只读兼容性需实测。

# Verification plan

## Verification cases

- AC-1 => M09-RETRIEVAL-IO-01
- AC-2 => M09-RETRIEVAL-IO-02
- AC-3 => M09-RETRIEVAL-IO-03, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-3
