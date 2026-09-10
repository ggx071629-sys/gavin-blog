---
id: archive-20260911-assistant-resume-refresh
level: L2
summary: Q3-04 首次换址自动导入和显式简历刷新
load_when:
  - task:20260911-assistant-resume-refresh
task_id: 20260911-assistant-resume-refresh
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录可信域配置、HTTP操作及有界重试。
evidence_sha256: 5073de43582994f78c2420c1a3a3798f45e17f6c7934922bbcb2833a3c6b4150
state_history:
---

# 20260911-assistant-resume-refresh

Deterministic compressed record. The original active spec remains in Git history.

## Goal

将Profile写入、状态/刷新API和既有worker串联，提供有界且可恢复的请求执行。

## Acceptance criteria

- AC-1: Profile URL首次/换址与入队原子提交，清空撤销；其他资料更新不导入。管理员GET状态no-store不下载，POST需要Session/CSRF和epoch，合并在途请求202、冷却60秒429、未配置或旧epoch409。
- AC-2: worker在内容事务和备份写锁之外下载/解析，短事务复核lease；既有配置一次初始化，无周期或年龄过期。resume请求不因常驻重建/索引队列饥饿。
- AC-3: 成功同hash复用；网络暂时失败暂停证据并最多追加1/5/15分钟三次重试，尊重Retry-After；永久失败等待手动，崩溃重启有界恢复，被替换请求不能复活。状态区分检查成功与索引完成且无正文/URL秘密。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-resume-refresh.json](../../verification/evidence/20260911-assistant-resume-refresh.json)

SHA-256: `5073de43582994f78c2420c1a3a3798f45e17f6c7934922bbcb2833a3c6b4150`

Closed at 2026-09-10T18:14:33.304724+00:00.
