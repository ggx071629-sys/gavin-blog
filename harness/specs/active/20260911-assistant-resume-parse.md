---
id: spec-20260911-assistant-resume-parse
level: L1
summary: Q3-02 在资源受限子进程中提取文本 PDF 简历
load_when:
  - task:20260911-assistant-resume-parse
task_id: 20260911-assistant-resume-parse
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录pypdf依赖、支持的PDF类型和解析资源隔离边界。
state_history:
---
# Context
Q3-01 已验收下载边界；本任务只将字节转换为有页码的文字，不写数据库或索引。
# Goal
使用锁定的pypdf在短生命周期子进程提取文字，强制资源上限并阻止网络/数据库访问。
# Non-goals
不新增OCR、人工预览、常驻进程或真实外部文件读取；不接刷新和持久化。
# Acceptance criteria
- AC-1: 未加密文本PDF可提取并保留页码，空/扫描/加密/损坏/超20页/超200000字符失败，返回固定原因而不虚构文字。
- AC-2: 子进程强制15秒和256MiB上限，禁止网络与数据库和任意文件读取；无法设置限制时parser_unavailable，不把线程超时当隔离。
# Risks
压缩内容可耗尽内存；Windows使用Job Object，POSIX使用resource限额；当前平台实测与其他平台代码支持分开记录。新增依赖只用于提取，不改变在线模型。
# Verification plan
## Verification cases
- AC-1 => M06-RESUME-PARSE-01
- AC-2 => M06-RESUME-PARSE-LIMITS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
