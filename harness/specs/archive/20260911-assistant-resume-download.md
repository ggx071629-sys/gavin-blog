---
id: archive-20260911-assistant-resume-download
level: L2
summary: Q3-01 以可信域名和固定公网连接有界下载简历 PDF
load_when:
  - task:20260911-assistant-resume-download
task_id: 20260911-assistant-resume-download
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明可信 PDF 下载配置、网络边界和独立截止执行。
evidence_sha256: 47c209387c71d3234f2c6beb6e7cb4df91deb45828dd5950616740e318dcaf9e
state_history:
---

# 20260911-assistant-resume-download

Deterministic compressed record. The original active spec remains in Git history.

## Goal

只从显式信任的 HTTPS 域下载 PDF，逐跳验证并固定公网 IP，限制文件/连接/读取/总耗时，输出脱敏失败结果。

## Acceptance criteria

- AC-1: 精确可信域、443和每跳公网校验不可绕过；TLS仍校验原主机，拒绝未授权跳转、私网/DNS混合结果、凭据或非HTTPS。
- AC-2: 文件头/类型、10MiB上限、最多3跳、连接/读/30秒总截止有效；失败输出固定码，子进程不继承应用秘密/代理，不向日志泄漏 URL 或文件正文。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-resume-download.json](../../verification/evidence/20260911-assistant-resume-download.json)

SHA-256: `47c209387c71d3234f2c6beb6e7cb4df91deb45828dd5950616740e318dcaf9e`

Closed at 2026-09-10T17:38:57.891350+00:00.
