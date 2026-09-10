---
id: spec-20260911-assistant-resume-refresh
level: L1
summary: Q3-04 首次换址自动导入和显式简历刷新
load_when:
  - task:20260911-assistant-resume-refresh
task_id: 20260911-assistant-resume-refresh
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录可信域配置、HTTP操作及有界重试。
state_history:
---
# Context
下载、解析、版本及索引边界已验收。用户最终选择首次/换址自动导入，同址手动刷新，无周期检查。
# Goal
将Profile写入、状态/刷新API和既有worker串联，提供有界且可恢复的请求执行。
# Non-goals
不实现管理页面或公开PDF路由，不调用真实简历或付费供应商。
# Acceptance criteria
- AC-1: Profile URL首次/换址与入队原子提交，清空撤销；其他资料更新不导入。管理员GET状态no-store不下载，POST需要Session/CSRF和epoch，合并在途请求202、冷却60秒429、未配置或旧epoch409。
- AC-2: worker在内容事务和备份写锁之外下载/解析，短事务复核lease；既有配置一次初始化，无周期或年龄过期。resume请求不因常驻重建/索引队列饥饿。
- AC-3: 成功同hash复用；网络暂时失败暂停证据并最多追加1/5/15分钟三次重试，尊重Retry-After；永久失败等待手动，崩溃重启有界恢复，被替换请求不能复活。状态区分检查成功与索引完成且无正文/URL秘密。
# Risks
网络/解析最长45秒；领取简历任务时owner与request租约90秒，进程崩溃后有界接管。外部工作期间不持备份锁，写入前重新领取短锁并检查身份。可信域默认为空。
# Verification plan
## Verification cases
- AC-1 => M06-RESUME-REFRESH-API-01
- AC-2 => M06-RESUME-REFRESH-WORKER-01
- AC-3 => M06-RESUME-REFRESH-RETRY-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
