---
id: spec-20260912-markdown-line-endings
level: L1
summary: Markdown 导入兼容 CRLF 换行且不放宽既有 front matter 校验
load_when:
  - task:20260912-markdown-line-endings
author: Codex
task_id: 20260912-markdown-line-endings
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: API 文档记录了导入的批次与 front matter 校验契约，需要补充解析前统一换行的行为。
state_history:
---
# Context
审查确认：同一 UTF-8 Markdown 内容以 CRLF 保存时报 `front matter is required`，LF 文件成功。根因是 parse_markdown 用 startswith("---\n") 判断 front matter，CRLF 文档首行为 `---\r\n`，于是被误判为缺少 front matter，正文里的 CRLF 也会原样进入存储。
# Goal
让同一内容的 LF 与 CRLF 文件得到一致的元数据、正文与仅创建草稿的结果，同时保持既有 front matter、YAML、编码与批次校验不变。
# Non-goals
不新增 ZIP 导入、不扩展编码或其他导入格式、不改变批次与字节上限、不改变重复 slug 与导出契约、不吞掉非法 front matter。
# Acceptance criteria
- AC-1: 同一内容的 LF/CRLF 文件导入得到一致的元数据、正文（不含 CR）与草稿状态。
- AC-2: 既有校验不放宽：缺少或未闭合 front matter、YAML 别名、非法 YAML 与非 UTF-8 仍被拒绝。
# Risks
在正文层面统一换行会改写存储的正文，因此必须确认导出与公开读取仍按 LF 往返；只替换 \r\n 而漏掉单独 CR 时旧式换行仍会失败；把校验放宽到“找不到 front matter 也继续”会误收非法文件。
# Verification plan
## Verification cases
- AC-1 => M05-CRLF-IMPORT-01, M08-DOCS-01
- AC-2 => M05-CRLF-IMPORT-01
## Gates
- api-tests => AC-1, AC-2
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
