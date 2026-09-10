---
id: spec-20260911-assistant-resume-storage
level: L1
summary: Q3-03 简历版本缓存和索引失效边界
load_when:
  - task:20260911-assistant-resume-storage
task_id: 20260911-assistant-resume-storage
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录内容库缓存、资格及清理语义。
state_history:
---
# Context
下载和解析已独立验收；绑定与版本契约已确认。本任务提供持久化和索引原语。
# Goal
保存有界PDF/文本版本，以绑定代次和任务lease阻止迟到提交，立即撤销旧资格，版本限定清理派生索引。
# Non-goals
不接Profile HTTP更新/刷新调度/管理界面/公开PDF路由；这些在后续任务完成。不添加定时检查。
# Acceptance criteria
- AC-1: 迁移增加独立单例来源、版本和请求记录；PDF/正文在内容库，同hash/管线复用版本；换址/清空递增epoch并删除缓存，A到B到A不会复活引用。
- AC-2: 短事务检查epoch/request/owner/token/fence/lease；检查失败立即暂停，发现新hash先停旧证据再解析；过期或被替代工作不能写版本/outbox。
- AC-3: resume投影可重建并混合检索；hydrate拒绝失败/旧版；索引完成才可用，版本限定purge不能删除新版本，多代索引旧片段可清理。
# Risks
内容SQLite体积增加；删除是逻辑撤销不承诺清除备份/WAL。原索引purge按来源删除，须为简历增加版本限定路径避免迟到清理删除新版。
# Verification plan
## Verification cases
- AC-1 => M06-RESUME-STORAGE-01
- AC-2 => M06-RESUME-FENCE-01
- AC-3 => M10-RESUME-INDEX-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
