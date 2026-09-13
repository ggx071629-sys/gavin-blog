---
id: decision-public-qa-admin-operations
level: L1
summary: 公开问答第五阶段采用默认关闭的 epoch gate、被动观测与 API-owner 两阶段索引切换
load_when:
  - task:20260829-public-qa-admin-operations
  - assistant-operations
author: Gavin
---

# 公开问答运营控制面决策

本文保留第五阶段决策。当前独立管理员试问、公开停用范围和共同总预算由 [2026-09-10 管理决策](20260910-assistant-management.md) 补充／替代相应旧描述；分类账本、被动观测、Worker 所有权与索引切换责任仍保留。

## 决策

第五阶段交付单管理员 `/admin/assistant`，但不执行 production enable。部署 API capability、Web launcher flag、runtime gate、readiness receipt 和被动健康分别保留权威，不压缩成一个布尔值。概览只读 runtime/content 两库的 allowlisted 本地事实并携带各自观察时间；刷新不调用 Chat、Embedding 或 Qdrant。

runtime gate fresh provision 默认 disabled，version 与 operational epoch 单调递增，并绑定 receipt、配置和 active generation。每个 admission、`prepared→sending`、正文 mutation、Saver 和 publish 都复核该 identity。安全停用不因 stale expected version 失败；响应后没有新 session、turn 或 sending。已经先越过 sending 的网络 handoff 不能撤回，但只能 exactly-once 无正文结算，旧 runner 不能发布结果。

三类北京时间账本分属既有 owner：Chat/query 在 runtime，index 在 content，统一以 `settled + reserved + new <= cap` 准入。人民币 2 元只指 Chat 的部署估算 cap；任何 cap 都不是供应商总账单保证，unknown usage 不由最坏费用倒推 token。

索引 retry 保留原失败行，并重新投影当前公开事实。sending/unknown 永不自动重发；已成功但结果未持久化的重计费 retry 必须 operator-authorized并保留 lineage。Worker 每进程 owner identity 唯一，使用单例 heartbeat、lease、单调 fence 和长调用续期；Qdrant mutation按 generation/source/revision/pipeline 收窄，失 fence 副作用写 repair intent。

rebuild 是持久命令，active outbox优先，staging 按 source revision 续跑且预算不足跨 BJT 等待。Worker 只标记 `ready_to_switch`，验证使用固定本地等维向量。finalize 由单 API owner 执行 runtime `switch_pending` fail-closed fence、content `BEGIN IMMEDIATE` digest/high-water/pointer 切换、runtime reconciliation。崩溃只允许留下可恢复的 switch pending；普通 enable 不能清 marker。切换后保持 disabled，重新签 receipt 后仍需显式 enable。

## 代价与边界

两库没有分布式事务，因此看板只能表达 partial/stale/unknown，不能宣称原子全局快照。停用不能撤回已发送的供应商请求，安全代价是丢弃正文而仍可能产生一次保守费用。真实供应商、代理链、Qdrant 持久化、备份恢复、2 vCPU／4 GB 实机与公网安全继续是后续 production No-Go；本地替身、dashboard 状态和 release gate 都不能替代这些资格。
