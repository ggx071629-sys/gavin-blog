---
id: spec-20260912-assistant-current-quality-harness
level: L1
summary: Q5 固定当前语料评测输入与受累计授权约束的运行器
author: Codex
load_when:
  - task:20260912-assistant-current-quality-harness
task_id: 20260912-assistant-current-quality-harness
verification_profile: stack
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 说明固定题集、当前语料、独立/调试划分、授权和实际质量局限。
status: active
---
# Context
Q4已验收；真实问答配置库有5份公开投影，累计模型调用78次/335376 micro-CNY。Q5需要当前版本题集与真实质量证据。
# Goal
固定当前语料题集与可复核期望，建立默认不付费、沿用原签名账本且拒绝漂移的评测运行器，并验证浏览器自动化范围。
# Non-goals
不改变生产资格、不增加调用或费用额度、不伪造独立人工标注/实体移动读屏/供应商账单证明；运行器通过不等于模型质量通过。
# Acceptance criteria
- AC-1: 题集区分debug/evaluation，来源版本和全文摘要固定，期望定位到原文；缺失来源、占位事实及独立人工复核未测范围显式记录。
- AC-2: 默认prepare不调用Chat/写费用；实际调用先复核同一授权/累计余额与语料，逐次预留/结算，未知结果保守结算后停止，拒绝额度/输入漂移。
- AC-3: 浏览器自动化验证恢复、移动布局/焦点、键盘和a11y可执行范围；人工读屏及实体设备验证保留未验证。
- AC-4: 真实输出/问题只保存在忽略的本地data，提交紧凑结果和限制；不把替身或离线准备当真实模型质量。
# Verification plan
## Verification cases
- AC-1 => M09-CURRENT-DATASET-01
- AC-2 => M09-CURRENT-BUDGET-01
- AC-3 => M09-CURRENT-BROWSER-01
- AC-4 => M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- e2e => AC-3
- harness-integrity => AC-4
