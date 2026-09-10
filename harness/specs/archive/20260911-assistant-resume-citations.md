---
id: archive-20260911-assistant-resume-citations
level: L2
summary: Q3-06 简历事实边界与可撤销PDF版本引用
load_when:
  - task:20260911-assistant-resume-citations
task_id: 20260911-assistant-resume-citations
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 记录同源PDF版本路由、事实边界、不可用提示与索引历史时间。
evidence_sha256: a8a753012ad53ab4504650bb0e1fcf640bb22759607698fd37211ebac0877edd
state_history:
---

# 20260911-assistant-resume-citations

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让引用打开回答实际使用且仍有效的PDF版本，严格约束个人事实与操作状态，完成生成前/最终发布复检链。

## Acceptance criteria

- AC-1: 只读匿名PDF路由只服务当前合格已索引版本，原始字节一致，no-store/attachment/nosniff；暂停、换址、清空、未知或错误格式版本404，不建会话/下载外部文件/调用模型。失败仍保留最后成功索引时间。
- AC-2: 简历显式自述支持事实，冲突说明并引用双方；缺失简历说明不可用并回答其余有依据部分，操作状态不冒充证据别名。模型只能引用现有alias；生成及发布前拒绝旧证据，不将PDF正文加入checkpoint。
- AC-3: 前端仅允许严格32位小写hex版本路径，PDF使用普通链接，公开回答和管理试问可打开文件，恶意路径被拒绝；既有网页引用仍可用，范围文案说明已导入公开简历。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-resume-citations.json](../../verification/evidence/20260911-assistant-resume-citations.json)

SHA-256: `a8a753012ad53ab4504650bb0e1fcf640bb22759607698fd37211ebac0877edd`

Closed at 2026-09-10T18:45:06.696052+00:00.
