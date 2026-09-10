---
id: spec-20260911-assistant-resume-download
level: L1
summary: Q3-01 以可信域名和固定公网连接有界下载简历 PDF
load_when:
  - task:20260911-assistant-resume-download
task_id: 20260911-assistant-resume-download
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明可信 PDF 下载配置、网络边界和独立截止执行。
state_history:
---
# Context
阶段二完成；简历最终采用首次/换址或手动触发，无周期检查。当前只实现可信文件下载边界，不接运行任务。
# Goal
只从显式信任的 HTTPS 域下载 PDF，逐跳验证并固定公网 IP，限制文件/连接/读取/总耗时，输出脱敏失败结果。
# Non-goals
不解析或索引 PDF，不访问真实简历，不公开抓取接口，不引入常驻服务或付费调用。
# Acceptance criteria
- AC-1: 精确可信域、443和每跳公网校验不可绕过；TLS仍校验原主机，拒绝未授权跳转、私网/DNS混合结果、凭据或非HTTPS。
- AC-2: 文件头/类型、10MiB上限、最多3跳、连接/读/30秒总截止有效；失败输出固定码，子进程不继承应用秘密/代理，不向日志泄漏 URL 或文件正文。
# Risks
DNS检查与连接分离会重绑定；阻塞DNS不能只靠socket超时控制，使用 worker 所有的短生命周期网络子进程作总截止，不新增常驻服务。真实连接与资源实现仍受本地平台验证。
# Verification plan
## Verification cases
- AC-1 => M06-RESUME-DOWNLOAD-01
- AC-2 => M06-RESUME-DOWNLOAD-LIMITS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
