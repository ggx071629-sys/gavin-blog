---
id: spec-20260906-local-real-qa
level: L1
summary: 显式本机真实问答启动、readiness隔离及阶段F实测
load_when:
  - task:20260906-local-real-qa
task_id: 20260906-local-real-qa
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 交付本机真实问答启停、密钥/预算/索引维护和资源实测说明。
state_history:
---

# Context

E阶段真实DeepSeek结构化请求已通过，本轮保守支出0.000774元，余0.999226元。E5服务与Qdrant目前未启动。现有离线启动使用test provider，生产readiness要求production profile；需要独立且显式的development真实启动边界。

# Goal

复用现有开发启动器、真实E5索引、在线graph和预算数据库接通本机真实问答。仅对固定回环origin和development签发本机receipt，验证已签名本机probe与当前配置一致。保留持久runtime账本；执行有界中英/连续/无证据问答和故障回归，记录实际进程资源、延迟及费用。

# Non-goals

不部署生产、不恢复冻结生产资格任务、不改变默认离线入口、不新增客户端/探测器/账本实现、不用本机推算冒充2核4GB目标机验收。测试时最多12个问答turn，单turn最多两次Chat及既有token上限，总预留必须在剩余额度内。

# Acceptance criteria

- AC-1: 显式real开发启动仅允许development、回环监听及origin、真实E5和官方DeepSeek；缺少或篡改本机probe/配置时不能签发receipt或启用gate，production仍要求原profile，离线命令不变。
- AC-2: 真实模式复用原运行时、引用/版本/预算/清理合同，runtime账本持久保存，正常重启不能刷新费用；本机启用仅在校验后发生，退出停止本轮进程。
- AC-3: 同一真实E5/Chat链完成双语、连续和无证据问答；故障、预算、删除/清理及输出合同有精确回归。按现有统计工具记录真实Chat下API内存、CPU和响应延迟，文档区分实测、估算及未验收项。
- AC-4: Web 接受既有 API 的多段引用、按文章去重来源合同；实时回答和恢复都保留全部已校验编号，同路径不同段引用不能误拒，伪造编号/路径仍拒绝。
- AC-5: 租约表支持既有同 IP 2 路、全局 3 路合同，满额仍返回受控 429；迁移保留现有租约、费用和 saver 数据，不靠重置 runtime 回避冲突。

# Risks

JSON应用schema不保证事实忠实性，需要人工复核引用与证据；本机profile不提供公网资格。模型数据将只包含合成问题及公开内容。实际测试预算受先验最大调用数和持久账本双重检查；费用使用高峰未缓存价保守估算，不冒充供应商精确账单。

# Verification plan

## Verification cases

- AC-1 => M09-LOCAL-REAL-BOUNDARY-01
- AC-2 => M09-LOCAL-REAL-RUNTIME-01
- AC-3 => M09-LOCAL-REAL-QA-01
- AC-4 => M09-LOCAL-REAL-CITATIONS-01
- AC-5 => M09-LOCAL-REAL-CONCURRENCY-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
- web-quality => AC-4
