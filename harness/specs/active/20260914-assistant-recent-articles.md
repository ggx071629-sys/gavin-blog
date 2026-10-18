---
id: spec-20260914-assistant-recent-articles
level: L1
summary: 为问答补充基于公开修订的文章时间查询
load_when:
  - task:20260914-assistant-recent-articles
task_id: 20260914-assistant-recent-articles
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确时间查询的公开修订、有限自然语言、排序、引用与调用边界。
state_history:
---

# Context

“最近更新了什么文章”目前进入无时间证据的内容检索，“最新文章”直接被全局时效规则拒绝。用户授权本地修复，不部署。工作区已有其他任务改动，须保留。

# Goal

用户进一步要求 tool calling。在既有 LangGraph 内通过原生 ChatOpenAI.bind_tools 让模型选择 list_recent_articles 的排序、数量与窗口，服务端严格验证后执行内容库只读查询。默认最多五篇，支持单篇与最多十篇的明确数量，以及今天、本周、最近七天的时间窗口。时间使用北京时间，更新时间沿用公开 API 的当前修订发布时间，忽略草稿保存。来源标题、路径与时间全部来自当前公开修订，在终态发布前读取；复用会话授权、终态、引用、预算、重试和留存通道，不调用嵌入，不追加工具结果改写调用。

# Non-goals

不新增数据库字段或公开 API，不提供外站时效、全站总数、任职信息或任意主题/日期过滤，不修改预算准入与部署状态。未完整识别的复杂问题不得丢弃限定词后冒充全站时间查询。

# Acceptance criteria

- AC-1: 中英文常见最近发布/更新清单和单篇问题被识别，复杂限定、混合指令与其他时效问题保留既有边界。
- AC-2: 只列当前公开未删除文章；发布时间和更新时间分别排序，同时间稳定排序，数量与窗口有界，草稿保存不影响公开事实。
- AC-3: 通过真实本地 SSE 流返回可导航引用及明确空列表；原生工具调用在既有预算和重试上限内计量，不发送 Embedding，非法工具/参数拒绝执行，重放、会话删除与终态前撤销保持有效。

# Verification plan

## Verification cases

- AC-1 => M09-RECENT-INTENT-01, M09-SCOPE-NOTICES-01, M09-PAGE-PRIORITY-01
- AC-2 => M09-RECENT-QUERY-01
- AC-3 => M09-RECENT-SSE-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
