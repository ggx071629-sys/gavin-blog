---
id: archive-20260911-assistant-resume-parse
level: L2
summary: Q3-02 在资源受限子进程中提取文本 PDF 简历
load_when:
  - task:20260911-assistant-resume-parse
task_id: 20260911-assistant-resume-parse
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录pypdf依赖、支持的PDF类型和解析资源隔离边界。
evidence_sha256: 256b4d417e356dd606427c16302da3f44fd760b2efe401a4f5279509be7e7f71
state_history:
---

# 20260911-assistant-resume-parse

Deterministic compressed record. The original active spec remains in Git history.

## Goal

使用锁定的pypdf在短生命周期子进程提取文字，强制资源上限并阻止网络/数据库访问。

## Acceptance criteria

- AC-1: 未加密文本PDF可提取并保留页码，空/扫描/加密/损坏/超20页/超200000字符失败，返回固定原因而不虚构文字。
- AC-2: 子进程强制15秒和256MiB上限，禁止网络与数据库和任意文件读取；无法设置限制时parser_unavailable，不把线程超时当隔离。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-resume-parse.json](../../verification/evidence/20260911-assistant-resume-parse.json)

SHA-256: `256b4d417e356dd606427c16302da3f44fd760b2efe401a4f5279509be7e7f71`

Closed at 2026-09-10T17:52:42.419903+00:00.
