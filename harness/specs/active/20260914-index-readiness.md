---
id: spec-20260914-index-readiness
level: L1
summary: 后台校验切换后的索引并续签既有运行资格
load_when:
  - task:20260914-index-readiness
task_id: 20260914-index-readiness
status: active
verification_profile: focused
planned_modules:
  - M11
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - packages/contracts/README.md
documentation_reason: 记录管理员资格续签接口、完整性检查和保持暂停的边界。
state_history:
---

# Context

服务器切换索引后，readiness仍绑定旧代，恢复试问返回503。用户授权本地开发、同步指定gavin-blog仓库并部署；数据和秘密不得提交，继续有限验证，不做长期压测。

# Goal

增加经管理员Session/CSRF保护的索引资格续签接口和高级维护按钮。只续签已经批准且非索引配置不变的资格：验证原HMAC及完整运行绑定、当前索引内容/FTS/Qdrant一致性、停用状态、维护保护与在途调用；通过后原子更新凭据。使用现有API owner与模型实例，不启动额外进程、不调用付费模型。请求绑定界面所见generation与gate版本，拒绝过期操作；重复请求安全。资格更新不恢复试问、不开放访客。

# Non-goals

不允许网页首次签发生产资格或批准模型、密钥、价格、预算、配置变化；不修改回答生成、关于页、数据schema或已有内容。

# Acceptance criteria

- AC-1: 真实重建和切换后可通过新接口续签，之后显式恢复试问成功；续签自身不恢复试问或开放访客，不增加模型调用。
- AC-2: 未认证、CSRF错误、过期版本、资格缺失/篡改/配置漂移、索引损坏、运行中或维护保护均拒绝且不改写凭据。
- AC-3: 后台提供续签步骤、操作中状态和明确失败提示，契约同步；构建和部署后当前索引续签及恢复试问可复查，原博客与数据保留。

# Verification plan

## Verification cases

- AC-1 => M11-READINESS-RENEW-01
- AC-2 => M11-READINESS-RENEW-02
- AC-3 => M11-READINESS-RENEW-03

## Gates

- api-tests => AC-1, AC-2
- api-lint => AC-1, AC-2
- web-quality => AC-3
- e2e => AC-3
