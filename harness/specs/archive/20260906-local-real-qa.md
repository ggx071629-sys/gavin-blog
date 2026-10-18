---
id: archive-20260906-local-real-qa
level: L2
summary: 显式本机真实问答启动、readiness隔离及阶段F实测
load_when:
  - task:20260906-local-real-qa
task_id: 20260906-local-real-qa
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 交付本机真实问答启停、密钥/预算/索引维护和资源实测说明。
evidence_sha256: 55e49ce79680784e2a7d5474a0fb9601ebfcdf1eeb85dcf847e447884bf85504
state_history:
---

# 20260906-local-real-qa

Deterministic compressed record. The original active spec remains in Git history.

## Goal

复用现有开发启动器、真实E5索引、在线graph和预算数据库接通本机真实问答。仅对固定回环origin和development签发本机receipt，验证已签名本机probe与当前配置一致。保留持久runtime账本；执行有界中英/连续/无证据问答和故障回归，记录实际进程资源、延迟及费用。

## Acceptance criteria

- AC-1: 显式real开发启动仅允许development、回环监听及origin、真实E5和官方DeepSeek；缺少或篡改本机probe/配置时不能签发receipt或启用gate，production仍要求原profile，离线命令不变。
- AC-2: 真实模式复用原运行时、引用/版本/预算/清理合同，runtime账本持久保存，正常重启不能刷新费用；本机启用仅在校验后发生，退出停止本轮进程。
- AC-3: 同一真实E5/Chat链完成双语、连续和无证据问答；故障、预算、删除/清理及输出合同有精确回归。按现有统计工具记录真实Chat下API内存、CPU和响应延迟，文档区分实测、估算及未验收项。
- AC-4: Web 接受既有 API 的多段引用、按文章去重来源合同；实时回答和恢复都保留全部已校验编号，同路径不同段引用不能误拒，伪造编号/路径仍拒绝。
- AC-5: 租约表支持既有同 IP 2 路、全局 3 路合同，满额仍返回受控 429；迁移保留现有租约、费用和 saver 数据，不靠重置 runtime 回避冲突；异步 saver 不遗留跨 await 的隐式事务阻塞同步控制写入，双图运行及删除屏障通过回归。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-local-real-qa.json](../../verification/evidence/20260906-local-real-qa.json)

SHA-256: `55e49ce79680784e2a7d5474a0fb9601ebfcdf1eeb85dcf847e447884bf85504`

Closed at 2026-09-06T12:29:48.694302+00:00.
