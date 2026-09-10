---
id: spec-20260911-assistant-resume-citations
level: L1
summary: Q3-06 简历事实边界与可撤销PDF版本引用
load_when:
  - task:20260911-assistant-resume-citations
task_id: 20260911-assistant-resume-citations
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 记录同源PDF版本路由、事实边界、不可用提示与索引历史时间。
state_history:
---
# Context
简历导入、版本、索引和管理端已验收，当前source.public_path尚未有PDF路由。状态展示审查发现失败时索引历史时间需保留。
# Goal
让引用打开回答实际使用且仍有效的PDF版本，严格约束个人事实与操作状态，完成生成前/最终发布复检链。
# Non-goals
不新增正文网页、外链跳转或模型生成href，不改变预算/历史上限，不调用真实简历或付费供应商。
# Acceptance criteria
- AC-1: 只读匿名PDF路由只服务当前合格已索引版本，原始字节一致，no-store/attachment/nosniff；暂停、换址、清空、未知或错误格式版本404，不建会话/下载外部文件/调用模型。失败仍保留最后成功索引时间。
- AC-2: 简历显式自述支持事实，冲突说明并引用双方；缺失简历说明不可用并回答其余有依据部分，操作状态不冒充证据别名。模型只能引用现有alias；生成及发布前拒绝旧证据，不将PDF正文加入checkpoint。
- AC-3: 前端仅允许严格32位小写hex版本路径，PDF使用普通链接，公开回答和管理试问可打开文件，恶意路径被拒绝；既有网页引用仍可用，范围文案说明已导入公开简历。
# Risks
已开始发送/已下载的文件不能撤回；取消资格对后续请求立即生效。模型遵循事实与冲突规则的真实质量不由夹具证明；只报告提示、校验和调用链结果。
# Verification plan
## Verification cases
- AC-1 => M06-RESUME-PDF-01
- AC-2 => M09-RESUME-FACTS-01
- AC-3 => M09-RESUME-CITATION-UI-01
## Gates
- api-tests => AC-1, AC-2
- e2e => AC-3
- harness-integrity => AC-1, AC-2, AC-3
