---
id: spec-20260912-public-error-recovery
level: L1
summary: 公开页面首次客户端加载失败进入可恢复错误页而不是旧页面内容
load_when:
  - task:20260912-public-error-recovery
author: Codex
task_id: 20260912-public-error-recovery
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 只修复既有客户端错误呈现缺陷并新增回归，README 未记录页面错误态约定，没有需要同步的 durable 文档。
state_history:
---
# Context
审查确认：首页进入文章、关于进入读书时，列表请求 503 会让地址已切换到目标路由而 DOM 仍停留旧页面，且没有重试入口。根因是共享 useApiFailure 在客户端初次 setup 抛出的错误既不是 fatal 也不是 unhandled，Nuxt 根组件不会把它渲染为错误页，只留下未处理拒绝。
# Goal
让首次客户端加载失败在目标路由呈现既有全站错误页与操作内恢复入口；错误页的站内入口可用；服务端直接访问失败与公开详情缺失的既有语义不变。
# Non-goals
不新增页面级错误块、不引入重试策略或全站超时、不改变服务端状态码语义、不宣称其余 useApiFailure 消费者全部复验、不修改搜索索引与内容契约。
# Acceptance criteria
- AC-1: 首次客户端加载失败时目标路由渲染可恢复错误页，不再显示上一页内容。
- AC-2: 错误页恢复入口可用，且服务端失败、搜索后续失败与缺失详情语义保持不变。
# Risks
共享错误的 fatal 标记只在客户端生效，误加到服务端会改变既有 503 语义；错误页站内跳转若不清除错误状态会在恢复后仍停留错误页；其余消费者只继承修正，未逐一复验。
# Verification plan
## Verification cases
- AC-1 => M06-PUBLIC-ERROR-01
- AC-2 => M01-PUBLIC-ERROR-01
## Gates
- e2e => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
