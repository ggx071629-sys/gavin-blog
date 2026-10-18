---
id: spec-20260914-answer-stability
level: L1
summary: 本地修复同义问题的证据选择、清单路由和无效回答验收
load_when:
  - task:20260914-answer-stability
task_id: 20260914-answer-stability
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/docs/decisions/20260914-sitewide-assistant-scope.md
documentation_reason: 用户明确全站公开页面知识范围；持久记录边界，文档仅保留本地。
state_history:
---

# Context

线上只读排查已复现：个人资料召回后被预算裁掉，清单问法依赖时间关键词，有引用的残句被当成成功。用户授权先本地修复、适度增加预算，发布仅业务代码。已有不相关修改保留。

# Goal

同义个人问题稳定覆盖当前公开个人资料；文章目录查询保留数量时间约束；预算优先保障证据；无关或不完整回答不能成功；拒答允许一次有界证据恢复。

# Non-goals

不部署、不推送、不变更存储、索引模型、限流、每日总预算或来源可信边界；不发布测试和 Harness。

# Acceptance criteria

- AC-1: 全站公开页面均为证据范围；技能问法补充个人资料但保留相关文章和项目，字符与 token 预算取舍兼顾来源；一般技术和其他人物问题不误归为博主技能。
- AC-2: 普通已发表文章清单调用目录工具，主题解释走 RAG，日期、数量和多任务约束不丢失。
- AC-3: 配置采用 16000 输入与 1024 输出上限；受信本地 tokenizer 带余量估算，缺失时保守回退；不得突破输入或上下文上限。
- AC-4: 冒号残句、无关引用、把教程当个人掌握程度的推断被拒绝；明确标注文章内容、项目记录的相关完整事实允许补充技能自述，保留否定和限制。
- AC-5: 已完成但空回答可补检索重试一次，最多两次聊天，不重发未知请求，不放松当前版本/会话校验。

# Verification plan

## Verification cases

- AC-1 => M09-STABILITY-01
- AC-2 => M09-STABILITY-02
- AC-3 => M09-STABILITY-03
- AC-4 => M09-STABILITY-04
- AC-5 => M09-STABILITY-05

## Gates

- api-tests => AC-1, AC-2, AC-3, AC-4, AC-5
- api-quality => AC-1, AC-2, AC-3, AC-4, AC-5
