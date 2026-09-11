---
id: spec-20260911-index-vector-reuse
level: L1
summary: 相同正文新版本复用向量并停止不可重试错误的退避循环
load_when:
  - task:20260911-index-vector-reuse
task_id: 20260911-index-vector-reuse
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录向量复用条件与需要介入错误的终止规则。
state_history:
---
# Context
两篇文章重新发布相同正文，新版本触发索引，但历史成功的相同输入被账本拒绝重复发送；任务将此当临时错误重试8次。已有向量可从同代索引复用。
# Goal
在同一模型与pipeline身份下，按完全一致的切片正文复用同来源已存向量，并更新新版本元数据与FTS；需要介入的错误立即失败且保留准确状态。
# Non-goals
不隐式重发未知请求，不提高预算，不自动切换新索引或暂停问答，不删除历史失败记录。
# Acceptance criteria
- AC-1: 相同正文重新发布后更新索引版本且不再次调用嵌入；正文、身份、向量维度或绑定不匹配不得复用。
- AC-2: 结果未知或成功记录缺失可复用向量时立即终止，区分原因并保持禁止隐式重发；普通临时错误仍保留重试。
# Risks
读取到的向量必须验证绑定、维度与有限数值；复用后仍使用现有来源版本及worker fence检查防止旧任务覆盖新版本。
# Verification plan
## Verification cases
- AC-1 => M10-VECTOR-REUSE-01, M08-DOCS-01
- AC-2 => M10-VECTOR-REUSE-02
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
