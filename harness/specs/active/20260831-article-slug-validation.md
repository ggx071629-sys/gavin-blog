---
id: spec-20260831-article-slug-validation
level: L1
summary: 阻止新建文章提交无效标题或 slug，并向管理员显示可操作的字段错误
load_when:
  - task:20260831-article-slug-validation
author: Codex
task_id: 20260831-article-slug-validation
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 本任务修复既有 ASCII slug 合同下的表单校验与错误反馈，不改变长期产品、架构、API 或运维边界。
state_history:
---

# Context

新建文章页会从标题自动生成 slug，但现有生成器只保留 ASCII 小写字母、数字和连字符。纯中文标题会得到空 slug，页面仍向 API 提交请求；FastAPI 正确返回 422，而页面只显示通用失败文案，管理员无法在提交前定位字段问题。

# Goal

在保持现有后端 ASCII slug 与稳定 URL 合同不变的前提下，让新建文章页在客户端阻止无效标题或 slug，并提供明确、可访问且可操作的字段错误；合法表单仍可创建草稿。

# Non-goals

- 不允许中文 slug，也不修改 API schema、数据库模型或公开 URL 规则。
- 不引入拼音转换、随机 slug 或新的运行时依赖。
- 不改动项目、书摘或既有文章编辑器的 slug 行为。

# Acceptance criteria

- AC-1: 空标题、空 slug 或不符合小写字母/数字/单连字符规则的 slug 在客户端被阻止提交，并在对应字段附近显示可访问错误。
- AC-2: 纯中文标题自动生成空 slug 时，页面明确要求填写英文或拼音 slug，不再产生 `POST /api/v1/admin/articles` 422 请求。
- AC-3: 合法标题与 slug 仍能提交创建草稿；服务端拒绝的创建请求保留可见反馈，而不是静默失败。

# Risks

- 客户端规则若与后端漂移，会错误阻止合法请求或继续放行无效请求。
- 错误反馈若只依赖颜色或不关联字段，会造成无障碍回归。
- 新增提交屏障不能破坏现有 CSRF、栏目、标签和成功导航流程。

# Verification plan

- web-quality => AC-1, AC-2
- e2e => AC-3
