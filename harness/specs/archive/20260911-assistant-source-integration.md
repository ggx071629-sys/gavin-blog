---
id: archive-20260911-assistant-source-integration
level: L2
summary: 核验关于页和简历在同一问答运行链中的成功、更新及失败闭环
load_when:
  - task:20260911-assistant-source-integration
task_id: 20260911-assistant-source-integration
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录两来源联调的真实执行边界以及实际PDF仍待输入的差异。
evidence_sha256: 2435a4cfc6f1072d82e8e9c3245054df3eaf66dde2531ad41193a5f142a5b96b
state_history:
---

# 20260911-assistant-source-integration

Deterministic compressed record. The original active spec remains in Git history.

## Goal

补充两来源与既有文章的可执行联调证据，避免用分项通过替代完整业务链。

## Acceptance criteria

- AC-1: 管理员发布关于页并首次配置简历后，真实PDF解析和worker索引使两来源可在同一公开问答中被检索、引用并下载对应文件；既有文章仍可回答，证据预算和模型调用上限保持。
- AC-2: 同址新版手动刷新撤销旧PDF资格，当前版本引用不混用；下载失败时只回答关于页等有效来源并说明简历不可用；清空撤销缓存，关于页发布等待排除旧修订。
- AC-3: 既有公开/管理引用与刷新界面继续通过真实构建流程，明确浏览器夹具与真实代理范围、保留真实输入待验事项。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-source-integration.json](../../verification/evidence/20260911-assistant-source-integration.json)

SHA-256: `2435a4cfc6f1072d82e8e9c3245054df3eaf66dde2531ad41193a5f142a5b96b`

Closed at 2026-09-10T19:03:59.556500+00:00.
