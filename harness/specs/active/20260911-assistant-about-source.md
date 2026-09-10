---
id: spec-20260911-assistant-about-source
level: L1
summary: 将管理员主动发布的关于页纳入现有问答检索和引用
load_when:
  - task:20260911-assistant-about-source
task_id: 20260911-assistant-about-source
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
documentation_reason: 记录新来源的发布资格、索引同步和关于页引用消费边界。
state_history:
---
# Context
执行 ASSISTANT-UPGRADE-PLAN 阶段二 Q2-01—Q2-05。现有四类来源没有关于页，默认 seed 不能代表管理员主动确认；前端入口允许 about 但回答引用尚不允许。遵循根目录 ASSISTANT-UPGRADE-CONTRACT.md 和 Q1-02 最终参数。
# Goal
新增 about 来源、明确发布资格、事务 outbox 与失效复检，使相关个人自述可被现有混合检索、预算和引用流程使用。
# Non-goals
不导入简历，不重建 RAG，不改公开关于页设计，不触碰无关工作区修改，不付费、不部署、不启用默认关闭的生产助手。
# Acceptance criteria
- AC-1: 关于页只有主动发布/回滚的当前修订可投影；草稿、自动 seed 和无发布版本不进入来源；升级旧库保留现有数据及四类来源约束。
- AC-2: 发布/回滚在内容事务内登记新版本索引；事务失败不泄漏任务，旧版立即失效，索引等待时其他来源可用，旧任务和重建不能恢复旧版本。
- AC-3: about 正文按既有 tokenizer 切片并参与关键词/向量检索与初次重建，相关证据满足片段预算及最终版本复检，不把整个页面无条件放入提示词。
- AC-4: 回答引用显示“关于 Gavin”并可点击 /about，公开与管理试问共享正确消费合同；提示词允许明确自述、拒绝从文章主题推断能力，冲突事实引用双方。
# Risks
历史 seed 与主动发布都标记 editor，需显式资格字段并保守回填；SQLite 扩展 CheckConstraint 必须新迁移；任意扩大 URL 白名单会放松引用安全；共同源码的消费者影响须逐项审查。
# Verification plan
## Verification cases
- AC-1 => M11-ASSISTANT-PROJECTION-01
- AC-2 => M11-ASSISTANT-SYNC-01
- AC-3 => M09-ABOUT-RETRIEVAL-01
- AC-4 => M09-ABOUT-CITATION-01, M09-ABOUT-FACTS-01
## Gates
- api-tests => AC-1, AC-2, AC-3, AC-4
- e2e => AC-4
- harness-integrity => AC-1, AC-2, AC-3, AC-4
