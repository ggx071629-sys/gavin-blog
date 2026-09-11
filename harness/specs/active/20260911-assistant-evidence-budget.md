---
id: spec-20260911-assistant-evidence-budget
level: L1
summary: 按模型剩余输入空间选取可引用的本站证据
load_when:
  - task:20260911-assistant-evidence-budget
task_id: 20260911-assistant-evidence-budget
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录证据输入预算、完整切片选择与引用校验边界。
state_history:
---
# Context
当前真实问题检索成功后输入估算约11253，超过8000。只裁剪历史不能解决本站资料过多；每日费用预算并未耗尽。
# Goal
在现有输入和每日费用上限内，确定性选择完整证据，让普通问题进入回答生成，并只接受实际发送证据的引用。
# Non-goals
不提高付费预算、不改变模型/凭据/资格、不降低估算安全界、不自动重发真实问题、不承诺检索未命中的资料可被回答。
# Acceptance criteria
- AC-1: 完整证据可容纳时保持原排序；超限先裁剪历史，再在检索候选内按来源轮转选择能装下的完整切片，跳过过大项并去除同来源同正文重复项，输入及输出预留均不超限。
- AC-2: 生成与已成功attempt恢复均将实际选中证据传给后续引用校验；未选中的别名不能被采纳。没有任何证据能装下时仍返回明确输入超限。
- AC-3: 本机既有代表问题在原8000上限内构建成功；不调用真实Chat、不修改配置和费用；文档同步。
# Risks
不得截断句子或改变正文事实，必须保留原别名和版本。来源覆盖只能在已有检索候选内实现，不能提升无关资料或伪造来源。
# Verification plan
## Verification cases
- AC-1 => M09-EVIDENCE-BUDGET-01
- AC-2 => M09-EVIDENCE-BUDGET-02
- AC-3 => M09-EVIDENCE-BUDGET-01, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
