---
id: archive-20260912-assistant-citation-locations
level: L2
summary: Q4-02 公开 About 证据字段并展示逐引用章节页码
load_when:
  - task:20260912-assistant-citation-locations
task_id: 20260912-assistant-citation-locations
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 说明公开 About 与问答来源定位的可核查范围。
evidence_sha256: 1d161669154427b3fe3548818ed3f35aff72cd9926af106fcf347acf91374a1b
state_history:
  - {"action":"freeze","at":"2026-09-12T14:25:00.119450+00:00","reason":"用户要求完成 Q4-01 后停止；Q4-02 仅准备规格，尚未实施。","scope_sha256":"17cb647d3a04c97045e3dedaa6c07a9c2b55f4d40e00d047869b7f7315f16f3f"}
  - {"action":"resume","at":"2026-09-12T14:41:44.094380+00:00","reason":"用户要求恢复 Q4-02 并依次完成剩余任务；沿用累计100次2元上限，未验证事项和Q6生产资格保留阻塞。"}
---

# 20260912-assistant-citation-locations

Deterministic compressed record. The original active spec remains in Git history.

## Goal

读者可以查看已经公开的 About 证据字段，并在每个引用编号处看到服务端章节或页码定位。

## Acceptance criteria

- AC-1: 公开 About 展示发布版 statement/editorial_topics，作为纯文本渲染，不显示未发布内容。
- AC-2: 同源多引用分别显示章节或页码，点击编号焦点落到对应定位且可返回；恢复后有效，源路径白名单及版本撤销保护保持。
- AC-3: 说明无章节时只能到来源正文核查，不伪造位置或完美定位承诺。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-citation-locations.json](../../verification/evidence/20260912-assistant-citation-locations.json)

SHA-256: `1d161669154427b3fe3548818ed3f35aff72cd9926af106fcf347acf91374a1b`

Closed at 2026-09-12T14:51:22.938439+00:00.
