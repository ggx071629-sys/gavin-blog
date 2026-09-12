---
id: spec-20260912-assistant-context-closure
level: L1
summary: Q4-05 当前上下文及跨源引用回归收尾
author: Codex
load_when:
  - task:20260912-assistant-context-closure
task_id: 20260912-assistant-context-closure
verification_profile: stack
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明阶段四回归范围及未覆盖的实际质量。
status: active
---
# Context
Q4-02到04已验收；旧历史拼接测试预期需要与新行为同步，图内两个类型注解待修正。
# Goal
验证当前跨来源/冲突、撤销和引用定位，修复失效回归预期并保留状态最小化。
# Non-goals
不把离线替身作为实际内容、模型质量或生产资格证明。
# Acceptance criteria
- AC-1: 跨来源自述保留各引用和冲突，撤销简历在发送/生成/发布复检，About旧版不再hydrate；PDF只下载有效版本并拒绝危险路径。
- AC-2: 当前问题不带旧正文或历史查询入checkpoint，有限指代及换题在当前版本继续通过；类型标注与运行状态一致。
- AC-3: 完整性/时效提示与有限规则仍满足Q4边界；阶段结论明确真实质量尚未验收。
# Verification plan
## Verification cases
- AC-1 => M09-CONTEXT-CROSS-01, M09-RESUME-CITATION-UI-01
- AC-2 => M09-CONTEXT-HISTORY-01, M09-REFERENCE-RESOLVE-01, M09-REFERENCE-CLARIFY-01
- AC-3 => M09-PAGE-PRIORITY-01, M09-SCOPE-NOTICES-01, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- e2e => AC-1
- harness-integrity => AC-3
