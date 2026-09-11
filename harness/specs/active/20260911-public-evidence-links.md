---
id: spec-20260911-public-evidence-links
level: L1
summary: 修复公开教程的凭据管理链接被误判导致证据遗漏
load_when:
  - task:20260911-public-evidence-links
task_id: 20260911-public-evidence-links
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明完整收录与证据隔离边界及公开文档链接的处理。
state_history:
---
# Context
当前两页简历全文与索引无缺字，25个切片在SQLite、FTS和向量库一致。公开DeepSeek教程的api_keys管理页面链接触发凭据名称规则，导致一个正常正文切片被隔离。
# Goal
证据扫描允许普通HTTP(S)文档链接路径中的凭据名称，保留实际凭据值、指令注入及泄密指令拦截；用户问题规则保持原样。
# Non-goals
不取消证据隔离、不执行教程命令、不自动确认关于页模板、不增加付费模型调用、不承诺任意扫描PDF的OCR或所有问法的召回。
# Acceptance criteria
- AC-1: 普通凭据管理文档链接不隔离正文，真实检索可返回原被隔离配置步骤。
- AC-2: 链接内外的实际密钥和泄密指令仍被隔离，用户输入的原有拒绝行为保持。
# Risks
URL不可信，仅豁免URL路径中的名称；查询参数、片段、URL凭据值和正文仍检查。
# Verification plan
## Verification cases
- AC-1 => M09-EVIDENCE-LINKS-01, M08-DOCS-01
- AC-2 => M09-EVIDENCE-LINKS-02
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
