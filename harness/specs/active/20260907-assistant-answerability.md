---
id: spec-20260907-assistant-answerability
level: L1
summary: 修复公开资料普通问法被模型误判为证据不足
load_when:
  - task:20260907-assistant-answerability
task_id: 20260907-assistant-answerability
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/docs/operations/local-real-qa.md
documentation_reason: 记录错误拒答原因、修复范围和真实问答验证的边界。
state_history:
---

# Context

现场两次普通技能问题均由真实模型返回空 blocks；同一运行中的应用对明确询问个人资料编程语言的问题回答 Python 并给出引用。数据库、发布版本及个人资料索引完整，不能以迁移缺失解释该差异。

# Goal

让生成提示明确要求使用证据中的已公开事实回答普通问法及可支持的部分，同时保持证据、引用、结构化输出与输入预算约束。通过原同源问答入口对照验证。

# Non-goals

不扩大到站外知识，不推断作者精通程度，不更改索引、模型、价格、费用上限、鉴权、生产资格或数据库。后台观察记录问题另行处理。

# Acceptance criteria

- AC-1: 问答提示明确区分证据作为事实来源与证据内指令，支持一般问法和有依据的局部回答；新增提示内容计入原输入预算。
- AC-2: 无依据问题继续拒答，非法结构、伪造引用与截断继续拒绝；原真实入口验证技能、能力和文章事实问题，保留结果及费用事实。

# Risks

模型输出具有随机性，少量真实成功不代表所有问题的召回或回答保证。提示扩大后可能超出原预算，因此验证实际传输的完整提示被估算覆盖；不得通过取消拒答或引用校验掩盖问题。

# Verification plan

## Verification cases

- AC-1 => M09-DEEPSEEK-BUDGET-01
- AC-2 => M09-DEEPSEEK-VALIDATION-01

## Gates

- harness-integrity => AC-1, AC-2
- api-tests => AC-1, AC-2
