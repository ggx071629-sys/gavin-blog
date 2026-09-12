---
id: spec-20260912-assistant-budget-calibration
level: L1
summary: 离线分解提示预算并与官方 tokenizer 和已保存 usage 校准
load_when:
  - task:20260912-assistant-budget-calibration
author: Codex
task_id: 20260912-assistant-budget-calibration
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录当前最小输入、独立开销及官方 tokenizer 校准的适用范围，避免仅增大额度。
state_history:
---

# Context

Q3-01 已验收。G12 的字节保守上界无法展示各部分开销；当前模型响应只有 deepseek-flash 别名，配置版本不等于供应商版本证明。DeepSeek 官方 token usage 页面提供 tokenizer 数据，但说明实际 usage 为准。可复用 G07 已保存且提示一致的 24 个响应，不新增付费调用。

# Goal

建立只输出数值和来源摘要的离线预算报告，分别核对固定指令/协议、当前问题、历史、候选与选中证据、回答文本、supports 和 JSON。找出有限可答样例的精确输入边界，并对官方来源计数与实际 usage 误差作可复核校准。

# Non-goals

不切换模型或安装运行依赖，不降低现有保守准入上界、不提高输入/输出上限或修改两次生成预留；不将样例最小值、官方文本 tokenizer 或未知消息模板误差推广为通用安全上界。

# Acceptance criteria

- AC-1: 报告区分 UTF-8 字节、保守估算与 tokenizer 计数；输入各组成项可核算，候选与选中证据分别记录，空答、长 supports 和非法结构不会被算作有效可答输出。
- AC-2: 有限中英文可答样例在输入/上下文的精确边界通过、少一单位拒绝；保持证据完整、历史裁剪及原最坏费用预留。
- AC-3: 官方 tokenizer 数据校验 SHA 后仅作为数据读取，离线样例与已保存模型 usage 校准有哈希/范围来源；不联网或发送模型调用，不把未知模型版本和模板差异当作已验证。

# Risks

不同字段各自分词的总和未必等于整段计数；报告同时保留整体计数，标记边界差异。官方 tokenizer 的来源可信不等于与该响应具体版本完全绑定，任何误差测量不自动改变准入。原始问答和 tokenizer 大文件仅保留本机忽略目录。

# Verification plan

## Verification cases

- AC-1 => M09-G12-ACCOUNTING-01
- AC-2 => M09-G12-FIT-01
- AC-3 => M09-G12-CALIBRATION-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-3
